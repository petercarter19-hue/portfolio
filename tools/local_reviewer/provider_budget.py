"""Immutable installation AI accounting, excluded from content backups.

Balances are derived from at most 500 lifetime reservations. Uncertain calls keep
their full encumbrance and active fence. Deliberate administrator rollback of the
entire ledger cannot be detected without an external monotonic anchor.
"""
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sqlite3
from uuid import UUID

RESERVE = "usp_ReserveResumeHostedExtractionForOwner"
FINISH = "usp_FinishResumeHostedExtractionForOwner"
RESERVE_KEYS = {"@UserKey", "@Scope", "@RequestId", "@ReservationMicroUsd",
                "@MaximumCalls", "@HardCapMicroUsd", "@ConcurrentRequests"}
FINISH_KEYS = {"@UserKey", "@Scope", "@RequestId"}
PROFILE_NAMES = {"interview", "extraction", "synthesis", "public", "speech"}
ONBOARDING_ALLOWANCE_MICRO_USD = 50_000_000
ALLOWANCE_TABLES = ("onboarding_allowances", "onboarding_allowance_members")


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def parameters(value, expected):
    if not isinstance(value, (list, tuple)):
        raise ValueError("Closed accounting parameters required")
    result = {}
    for pair in value:
        if not isinstance(pair, (tuple, list)) or len(pair) != 2 or pair[0] in result:
            raise ValueError("Closed accounting parameters required")
        result[pair[0]] = pair[1]
    if set(result) != expected:
        raise ValueError("Closed accounting parameters required")
    return result


def request_id(value):
    if not isinstance(value, str) or str(UUID(value)) != value:
        raise ValueError("Canonical request UUID required")
    return value


def natural(value, *, positive=False):
    if type(value) is not int or not int(positive) <= value <= 2**53 - 1:
        raise ValueError("Bounded integer accounting value required")
    return value


