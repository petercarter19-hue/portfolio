"""Versioned JSON snapshots of explicitly bound fixture state. No executable payloads."""
from __future__ import annotations

import base64
import dataclasses
import enum
import hashlib
import json
import math
import os
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

SCHEMA = 1
MAX_SNAPSHOT_BYTES = 400_000_000


class SnapshotError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def atomic_write(path: Path, data: bytes):
    """Publish only a flushed, complete file. Never truncate the live snapshot."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".writing")
    with temporary.open("wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


class Codec:
    def __init__(self, classes=()):
        self.classes = {cls.__module__ + "." + cls.__qualname__: cls for cls in classes}

    def encode(self, value, depth=0):
        if depth > 100:
            raise SnapshotError("State is too deeply nested")
        child = lambda v: self.encode(v, depth + 1)
        if isinstance(value, enum.Enum):
            return self._class(value, "enum", value.name)
        if value is None or type(value) in (str, int, bool):
            return value
        if type(value) is float and math.isfinite(value):
            return value
        if isinstance(value, datetime):
            return {"$": "datetime", "v": value.isoformat()}
        if isinstance(value, date):
            return {"$": "date", "v": value.isoformat()}
        if isinstance(value, Decimal):
            if not value.is_finite():
                raise SnapshotError("Nonfinite decimal")
            return {"$": "decimal", "v": str(value)}
        if type(value) is bytes:
            return {"$": "bytes", "v": base64.b64encode(value).decode("ascii")}
        if type(value) is dict:
            return {"$": "dict", "v": [[child(k), child(v)] for k, v in value.items()]}
        for cls, tag in ((list, "list"), (tuple, "tuple"), (set, "set"), (frozenset, "frozenset")):
            if type(value) is cls:
                items = [child(v) for v in value]
                if tag in {"set", "frozenset"}:
                    items.sort(key=canonical)
                return {"$": tag, "v": items}
        if dataclasses.is_dataclass(value) and not isinstance(value, type):
            return self._class(value, "record", {field.name: child(getattr(value, field.name)) for field in dataclasses.fields(value)})
        raise SnapshotError("Unapproved state type: " + type(value).__name__)

    def _class(self, value, tag, payload):
        name = type(value).__module__ + "." + type(value).__qualname__
        if self.classes.get(name) is not type(value):
            raise SnapshotError("Unapproved record type: " + name)
        return {"$": tag, "c": name, "v": payload}

    def decode(self, value, depth=0):
        if depth > 100:
            raise SnapshotError("State is too deeply nested")
        child = lambda v: self.decode(v, depth + 1)
        if value is None or type(value) in (str, int, bool):
            return value
        if type(value) is float and math.isfinite(value):
            return value
        if type(value) is not dict or set(value) not in ({"$", "v"}, {"$", "v", "c"}):
            raise SnapshotError("Invalid state encoding")
        tag, payload = value["$"], value["v"]
        if tag in {"enum", "record"}:
            cls = self.classes.get(value.get("c"))
            if cls is None:
                raise SnapshotError("Unapproved record in snapshot")
            if tag == "enum" and issubclass(cls, enum.Enum):
                return cls[payload]
            if tag == "record" and dataclasses.is_dataclass(cls):
                if type(payload) is not dict or set(payload) != {f.name for f in dataclasses.fields(cls)}:
                    raise SnapshotError("Record fields changed")
                return cls(**{k: child(v) for k, v in payload.items()})
            raise SnapshotError("Record kind changed")
        if "c" in value:
            raise SnapshotError("Unexpected class field")
        if tag == "dict":
            if type(payload) is not list:
                raise SnapshotError("Invalid dictionary")
            result = {}
            for pair in payload:
                if type(pair) is not list or len(pair) != 2:
                    raise SnapshotError("Invalid dictionary entry")
                key = child(pair[0])
                if key in result:
                    raise SnapshotError("Duplicate dictionary key")
                result[key] = child(pair[1])
            return result
        if tag in {"list", "tuple", "set", "frozenset"}:
            if type(payload) is not list:
                raise SnapshotError("Invalid collection")
            return {"list": list, "tuple": tuple, "set": set, "frozenset": frozenset}[tag](child(v) for v in payload)
        if type(payload) is not str:
            raise SnapshotError("Invalid scalar")
        if tag == "datetime":
            return datetime.fromisoformat(payload)
        if tag == "date":
            return date.fromisoformat(payload)
        if tag == "decimal":
            result = Decimal(payload)
            if not result.is_finite():
                raise SnapshotError("Invalid decimal")
            return result
        if tag == "bytes":
            return base64.b64decode(payload, validate=True)
        raise SnapshotError("Unknown state encoding")


class State:
    """Explicit attributes only: locks, transports and callbacks are reconstructed."""
    def __init__(self, bindings: dict[str, tuple[Any, str]], codec: Codec):
        self.bindings, self.codec = bindings, codec
        self.types = {name: type(getattr(obj, attr)) for name, (obj, attr) in bindings.items()}
        self.contract = hashlib.sha256(canonical({
            "bindings": {k: v.__name__ for k, v in self.types.items()},
            "records": {name: [f.name for f in dataclasses.fields(cls)] if dataclasses.is_dataclass(cls)
                        else list(cls.__members__) for name, cls in codec.classes.items()},
        })).hexdigest()

    def capture(self):
        return self.codec.encode({name: getattr(obj, attr) for name, (obj, attr) in self.bindings.items()})

    def validate(self, encoded):
        decoded = self.codec.decode(encoded)
        if type(decoded) is not dict or set(decoded) != set(self.bindings):
            raise SnapshotError("Snapshot bindings changed")
        if any(type(decoded[k]) is not cls for k, cls in self.types.items()):
            raise SnapshotError("Snapshot binding types changed")
        return decoded

    def restore(self, encoded):
        values = self.validate(encoded)
        for name, (obj, attr) in self.bindings.items():
            setattr(obj, attr, values[name])


class SnapshotStore:
    def __init__(self, path: Path, state: State, *, namespace=None):
        if namespace is not None and (not isinstance(namespace, str) or len(namespace) != 64
                                      or any(c not in "0123456789abcdef" for c in namespace)):
            raise SnapshotError("Invalid fictional snapshot namespace")
        self.path, self.state, self.generation, self.namespace = path, state, 0, namespace

    def ordinary_path(self):
        if self.namespace is not None and any(
                p.is_symlink() or getattr(p, "is_junction", lambda: False)()
                for p in (self.path, *self.path.parents)):
            raise SnapshotError("Fictional snapshot path contains a link")

    def pack(self, encoded, generation=None):
        body = {"schema": SCHEMA, "contract": self.state.contract,
                "generation": self.generation if generation is None else generation, "state": encoded}
        if self.namespace is not None:
            body["namespace"] = self.namespace
        return canonical({"body": body, "sha256": hashlib.sha256(canonical(body)).hexdigest()})

    def unpack(self, data):
        if len(data) > MAX_SNAPSHOT_BYTES:
            raise SnapshotError("Snapshot exceeds installation limit")
        document = json.loads(data)
        if type(document) is not dict or set(document) != {"body", "sha256"}:
            raise SnapshotError("Invalid snapshot envelope")
        body = document["body"]
        if hashlib.sha256(canonical(body)).hexdigest() != document["sha256"]:
            raise SnapshotError("Snapshot checksum does not match")
        fields = {"schema", "contract", "generation", "state"} | ({"namespace"} if self.namespace else set())
        if (set(body) != fields or body["schema"] != SCHEMA or body["contract"] != self.state.contract
                or body.get("namespace") != self.namespace):
            raise SnapshotError("Snapshot is incompatible; preserve it and restore its matching release")
        if type(body["generation"]) is not int or body["generation"] < 0:
            raise SnapshotError("Invalid snapshot generation")
        self.state.validate(body["state"])
        return body

    def save(self, encoded=None):
        self.ordinary_path()
        encoded = self.state.capture() if encoded is None else encoded
        self.state.validate(encoded)
        data = self.pack(encoded, self.generation + 1)
        if len(data) > MAX_SNAPSHOT_BYTES:
            raise SnapshotError("Snapshot exceeds installation limit; checkpoint and reduce fictional files")
        atomic_write(self.path, data)
        self.generation += 1

    def load(self):
        self.ordinary_path()
        body = self.unpack(self.path.read_bytes())
        self.state.restore(body["state"])
        self.generation = body["generation"]