def identity_digest(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", value):
        raise ValueError("Bounded native response identity required")
    return sha256(value.encode("ascii")).hexdigest()


def validate_allocation(owner, allocation_sha256, profiles):
    request_id(owner)
    if not isinstance(allocation_sha256, str) or not re.fullmatch("[0-9a-f]{64}", allocation_sha256):
        raise ValueError("Bound allocation digest required")
    if not isinstance(profiles, dict) or set(profiles) != PROFILE_NAMES:
        raise ValueError("All five allocated profiles required")
    scopes = set()
    for profile in profiles.values():
        if not isinstance(profile, dict):
            raise ValueError("Explicit profile allocation required")
        scope = profile.get("scope")
        if not isinstance(scope, str) or not re.fullmatch("[a-z0-9-]{1,80}", scope) or scope in scopes:
            raise ValueError("Distinct explicit scopes required")
        scopes.add(scope)
        for key in ("maximum_calls", "hard_cap_micro_usd", "reservation_micro_usd", "concurrent_requests"):
            natural(profile.get(key), positive=True)
        if (profile["concurrent_requests"] != 1 or profile["maximum_calls"] > 100
                or profile["reservation_micro_usd"] > profile["hard_cap_micro_usd"]):
            raise ValueError("Bound allocation limits exceeded")


class ProviderBudget:
    persistence_label = "private_installation_sqlite_immutable_accounting_not_azure_sql"
    TABLES = ("metadata", "reservations", "settlements", "native_responses", "releases", "overruns")

    @staticmethod
    def _resolutions(db):
        db.execute("""CREATE TABLE operator_resolutions (
            scope TEXT NOT NULL, request_id TEXT NOT NULL, charge INTEGER NOT NULL CHECK(charge>0),
            evidence TEXT NOT NULL, created_at_utc TEXT NOT NULL,
            PRIMARY KEY(scope,request_id), FOREIGN KEY(scope,request_id) REFERENCES reservations)""")
        for action in ("UPDATE", "DELETE"):
            db.execute(f"CREATE TRIGGER immutable_operator_resolutions_{action} BEFORE {action} ON operator_resolutions "
                       "BEGIN SELECT RAISE(ABORT,'Immutable accounting event'); END")
        db.execute("PRAGMA user_version=3")

    @classmethod
    def initialize(cls, path, *, owner, allocation_sha256, profiles):
        validate_allocation(owner, allocation_sha256, profiles)
        path = Path(path).absolute()
        cls._ordinary(path)
        if path.suffix != ".sqlite3":
            raise ValueError("Ordinary private ledger path required")
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
        with closing(sqlite3.connect(path, isolation_level=None)) as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE")
            db.execute("CREATE TABLE metadata (name TEXT PRIMARY KEY, value TEXT NOT NULL)")
            db.execute("""CREATE TABLE reservations (
                scope TEXT NOT NULL, request_id TEXT NOT NULL, owner TEXT NOT NULL,
                amount INTEGER NOT NULL CHECK(amount>0), created_at_utc TEXT NOT NULL,
                PRIMARY KEY(scope,request_id))""")
            db.execute("""CREATE TABLE settlements (
                scope TEXT NOT NULL, request_id TEXT NOT NULL, charge INTEGER NOT NULL CHECK(charge>=0),
                evidence TEXT NOT NULL, created_at_utc TEXT NOT NULL,
                PRIMARY KEY(scope,request_id), FOREIGN KEY(scope,request_id) REFERENCES reservations)""")
            db.execute("""CREATE TABLE native_responses (
                identity_sha256 TEXT PRIMARY KEY, scope TEXT NOT NULL, request_id TEXT NOT NULL,
                FOREIGN KEY(scope,request_id) REFERENCES settlements)""")
            db.execute("""CREATE TABLE releases (
                scope TEXT NOT NULL, request_id TEXT NOT NULL, created_at_utc TEXT NOT NULL,
                PRIMARY KEY(scope,request_id), FOREIGN KEY(scope,request_id) REFERENCES settlements)""")
            db.execute("""CREATE TABLE overruns (
                scope TEXT NOT NULL, request_id TEXT NOT NULL, observed_charge INTEGER NOT NULL,
                evidence TEXT NOT NULL, PRIMARY KEY(scope,request_id,evidence),
                FOREIGN KEY(scope,request_id) REFERENCES reservations)""")
            for table in cls.TABLES:
                for action in ("UPDATE", "DELETE"):
                    db.execute(f"CREATE TRIGGER immutable_{table}_{action} BEFORE {action} ON {table} "
                               "BEGIN SELECT RAISE(ABORT,'Immutable accounting event'); END")
            db.executemany("INSERT INTO metadata VALUES (?,?)", {
                "owner": owner, "allocation_sha256": allocation_sha256, "profiles": encoded(profiles)}.items())
            db.execute("PRAGMA user_version=2")
            db.commit()
        return cls(path, owner=owner, allocation_sha256=allocation_sha256, profiles=profiles)

    @staticmethod
    def _ordinary(path):
        if any(p.is_symlink() or getattr(p, "is_junction", lambda: False)() for p in (path, *path.parents)):
            raise ValueError("Ordinary private ledger path required")

    def __init__(self, path, *, owner, allocation_sha256, profiles, onboarding_context=None):
        validate_allocation(owner, allocation_sha256, profiles)
        self.path, self.owner = Path(path).absolute(), owner
        self.profiles = json.loads(encoded(profiles))
        self.expected = {"owner": owner, "allocation_sha256": allocation_sha256, "profiles": encoded(profiles)}
        self.onboarding_context = self.validate_onboarding_context(onboarding_context)
        with self.connection() as db:
            if (db.execute("PRAGMA quick_check").fetchone()[0] != "ok"
                    or db.execute("PRAGMA foreign_key_check").fetchone() is not None):
                raise ValueError("Provider ledger is incomplete")

    @contextmanager
    def connection(self):
        self._ordinary(self.path)
        if not self.path.is_file():
            raise ValueError("Existing private ledger required; no new allowance created")
        db = sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True, timeout=5, isolation_level=None)
        try:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("PRAGMA synchronous=FULL")
            # Version, tables and triggers must come from one read snapshot:
            # a concurrent valid v2-to-v3 commit must not look like corruption.
            db.execute("BEGIN")
            version = db.execute("PRAGMA user_version").fetchone()[0]
            tables = self.TABLES + (("operator_resolutions",) if version >= 3 else ()) + (ALLOWANCE_TABLES if version == 4 else ())
            if (version not in (2, 3, 4)
                    or dict(db.execute("SELECT name,value FROM metadata")) != self.expected
                    or {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")} != set(tables)
                    or {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='trigger'")}
                    != {f"immutable_{t}_{a}" for t in tables for a in ("UPDATE", "DELETE")}):
                raise ValueError("Provider allocation or ledger changed; uncertainty preserved")
            db.rollback()
            yield db
        except sqlite3.Error:
            raise ValueError("Provider accounting unavailable; uncertainty preserved") from None
        finally:
            if db.in_transaction:
                db.rollback()
            db.close()

    def profile(self, scope):
        return next((p for p in self.profiles.values() if p["scope"] == scope), None)

    @staticmethod
    def validate_onboarding_context(value):
        if value is None:
            return None
        if (type(value) is not dict or set(value) != {"installation", "namespace"}
                or not isinstance(value["installation"], str) or not re.fullmatch("[0-9a-f]{48}", value["installation"])
                or not isinstance(value["namespace"], str) or not re.fullmatch("[0-9a-f]{64}", value["namespace"])):
            raise ValueError("Exact server-owned onboarding context required")
        return dict(value)

    @staticmethod
    def _create_allowance_tables(db):
        db.execute("""CREATE TABLE onboarding_allowances (
            request_id TEXT PRIMARY KEY, installation TEXT NOT NULL, owner TEXT NOT NULL,
            namespace TEXT NOT NULL, amount INTEGER NOT NULL CHECK(amount=50000000),
            payload TEXT NOT NULL, created_at_utc TEXT NOT NULL,
            UNIQUE(installation,owner,namespace))""")
        db.execute("""CREATE TABLE onboarding_allowance_members (
            scope TEXT NOT NULL, request_id TEXT NOT NULL, allowance_id TEXT NOT NULL,
            PRIMARY KEY(scope,request_id), FOREIGN KEY(scope,request_id) REFERENCES reservations,
            FOREIGN KEY(allowance_id) REFERENCES onboarding_allowances(request_id))""")
        for table in ALLOWANCE_TABLES:
            for action in ("UPDATE", "DELETE"):
                db.execute(f"CREATE TRIGGER immutable_{table}_{action} BEFORE {action} ON {table} "
                           "BEGIN SELECT RAISE(ABORT,'Immutable accounting event'); END")
        db.execute("PRAGMA user_version=4")

    def _allowance(self, db):
        if self.onboarding_context is None or db.execute("PRAGMA user_version").fetchone()[0] != 4:
            return None
        return db.execute("SELECT * FROM onboarding_allowances WHERE installation=? AND owner=? AND namespace=?",
                          (self.onboarding_context["installation"], self.owner, self.onboarding_context["namespace"])).fetchone()

    @staticmethod
    def _allowance_totals(db, allowance):
        return db.execute("""SELECT COUNT(*) AS calls,
            COALESCE(SUM(MAX(CASE WHEN x.request_id IS NOT NULL THEN s.charge ELSE COALESCE(o.charge,r.amount) END,
                             COALESCE(v.charge,0))),0) AS encumbered,
            COALESCE(SUM(CASE WHEN x.request_id IS NOT NULL THEN s.charge ELSE 0 END),0) AS settled,
            COALESCE(SUM(COALESCE(o.charge,0)),0) AS failed_charge,
            COALESCE(SUM(CASE WHEN x.request_id IS NULL AND o.request_id IS NULL THEN r.amount ELSE 0 END),0) AS unresolved,
            COALESCE(MAX(CASE WHEN v.request_id IS NOT NULL THEN 1 ELSE 0 END),0) AS overrun_fenced
            FROM onboarding_allowance_members a JOIN reservations r USING(scope,request_id)
            LEFT JOIN settlements s USING(scope,request_id) LEFT JOIN releases x USING(scope,request_id)
            LEFT JOIN operator_resolutions o USING(scope,request_id)
            LEFT JOIN (SELECT scope,request_id,MAX(observed_charge) AS charge FROM overruns GROUP BY scope,request_id) v
                USING(scope,request_id) WHERE a.allowance_id=?""", (allowance,)).fetchone()

    def grant_onboarding_allowance(self, document, *, evidence):
        fields = {"schema_version", "request_id", "installation", "owner", "namespace", "allocation_sha256",
                  "configuration_sha256", "authority_ref", "amount_micro_usd"}
        if (type(document) is not dict or set(document) != fields or type(document["schema_version"]) is not int
                or document["schema_version"] != 1 or document["owner"] != self.owner
                or document["allocation_sha256"] != self.expected["allocation_sha256"]
                or self.onboarding_context != {key: document[key] for key in ("installation", "namespace")}
                or type(document["amount_micro_usd"]) is not int or document["amount_micro_usd"] != ONBOARDING_ALLOWANCE_MICRO_USD
                or not isinstance(document["authority_ref"], str) or not 1 <= len(document["authority_ref"]) <= 240
                or not isinstance(document["configuration_sha256"], str) or not re.fullmatch("[0-9a-f]{64}", document["configuration_sha256"])
                or type(evidence) is not dict or set(evidence) != {"proof_sha256", "review_sha256", "source_sha256"}
                or any(not isinstance(v, str) or not re.fullmatch("[0-9a-f]{64}", v) for v in evidence.values())):
            raise ValueError("Exact reviewed owner onboarding allowance required")
        request_id(document["request_id"])
        payload = encoded({"document": document, "evidence": evidence})
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version == 4:
                previous = db.execute("SELECT * FROM onboarding_allowances WHERE request_id=?", (document["request_id"],)).fetchone()
                if previous is not None:
                    if previous["payload"] != payload:
                        raise ValueError("Changed allowance request replay refused")
                    db.commit()
                    return {"grant_request_id": previous["request_id"], "replayed": True}
                if self._allowance(db) is not None:
                    raise ValueError("One onboarding allowance only; replenishment is not supported")
            if any(self._totals(db, p["scope"])["active"] for p in self.profiles.values()) or db.execute("SELECT 1 FROM overruns").fetchone():
                raise ValueError("Unresolved provider accounting remains fenced")
            if version == 2:
                self._resolutions(db)
            if version != 4:
                self._create_allowance_tables(db)
            db.execute("INSERT INTO onboarding_allowances VALUES (?,?,?,?,?,?,?)",
                       (document["request_id"], document["installation"], self.owner, document["namespace"],
                        document["amount_micro_usd"], payload, datetime.now(timezone.utc).isoformat()))
            db.commit()
        return {"grant_request_id": document["request_id"], "replayed": False}

    def onboarding_allowance_snapshot(self):
        with self.connection() as db:
            row = self._allowance(db)
            if row is None:
                return None
            totals = self._allowance_totals(db, row["request_id"])
            return {"grant_request_id": row["request_id"], "installation": row["installation"], "owner": row["owner"],
                    "namespace": row["namespace"], "amount_micro_usd": row["amount"],
                    "available_micro_usd": max(0, row["amount"] - totals["encumbered"]),
                    "encumbered_micro_usd": totals["encumbered"], "settled_micro_usd": totals["settled"],
                    "failed_charge_micro_usd": totals["failed_charge"],
                    "overrun_fenced": bool(totals["overrun_fenced"]),
                    "unresolved_micro_usd": totals["unresolved"], "dispatched_calls": totals["calls"]}

    def first_row(self, procedure, values=None):
        if procedure == RESERVE:
            return {"reserved": self.reserve(parameters(values, RESERVE_KEYS))}
        if procedure == FINISH:
            parameters(values, FINISH_KEYS)
            # Legacy finish cannot authorize usage settlement or fence release.
            return {"finished": False}
        raise ValueError("Unsupported provider accounting operation")

    @staticmethod
    def _totals(db, scope, *, base_only=False):
        version = db.execute("PRAGMA user_version").fetchone()[0]
        resolved = ("operator_resolutions" if version >= 3
                    else "(SELECT NULL AS scope,NULL AS request_id,0 AS charge WHERE 0)")
        funding_filter = (" AND NOT EXISTS (SELECT 1 FROM onboarding_allowance_members a WHERE a.scope=r.scope AND a.request_id=r.request_id)"
                          if base_only and version == 4 else "")
        return db.execute(f"""SELECT COUNT(*) AS calls,
            COALESCE(SUM(CASE WHEN s.request_id IS NULL THEN r.amount ELSE s.charge END),0) AS encumbered,
            COALESCE(SUM(COALESCE(s.charge,0)),0) AS settled,
            COALESCE(SUM(COALESCE(o.charge,0)),0) AS failed_charge,
            COALESCE(SUM(CASE WHEN x.request_id IS NULL AND o.request_id IS NULL THEN 1 ELSE 0 END),0) AS active
            FROM reservations r LEFT JOIN settlements s USING(scope,request_id)
            LEFT JOIN releases x USING(scope,request_id)
            LEFT JOIN {resolved} o USING(scope,request_id) WHERE r.scope=?{funding_filter}""", (scope,)).fetchone()

    def resolve_failed_public(self, *, owner, scope, request, amount, evidence):
        """Local operator only. Caller must hold the stopped installation lock.

        Evidence attests independent review of transport/worker quiescence, not
        successful native completion. No successful-settlement row is invented.
        Migration and failure event commit together; ordinary startup never migrates.
        """
        if (owner != self.owner or scope != self.profiles["public"]["scope"]
                or type(amount) is not int or amount != self.profiles["public"]["reservation_micro_usd"]
                or type(evidence) is not dict or set(evidence) != {"proof_sha256", "configuration_sha256", "review_sha256"}
                or any(not isinstance(v, str) or not re.fullmatch("[0-9a-f]{64}", v) for v in evidence.values())):
            raise ValueError("Exact reviewed failed public operation required")
        evidence = encoded(evidence)
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            self._binding(db, owner, scope, request)
            row = db.execute("SELECT amount FROM reservations WHERE scope=? AND request_id=?", (scope, request)).fetchone()
            if row["amount"] != amount or db.execute("SELECT 1 FROM overruns WHERE scope=?", (scope,)).fetchone():
                raise ValueError("Original full reservation without overrun required")
            if db.execute("SELECT 1 FROM settlements WHERE scope=? AND request_id=?", (scope, request)).fetchone():
                raise ValueError("Partial or successful settlement cannot be operator resolved")
            if db.execute("PRAGMA user_version").fetchone()[0] == 2:
                self._resolutions(db)
            previous = db.execute("SELECT charge,evidence FROM operator_resolutions WHERE scope=? AND request_id=?",
                                  (scope, request)).fetchone()
            if previous:
                if previous["charge"] != amount or previous["evidence"] != evidence:
                    raise ValueError("Conflicting operator resolution refused")
            else:
                db.execute("INSERT INTO operator_resolutions VALUES (?,?,?,?,?)",
                           (scope, request, amount, evidence, datetime.now(timezone.utc).isoformat()))
            db.commit()
        return {"request_id": request, "state": "failed_operator_resolved", "charge_micro_usd": amount}

    def reserve(self, values):
        selected = self.profile(values["@Scope"])
        if values["@UserKey"] != self.owner or selected is None or any(
                type(values[k]) is not int or values[k] != selected[f] for k, f in (
                    ("@ReservationMicroUsd", "reservation_micro_usd"), ("@MaximumCalls", "maximum_calls"),
                    ("@HardCapMicroUsd", "hard_cap_micro_usd"), ("@ConcurrentRequests", "concurrent_requests"))):
            return False
        request, scope = request_id(values["@RequestId"]), selected["scope"]
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            total = self._totals(db, scope)
            duplicate = db.execute("SELECT 1 FROM reservations WHERE scope=? AND request_id=?", (scope, request)).fetchone()
            overrun = db.execute("SELECT 1 FROM overruns WHERE scope=?", (scope,)).fetchone()
            allowance = self._allowance(db)
            if allowance is not None:
                funding = self._allowance_totals(db, allowance["request_id"])
                money = (not funding["overrun_fenced"]
                         and funding["encumbered"] + selected["reservation_micro_usd"] <= allowance["amount"])
            else:
                # After migration, an unrecognised onboarding context never borrows base funding.
                money = (not (self.onboarding_context is not None and db.execute("PRAGMA user_version").fetchone()[0] == 4)
                         and self._totals(db, scope, base_only=True)["encumbered"] + selected["reservation_micro_usd"] <= selected["hard_cap_micro_usd"])
            allowed = (not duplicate and not overrun and not total["active"]
                       and total["calls"] < selected["maximum_calls"]
                       and money)
            if allowed:
                db.execute("INSERT INTO reservations VALUES (?,?,?,?,?)", (scope, request, self.owner,
                    selected["reservation_micro_usd"], datetime.now(timezone.utc).isoformat()))
                if allowance is not None:
                    db.execute("INSERT INTO onboarding_allowance_members VALUES (?,?,?)", (scope, request, allowance["request_id"]))
            db.commit()
            return bool(allowed)

    def _binding(self, db, owner, scope, request):
        request_id(request)
        if owner != self.owner or self.profile(scope) is None or db.execute(
                "SELECT 1 FROM reservations WHERE scope=? AND request_id=? AND owner=?",
                (scope, request, owner)).fetchone() is None:
            raise ValueError("Reserved accounting identity required")

    def usage(self, scope, events):
        profile = self.profile(scope)
        if profile is None or not isinstance(events, list) or not 1 <= len(events) <= profile.get("maximum_phases", 1):
            raise ValueError("Bound completed phases required")
        charge, overrun, identities = 0, False, set()
        for index, event in enumerate(events, 1):
            speech = "duration_tariff" in profile
            fields = {"phase", "identity_sha256", "seconds"} if speech else {
                "phase", "identity_sha256", "input_tokens", "output_tokens"}
            if type(event) is not dict or set(event) != fields or type(event["phase"]) is not int or event["phase"] != index:
                raise ValueError("Closed ordered completed phase required")
            identity = event["identity_sha256"]
            if not isinstance(identity, str) or not re.fullmatch("[0-9a-f]{64}", identity) or identity in identities:
                raise ValueError("Unique completed native identity required")
            identities.add(identity)
            if speech:
                seconds, tariff = natural(event["seconds"], positive=True), profile["duration_tariff"]
                charge += (seconds * tariff["operator_micro_usd_per_audio_hour"] + 3599) // 3600
                overrun |= seconds > tariff["maximum_decoded_seconds"]
            else:
                incoming, outgoing = natural(event["input_tokens"]), natural(event["output_tokens"])
                charge += (incoming * profile["input_micro_usd_per_million"]
                           + outgoing * profile["output_micro_usd_per_million"] + 999999) // 1000000
                overrun |= (incoming > profile.get("input_tokens", profile.get("input_tokens_per_phase", 0))
                            or outgoing > profile.get("output_tokens", profile.get("output_tokens_per_phase", 0)))
        natural(charge)
        return charge, overrun or charge > profile["reservation_micro_usd"]

    def observe_overrun(self, owner, scope, request, events):
        charge, overrun = self.usage(scope, events)
        if overrun:
            with self.connection() as db:
                db.execute("BEGIN IMMEDIATE")
                self._binding(db, owner, scope, request)
                db.execute("INSERT OR IGNORE INTO overruns VALUES (?,?,?,?)", (scope, request, charge, encoded(events)))
                db.commit()

    def settle(self, owner, scope, request, events, *, release=True, zero_completion=False):
        if zero_completion is True and scope == self.profiles["public"]["scope"] and events == []:
            charge, overrun = 0, False
        else:
            if zero_completion is not False:
                raise ValueError("Closed zero completion required")
            charge, overrun = self.usage(scope, events)
        if overrun:
            self.observe_overrun(owner, scope, request, events)
            raise ValueError("Observed usage exceeded its reserved envelope")
        evidence = encoded({"zero": "authorized_no_sources", "events": []} if zero_completion else events)
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            self._binding(db, owner, scope, request)
            if (db.execute("PRAGMA user_version").fetchone()[0] >= 3 and db.execute(
                    "SELECT 1 FROM operator_resolutions WHERE scope=? AND request_id=?", (scope, request)).fetchone()):
                raise ValueError("Operator-resolved failure cannot become successful")
            previous = db.execute("SELECT charge,evidence FROM settlements WHERE scope=? AND request_id=?", (scope, request)).fetchone()
            if previous is not None:
                if previous["charge"] != charge or previous["evidence"] != evidence:
                    raise ValueError("Conflicting settlement replay refused")
            else:
                if db.execute("SELECT 1 FROM overruns WHERE scope=?", (scope,)).fetchone():
                    raise ValueError("Overrun accounting remains fenced")
                db.execute("INSERT INTO settlements VALUES (?,?,?,?,?)",
                           (scope, request, charge, evidence, datetime.now(timezone.utc).isoformat()))
                db.executemany("INSERT INTO native_responses VALUES (?,?,?)",
                               [(e["identity_sha256"], scope, request) for e in events])
            if release:
                db.execute("INSERT OR IGNORE INTO releases VALUES (?,?,?)", (scope, request, datetime.now(timezone.utc).isoformat()))
            db.commit()

    def snapshot(self, scope):
        profile = self.profile(scope)
        if profile is None:
            return None
        with self.connection() as db:
            total = self._totals(db, scope)
            base = self._totals(db, scope, base_only=True)
            rows = db.execute("""SELECT r.scope,r.request_id,r.owner,r.amount,r.created_at_utc,
                CASE WHEN x.request_id IS NULL THEN 'active' ELSE 'finished' END AS state,
                s.charge,s.evidence,x.created_at_utc AS finished_at_utc FROM reservations r
                LEFT JOIN settlements s USING(scope,request_id) LEFT JOIN releases x USING(scope,request_id)
                WHERE r.scope=? ORDER BY r.created_at_utc""", (scope,))
            reservations = [dict(row) for row in rows]
            resolutions = [dict(row) for row in db.execute("SELECT * FROM operator_resolutions WHERE scope=?", (scope,))] if db.execute("PRAGMA user_version").fetchone()[0] >= 3 else []
            for row in reservations:
                if any(r["request_id"] == row["request_id"] for r in resolutions):
                    row["state"] = "failed_operator_resolved"
            return {"budget": {**profile, "dispatched_calls": total["calls"], "prepaid_micro_usd": total["encumbered"],
                               "base_prepaid_micro_usd": base["encumbered"],
                               "base_available_micro_usd": max(0, profile["hard_cap_micro_usd"] - base["encumbered"]),
                               "settled_micro_usd": total["settled"], "failed_charge_micro_usd": total["failed_charge"]},
                    "reservations": reservations, "operator_resolutions": resolutions,
                    "overruns": [dict(row) for row in db.execute("SELECT * FROM overruns WHERE scope=?", (scope,))]}

    def has_active(self, scopes):
        with self.connection() as db:
            return any(self._totals(db, scope)["active"] for scope in scopes)
