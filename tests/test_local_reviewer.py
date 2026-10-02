"""Acceptance of the offline adapter's durability and isolation boundaries."""
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import io
import json
import os
from pathlib import Path
import socket
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4
import zipfile

from tools.local_reviewer.persistence import Codec, SnapshotError, SnapshotStore, State
from tools.local_reviewer.manager import extract_artifact, install, verify_release, digest
from tools.local_reviewer.persistence import canonical
from tools.local_reviewer.runtime import Boundary, build_fixture, reset_member


class Choice(Enum):
    ONE = "one"


@dataclass(frozen=True)
class Record:
    value: str
    when: datetime


class SnapshotTests(unittest.TestCase):
    def test_fictional_snapshot_rejects_legacy_and_other_namespaces_without_rewriting_personal(self):
        with tempfile.TemporaryDirectory() as directory:
            obj = SimpleNamespace(values={"personal": "preserved"})
            state = State({"values": (obj, "values")}, Codec())
            personal = SnapshotStore(Path(directory) / "state.json", state)
            personal.save()
            original = personal.path.read_bytes()
            fiction = SnapshotStore(Path(directory) / "fiction.json", state, namespace="a" * 64)
            obj.values = {"fiction": "separate"}
            fiction.save()
            other = SnapshotStore(Path(directory) / "other.json", state, namespace="b" * 64)
            for reader, raw in ((fiction, original), (personal, fiction.path.read_bytes()),
                                (other, fiction.path.read_bytes())):
                with self.assertRaises(SnapshotError):
                    reader.unpack(raw)
            self.assertEqual(personal.path.read_bytes(), original)
            with patch("tools.local_reviewer.persistence.os.replace", side_effect=OSError("interrupted save")):
                with self.assertRaises(OSError):
                    fiction.save()
            fiction.load()
            self.assertEqual(obj.values, {"fiction": "separate"})

    def test_safe_roundtrip_preserves_typed_keys_binary_records_and_enums(self):
        codec = Codec((Record, Choice))
        value = {(1, "owner"): (b"\x00\xff", Record("fiction", datetime.now(timezone.utc)), Choice.ONE), "set": frozenset((1, 2))}
        self.assertEqual(codec.decode(json.loads(json.dumps(codec.encode(value)))), value)
        with self.assertRaises(SnapshotError):
            codec.decode({"$": "record", "c": "os.system", "v": {}})
        with self.assertRaises(SnapshotError):
            codec.encode(object())

    def test_atomic_save_failure_preserves_previous_disk_and_corruption_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            obj = SimpleNamespace(values={"owner": "before"})
            state = State({"values": (obj, "values")}, Codec())
            store = SnapshotStore(Path(directory) / "state.json", state)
            store.save()
            previous = store.path.read_bytes()
            obj.values["owner"] = "after"
            with patch("tools.local_reviewer.persistence.os.replace", side_effect=OSError("disk failed")):
                with self.assertRaises(OSError):
                    store.save()
            self.assertEqual(store.path.read_bytes(), previous)
            store.load()
            self.assertEqual(obj.values["owner"], "before")
            broken = json.loads(previous)
            broken["body"]["generation"] += 1
            with self.assertRaises(SnapshotError):
                store.unpack(json.dumps(broken).encode())

    def test_zip_traversal_link_collision_and_secret_files_are_refused(self):
        for names in (("../escape",), (".env",), ("app.py", "APP.py")):
            with self.subTest(names=names), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "source.zip"
                with zipfile.ZipFile(path, "w") as archive:
                    for name in names:
                        archive.writestr(name, b"untrusted")
                with self.assertRaises(ValueError):
                    extract_artifact(path, Path(directory) / "release")

    def test_failed_update_preparation_never_publishes_new_manifest(self):
        from tools.local_reviewer import manager
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = {"installation": "test", "release": "old"}
            (root / "installation.json").write_text(json.dumps(old))
            real_write = manager.atomic_write
            def fail_inputs(path, data):
                if path.parent.name == "inputs":
                    raise OSError("Injected preparation failure")
                real_write(path, data)
            args = SimpleNamespace(action="update")
            with patch.object(manager, "prepare_release", return_value=("new", {"candidate_state": "reviewed-preview"}, {})), \
                    patch.object(manager, "verify_release"), \
                    patch.object(manager.subprocess, "run", return_value=SimpleNamespace(returncode=0)), \
                    patch.object(manager, "atomic_write", side_effect=fail_inputs), \
                    patch.object(manager, "owned_status") as status:
                with self.assertRaises(OSError):
                    install(root, args)
                status.assert_not_called()
            self.assertEqual(json.loads((root / "installation.json").read_text()), old)

    def test_complete_controller_tree_rejects_added_importable_module(self):
        from tools.local_reviewer import manager
        import hashlib
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            name = "a" * 40 + "-" + "b" * 12
            release = root / "releases" / name
            (release / "source").mkdir(parents=True)
            (release / "requirements-reviewed.txt").write_text("waitress==3.0.2")
            artifact = {"files": {}, "overlay_sha256": digest(release / "requirements-reviewed.txt")}
            (release / "release.json").write_text(json.dumps(artifact))
            expected = {"tools/local_reviewer/__init__.py": hashlib.sha256(b"safe").hexdigest()}
            controller = hashlib.sha256(canonical(expected)).hexdigest()
            target = root / "controllers" / controller
            (target / "tools/local_reviewer").mkdir(parents=True)
            (target / "tools/local_reviewer/__init__.py").write_bytes(b"safe")
            manifest = {"release": name, "artifact": artifact, "runtime": {}, "controller": controller, "controller_files": expected}
            with patch.object(manager, "require_private_runtime"):
                verify_release(root, manifest)
                (target / "tools/__init__.py").write_text("raise RuntimeError('must not import')")
                with self.assertRaisesRegex(ValueError, "controller changed"):
                    verify_release(root, manifest)

    def test_stop_waits_for_child_lifetime_even_after_listener_closes(self):
        from tools.local_reviewer import manager
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            held = True
            attempts = []

            @contextmanager
            def child_lock(path, name):
                self.assertEqual((path, name), (root, "server.lock"))
                attempts.append(held)
                if held:
                    raise BlockingIOError("Child still finishing teardown")
                yield

            def finish_child(_delay):
                nonlocal held
                held = False

            with patch.object(manager, "owned_status", return_value={"running": False}), \
                    patch.object(manager, "exclusive", side_effect=child_lock), \
                    patch.object(manager.time, "sleep", side_effect=finish_child), \
                    patch.object(manager, "control") as control:
                result = manager.stop(root, wait=True)
            self.assertEqual(attempts, [True, False])
            self.assertEqual(result, {"running": False, "stopped": True})
            control.assert_not_called()

    def test_update_waits_for_listener_closed_child_before_checkpoint_and_promotion(self):
        from tools.local_reviewer import manager
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = {"installation": "test", "release": "old"}
            (root / "installation.json").write_text(json.dumps(old))
            (root / "data").mkdir()
            state = root / "data" / "state.json"
            state.write_bytes(b"before final child save")
            held = True
            attempts = []
            real_checkpoint = manager.offline_checkpoint

            @contextmanager
            def child_lock(path, name):
                self.assertEqual((path, name), (root, "server.lock"))
                attempts.append(held)
                if held:
                    raise BlockingIOError("Child still finishing teardown")
                yield

            def finish_child(_delay):
                nonlocal held
                self.assertEqual(json.loads((root / "installation.json").read_text()), old)
                state.write_bytes(b"final child save")
                held = False

            def checkpoint(path):
                self.assertFalse(held)
                return real_checkpoint(path)

            args = SimpleNamespace(action="update")
            with patch.object(manager, "prepare_release", return_value=("new", {"candidate_state": "reviewed-preview"}, {})), \
                    patch.object(manager, "verify_release"), \
                    patch.object(manager.subprocess, "run", return_value=SimpleNamespace(returncode=0)), \
                    patch.object(manager, "owned_status", return_value={"running": False}), \
                    patch.object(manager, "exclusive", side_effect=child_lock), \
                    patch.object(manager.time, "sleep", side_effect=finish_child), \
                    patch.object(manager, "offline_checkpoint", side_effect=checkpoint):
                result = install(root, args)
            self.assertEqual(attempts, [True, False])
            self.assertEqual(result["installed"], "new")
            previous = json.loads((root / "previous.json").read_text())
            self.assertEqual(previous["manifest"], old)
            self.assertEqual((root / "checkpoints" / previous["checkpoint"]).read_bytes(), b"final child save")


class FactoryPairTests(unittest.TestCase):
    """Exercise real loaders, ledger fences and atomic selection on private fiction."""
    def setUp(self):
        from tools.local_reviewer import manager, providers
        from tools.local_reviewer.provider_budget import ProviderBudget
        from tests.test_local_reviewer_providers import configuration
        self.manager, self.providers = manager, providers
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.identity = SimpleNamespace(owner=str(uuid4()))
        self.old = {"installation": "fictional-test", "release": "old", "private_profile": True}
        manager.write(self.root / "installation.json", self.old)
        manager.write(self.root / "private-access.json", {"fictional_owner": self.identity.owner})
        self.sources = {}
        for version in ("old", "new", "onboarding"):
            source = self.root / "releases" / version / "source"
            source.mkdir(parents=True)
            (source / "service.py").write_text("FICTIONAL " + version)
            self.sources[version] = source
        config = configuration(self.identity.owner)
        allocation = canonical({"profiles": config["profiles"]})
        allocation_sha = __import__("hashlib").sha256(allocation).hexdigest()
        (self.root / "ai-allocation.json").write_bytes(allocation)
        config["allocation_sha256"] = allocation_sha
        self.interfaces = {}
        for version in ("old", "new", "onboarding"):
            self.interfaces[version] = {**config["factory"], "ongoing_budget_port": providers.ONGOING_BINDINGS,
                "files_sha256": {"service.py": digest(self.sources[version] / "service.py")}}
        config["factory"] = {key: self.interfaces["old"][key] for key in
                             ("files_sha256", "profile_contract", "limits_maxima")}
        self.config = config
        manager.write(self.root / "live-ai.json", config)
        manager.write(self.root / "ai-factory.json", self.interfaces["old"])
        self.factory = self.root / "successor.json"
        manager.write(self.factory, self.interfaces["new"])
        self.onboarding_factory = self.root / "onboarding.json"
        manager.write(self.onboarding_factory, self.interfaces["onboarding"])
        self.args = SimpleNamespace(action="update", candidate_state="accepted-main", factory=self.factory)
        self.budget = ProviderBudget.initialize(self.root / "data/provider-budget-v1.sqlite3",
            owner=self.identity.owner, allocation_sha256=allocation_sha, profiles=config["profiles"])
        (self.root / "data/state.json").write_bytes(b"preserved fictional content generation15")
        self.protected = {name: (self.root / name).read_bytes() for name in
            ("live-ai.json", "ai-factory.json", "ai-allocation.json", "data/state.json", "data/provider-budget-v1.sqlite3")}
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        # Synthetic immutable interfaces stand in for the three reviewed artifacts;
        # the actual hash checking, source checking and allocation checks run.
        self.stack.enter_context(patch.object(providers, "ALLOCATION_SHA256", allocation_sha))
        self.stack.enter_context(patch.object(providers, "FACTORY_SHA256", digest(self.root / "ai-factory.json")))
        self.stack.enter_context(patch.object(providers, "SUCCESSOR_FACTORY_SHA256", digest(self.factory)))
        self.stack.enter_context(patch.object(providers, "ONBOARDING_FACTORY_SHA256", digest(self.onboarding_factory)))
        self.stack.enter_context(patch.object(manager, "require_private_files"))
        self.stack.enter_context(patch.object(manager, "private_permissions"))
        self.stack.enter_context(patch("tools.local_reviewer.runtime.private_access", return_value=self.identity))
        self.stack.enter_context(patch("tools.local_reviewer.runtime.build_fixture"))
        self.stack.enter_context(patch.object(manager, "verify_release",
            side_effect=lambda _root, manifest: self.sources[manifest["release"]].parent))
        self.status = self.stack.enter_context(patch.object(manager, "owned_status", return_value={"running": False}))
        self.prepare = self.stack.enter_context(patch.object(manager, "prepare_release",
            return_value=("new", {"candidate_state": "accepted-main"}, {})))
        self.probe = self.stack.enter_context(patch.object(manager.subprocess, "run", side_effect=self.probe_pair))

    def probe_pair(self, command, **kwargs):
        # The update must retain the original worker lifetime lock at this point.
        with self.assertRaises(OSError):
            with self.manager.exclusive(self.root, "server.lock"):
                pass
        configuration_id = command[command.index("--provider-configuration") + 1]
        release = command[command.index("--release") + 1]
        self.providers.load_configuration(self.root, self.identity, self.sources[release],
                                          configuration_id=configuration_id)
        self.assertEqual(self.manager.read(self.root / "installation.json"), self.old)
        return SimpleNamespace(returncode=0)

    def assert_preserved(self):
        for name, data in self.protected.items():
            self.assertEqual((self.root / name).read_bytes(), data, name)

    def use_onboarding(self):
        self.args.factory = self.onboarding_factory
        self.prepare.return_value = ("onboarding", {"candidate_state": "accepted-main"}, {})

    def test_onboarding_pair_promotes_from_successor_and_rolls_back_without_rewriting_content(self):
        install(self.root, self.args)
        self.old = self.manager.read(self.root / "installation.json")
        self.use_onboarding()
        install(self.root, self.args)
        manifest = self.manager.read(self.root / "installation.json")
        self.assertEqual(manifest["release"], "onboarding")
        self.assertNotEqual(manifest["provider_configuration"], self.old["provider_configuration"])
        loaded = self.providers.load_configuration(self.root, self.identity, self.sources["onboarding"])
        self.assertEqual(loaded["factory"]["files_sha256"], self.interfaces["onboarding"]["files_sha256"])
        self.assertEqual({k: v for k, v in loaded.items() if k != "factory"},
                         {k: v for k, v in self.config.items() if k != "factory"})
        self.assert_preserved()
        with patch.object(self.manager, "stop", return_value={"stopped": True}):
            self.assertEqual(self.manager.rollback(self.root)["rolled_back"], "new")
        self.assertEqual(self.manager.read(self.root / "installation.json"), self.old)
        self.providers.load_configuration(self.root, self.identity, self.sources["new"])
        self.assert_preserved()

    def test_promotion_and_snapshot_use_one_validated_factory_read(self):
        self.use_onboarding()
        original = self.onboarding_factory.read_bytes()
        read_bytes = Path.read_bytes
        reads = []
        def changing_read(path):
            data = read_bytes(path)
            if path == self.onboarding_factory:
                reads.append(data)
                path.write_bytes(data + b" unreviewed replacement")
            return data
        with patch.object(Path, "read_bytes", changing_read):
            install(self.root, self.args)
        self.assertEqual(reads, [original])
        manifest = self.manager.read(self.root / "installation.json")
        pair = self.manager.read(self.root / "data/provider-configurations" /
                                 (manifest["provider_configuration"] + ".json"))
        self.assertEqual(pair["factory_utf8"].encode(), original)
        self.providers.load_configuration(self.root, self.identity, self.sources["onboarding"])
        self.assert_preserved()

    def test_legacy_loading_does_not_admit_legacy_or_arbitrary_promotion(self):
        self.assertEqual(self.providers.load_configuration(self.root, self.identity, self.sources["old"]), self.config)
        arbitrary = self.root / "arbitrary.json"
        self.manager.write(arbitrary, {**self.interfaces["onboarding"], "unreviewed": True})
        for factory in (self.root / "ai-factory.json", arbitrary):
            with self.subTest(factory=factory.name):
                self.args.factory = factory
                with self.assertRaisesRegex(ValueError, "factory binding changed"):
                    install(self.root, self.args)
                self.prepare.assert_not_called()
                self.assertEqual(self.manager.read(self.root / "installation.json"), self.old)
                self.assert_preserved()

    def test_onboarding_source_or_contract_mismatch_keeps_original_pair(self):
        self.use_onboarding()
        source = self.sources["onboarding"] / "service.py"
        original = source.read_bytes()
        source.write_bytes(b"unreviewed app")
        with self.assertRaisesRegex(ValueError, "Application factory changed"):
            install(self.root, self.args)
        source.write_bytes(original)
        changed = {**self.interfaces["onboarding"], "limits_maxima": {"changed": 1}}
        self.manager.write(self.onboarding_factory, changed)
        with patch.object(self.providers, "ONBOARDING_FACTORY_SHA256", digest(self.onboarding_factory)):
            with self.assertRaisesRegex(ValueError, "contracts or caps"):
                install(self.root, self.args)
        self.assertEqual(self.manager.read(self.root / "installation.json"), self.old)
        self.providers.load_configuration(self.root, self.identity, self.sources["old"])
        self.assert_preserved()

    def test_onboarding_snapshot_or_manifest_failure_keeps_original_pair(self):
        self.use_onboarding()
        real_write = self.manager.atomic_write
        for location in ("provider-configurations", "installation.json"):
            with self.subTest(location=location):
                def fail(path, data):
                    if path.name == location or path.parent.name == location:
                        raise OSError("fictional interrupted write")
                    real_write(path, data)
                with patch.object(self.manager, "atomic_write", side_effect=fail):
                    with self.assertRaises(OSError):
                        install(self.root, self.args)
                self.assertEqual(self.manager.read(self.root / "installation.json"), self.old)
                self.providers.load_configuration(self.root, self.identity, self.sources["old"])
                self.assert_preserved()

    def test_atomic_app_and_configuration_selection_retains_ledger_content_and_identity(self):
        result = install(self.root, self.args)
        self.assertEqual(result["installed"], "new")
        manifest = self.manager.read(self.root / "installation.json")
        self.assertEqual(manifest["installation"], self.old["installation"])
        self.assertEqual(self.manager.read(self.root / "previous.json")["manifest"], self.old)
        config = self.providers.load_configuration(self.root, self.identity, self.sources["new"])
        self.assertEqual({k: v for k, v in config.items() if k != "factory"},
                         {k: v for k, v in self.config.items() if k != "factory"})
        self.assert_preserved()
        with self.manager.exclusive(self.root, "server.lock"):
            pass

    def test_running_or_undrained_worker_refuses_before_preparation(self):
        self.status.return_value = {"running": True}
        with self.assertRaisesRegex(ValueError, "Stop the private site"):
            install(self.root, self.args)
        self.status.return_value = {"running": False}
        with self.manager.exclusive(self.root, "server.lock"):
            with self.assertRaises(OSError):
                install(self.root, self.args)
        self.prepare.assert_not_called()
        self.assert_preserved()

    def test_active_reservation_refuses_without_releasing_or_replacing_original_binding(self):
        profile = self.config["profiles"]["public"]
        self.budget.reserve({"@UserKey": self.identity.owner, "@Scope": profile["scope"],
            "@RequestId": str(uuid4()), "@ReservationMicroUsd": profile["reservation_micro_usd"],
            "@MaximumCalls": profile["maximum_calls"], "@HardCapMicroUsd": profile["hard_cap_micro_usd"],
            "@ConcurrentRequests": 1})
        before = self.budget.snapshot(profile["scope"])
        with self.assertRaisesRegex(ValueError, "active provider reservations"):
            install(self.root, self.args)
        self.assertEqual(self.budget.snapshot(profile["scope"]), before)
        self.assertEqual(self.manager.read(self.root / "installation.json"), self.old)
        self.prepare.assert_not_called()
        self.probe.assert_not_called()

    def test_factory_tampering_and_preview_promotion_refuse_before_pointer_change(self):
        self.factory.write_text("{}")
        with self.assertRaisesRegex(ValueError, "binding changed"):
            install(self.root, self.args)
        self.args.candidate_state = "reviewed-preview"
        with self.assertRaisesRegex(ValueError, "accepted-app update"):
            install(self.root, self.args)
        self.assertEqual(self.manager.read(self.root / "installation.json"), self.old)
        self.assert_preserved()

    def test_candidate_source_mismatch_leaves_old_pair_loadable(self):
        (self.sources["new"] / "service.py").write_text("unreviewed")
        with self.assertRaisesRegex(ValueError, "Application factory changed"):
            install(self.root, self.args)
        self.assertEqual(self.manager.read(self.root / "installation.json"), self.old)
        self.providers.load_configuration(self.root, self.identity, self.sources["old"])
        self.assert_preserved()

    def test_cached_preview_or_contract_change_cannot_use_an_accepted_argument(self):
        self.prepare.return_value = ("new", {"candidate_state": "reviewed-preview"}, {})
        with self.assertRaisesRegex(ValueError, "artifact is not accepted"):
            install(self.root, self.args)
        self.prepare.return_value = ("new", {"candidate_state": "accepted-main"}, {})
        changed = json.loads(self.factory.read_text())
        changed["limits_maxima"] = {**changed["limits_maxima"], "proof_max_age_seconds": 901}
        self.manager.write(self.factory, changed)
        with patch.object(self.providers, "SUCCESSOR_FACTORY_SHA256", digest(self.factory)):
            with self.assertRaisesRegex(ValueError, "contracts or caps"):
                install(self.root, self.args)
        self.assertEqual(self.manager.read(self.root / "installation.json"), self.old)
        self.assert_preserved()

    def test_ordinary_controller_update_retains_selected_configuration(self):
        install(self.root, self.args)
        selected = self.manager.read(self.root / "installation.json")["provider_configuration"]
        def probe_existing(command, **kwargs):
            self.assertNotIn("--provider-configuration", command)
            self.providers.load_configuration(self.root, self.identity, self.sources["new"])
            return SimpleNamespace(returncode=0)
        self.probe.side_effect = probe_existing
        self.args.factory = None
        install(self.root, self.args)
        self.assertEqual(self.manager.read(self.root / "installation.json")["provider_configuration"], selected)
        self.assert_preserved()

    def test_snapshot_or_manifest_write_failure_retains_old_pair(self):
        real_write = self.manager.atomic_write
        for location in ("provider-configurations", "installation.json"):
            with self.subTest(location=location):
                def fail(path, data):
                    if path.name == location or path.parent.name == location:
                        raise OSError("fictional interrupted write")
                    real_write(path, data)
                with patch.object(self.manager, "atomic_write", side_effect=fail):
                    with self.assertRaises(OSError):
                        install(self.root, self.args)
                self.assertEqual(self.manager.read(self.root / "installation.json"), self.old)
                self.providers.load_configuration(self.root, self.identity, self.sources["old"])
                self.assert_preserved()

    def test_selected_snapshot_tampering_missing_or_invalid_id_refuses_without_fallback(self):
        install(self.root, self.args)
        manifest = self.manager.read(self.root / "installation.json")
        path = self.root / "data/provider-configurations" / (manifest["provider_configuration"] + ".json")
        original = path.read_bytes()
        path.write_bytes(original + b" ")
        with self.assertRaisesRegex(ValueError, "binding changed"):
            self.providers.load_configuration(self.root, self.identity, self.sources["new"])
        path.unlink()
        with self.assertRaises(ValueError):
            self.providers.load_configuration(self.root, self.identity, self.sources["new"])
        for invalid in (None, "../escape", "a" * 63):
            self.manager.write(self.root / "installation.json", {**manifest, "provider_configuration": invalid})
            with self.assertRaisesRegex(ValueError, "configuration identity"):
                self.providers.load_configuration(self.root, self.identity, self.sources["old"])

    def test_previous_manifest_rollback_selects_original_pair_and_preserves_budget(self):
        install(self.root, self.args)
        with patch.object(self.manager, "stop", return_value={"stopped": True}):
            result = self.manager.rollback(self.root)
        self.assertEqual(result["rolled_back"], "old")
        self.assertEqual(self.manager.read(self.root / "installation.json"), self.old)
        self.assertEqual(self.providers.load_configuration(self.root, self.identity, self.sources["old"]), self.config)
        self.assert_preserved()

    def test_active_successor_request_refuses_rollback_without_stranding_recovery(self):
        install(self.root, self.args)
        profile = self.config["profiles"]["public"]
        self.budget.reserve({"@UserKey": self.identity.owner, "@Scope": profile["scope"],
            "@RequestId": str(uuid4()), "@ReservationMicroUsd": profile["reservation_micro_usd"],
            "@MaximumCalls": profile["maximum_calls"], "@HardCapMicroUsd": profile["hard_cap_micro_usd"],
            "@ConcurrentRequests": 1})
        manifest = (self.root / "installation.json").read_bytes()
        content = (self.root / "data/state.json").read_bytes()
        ledger = (self.root / "data/provider-budget-v1.sqlite3").read_bytes()
        before = self.budget.snapshot(profile["scope"])
        with patch.object(self.manager, "stop", return_value={"stopped": True}), \
                patch.object(self.manager, "offline_checkpoint") as checkpoint:
            with self.assertRaisesRegex(ValueError, "current binding before rollback"):
                self.manager.rollback(self.root)
            checkpoint.assert_not_called()
        self.assertEqual((self.root / "installation.json").read_bytes(), manifest)
        self.assertEqual((self.root / "data/state.json").read_bytes(), content)
        self.assertEqual((self.root / "data/provider-budget-v1.sqlite3").read_bytes(), ledger)
        self.assertEqual(self.budget.snapshot(profile["scope"]), before)
        self.assertFalse((self.root / "rollback-receipt.json").exists())
        self.providers.load_configuration(self.root, self.identity, self.sources["new"])

    def test_active_original_request_also_refuses_app_change_without_a_new_factory(self):
        # A new release identity changes recovery binding even if factory files
        # are byte-identical. Controller-only refresh of the same app remains usable.
        (self.sources["new"] / "service.py").write_bytes((self.sources["old"] / "service.py").read_bytes())
        profile = self.config["profiles"]["public"]
        self.budget.reserve({"@UserKey": self.identity.owner, "@Scope": profile["scope"],
            "@RequestId": str(uuid4()), "@ReservationMicroUsd": profile["reservation_micro_usd"],
            "@MaximumCalls": profile["maximum_calls"], "@HardCapMicroUsd": profile["hard_cap_micro_usd"],
            "@ConcurrentRequests": 1})
        before = self.budget.snapshot(profile["scope"])
        self.args.factory = None
        def probe_existing(command, **kwargs):
            self.providers.load_configuration(self.root, self.identity, self.sources["new"])
            return SimpleNamespace(returncode=0)
        self.probe.side_effect = probe_existing
        with patch.object(self.manager, "offline_checkpoint") as checkpoint:
            with self.assertRaisesRegex(ValueError, "before updating the app binding"):
                install(self.root, self.args)
            checkpoint.assert_not_called()
        self.assertEqual(self.manager.read(self.root / "installation.json"), self.old)
        self.assertEqual(self.budget.snapshot(profile["scope"]), before)
        self.assertFalse((self.root / "previous.json").exists())
        self.providers.load_configuration(self.root, self.identity, self.sources["old"])

    def test_same_app_controller_refresh_preserves_active_original_recovery_binding(self):
        profile = self.config["profiles"]["public"]
        self.budget.reserve({"@UserKey": self.identity.owner, "@Scope": profile["scope"],
            "@RequestId": str(uuid4()), "@ReservationMicroUsd": profile["reservation_micro_usd"],
            "@MaximumCalls": profile["maximum_calls"], "@HardCapMicroUsd": profile["hard_cap_micro_usd"],
            "@ConcurrentRequests": 1})
        before = self.budget.snapshot(profile["scope"])
        binding = self.manager.operator_configuration_digest(self.root, self.old)
        content = (self.root / "data/state.json").read_bytes()
        ledger = (self.root / "data/provider-budget-v1.sqlite3").read_bytes()
        self.prepare.return_value = ("old", {"candidate_state": "accepted-main"}, {})
        self.args.factory = None
        def probe_original(command, **kwargs):
            self.assertNotIn("--provider-configuration", command)
            self.providers.load_configuration(self.root, self.identity, self.sources["old"])
            return SimpleNamespace(returncode=0)
        self.probe.side_effect = probe_original
        install(self.root, self.args)
        manifest = self.manager.read(self.root / "installation.json")
        self.assertEqual(manifest["release"], self.old["release"])
        self.assertNotIn("provider_configuration", manifest)
        self.assertEqual(self.manager.operator_configuration_digest(self.root, manifest), binding)
        self.assertEqual(self.budget.snapshot(profile["scope"]), before)
        self.assertEqual((self.root / "data/state.json").read_bytes(), content)
        self.assertEqual((self.root / "data/provider-budget-v1.sqlite3").read_bytes(), ledger)


class WorkspaceOperatorTests(unittest.TestCase):
    setUpPair = FactoryPairTests.setUp
    probe_pair = FactoryPairTests.probe_pair

    def setUp(self):
        self.setUpPair()
        from tools.local_reviewer.private_identity import PrivateIdentity
        self.identity = PrivateIdentity.from_config({"origin": "https://test.example.ts.net:8443",
            "login": "owner@example.test", "owner": self.identity.owner, "display_name": "Private Test Profile"})
        self.manager.write(self.root / "private-access.json", {
            "origin": self.identity.origin, "login": self.identity.login,
            "owner": self.identity.owner, "display_name": self.identity.display_name})
        self.stack.enter_context(patch("tools.local_reviewer.runtime.private_access", return_value=self.identity))
        self.stack.enter_context(patch("tools.local_reviewer.runtime.build_fixture", side_effect=self.fresh))
        state = self.fresh()[3]
        state.bindings["values"][0].values = {"personal-secret": "never copied"}
        store = SnapshotStore(self.root / "data/state.json", state)
        store.save()
        self.personal = store.path.read_bytes()

    def fresh(self, *args, **kwargs):
        obj = SimpleNamespace(values={"fresh-fixture": True})
        return None, None, set(), State({"values": (obj, "values")}, Codec())

    def snapshots(self):
        return {name: self.budget.snapshot(profile["scope"]) for name, profile in self.config["profiles"].items()}

    def test_create_select_restore_and_return_keep_personal_and_root_accounting(self):
        from tools.local_reviewer.runtime import selected_context
        before = self.snapshots()
        ledger = (self.root / "data/provider-budget-v1.sqlite3").read_bytes()
        self.manager.create_workspace(self.root)
        self.manager.select_workspace(self.root, "onboarding")
        context = selected_context(self.root)
        store = context.store(self.fresh()[3]); store.load()
        self.assertNotIn("personal-secret", store.state.capture().__str__())
        checkpoint = self.manager.offline_checkpoint(self.root)
        store.state.bindings["values"][0].values = {"fictional-edit": "corrected"}
        store.save()
        self.manager.restore_private(self.root, checkpoint)
        restored = context.store(self.fresh()[3]); restored.load()
        self.assertEqual(restored.state.bindings["values"][0].values, {"fresh-fixture": True})
        # Even if a personal checkpoint is copied into the fictional directory,
        # the typed namespace contract must refuse it before any state write.
        (context.checkpoints / "foreign.json").write_bytes(self.personal)
        current = context.state_path.read_bytes()
        with self.assertRaises(SnapshotError): self.manager.restore_private(self.root, "foreign.json")
        self.assertEqual(context.state_path.read_bytes(), current)
        self.manager.select_workspace(self.root, "personal")
        self.assertEqual(selected_context(self.root).identity, self.identity)
        self.assertEqual((self.root / "data/state.json").read_bytes(), self.personal)
        self.assertEqual(self.snapshots(), before)
        self.assertEqual((self.root / "data/provider-budget-v1.sqlite3").read_bytes(), ledger)

    def test_active_reservation_in_each_profile_blocks_create_select_and_restore(self):
        self.manager.create_workspace(self.root)
        checkpoint = self.manager.offline_checkpoint(self.root)
        for name, profile in self.config["profiles"].items():
            request = str(uuid4())
            self.assertTrue(self.budget.reserve({"@UserKey": self.identity.owner, "@Scope": profile["scope"],
                "@RequestId": request, "@ReservationMicroUsd": profile["reservation_micro_usd"],
                "@MaximumCalls": profile["maximum_calls"], "@HardCapMicroUsd": profile["hard_cap_micro_usd"],
                "@ConcurrentRequests": 1}))
            for action in (lambda: self.manager.create_workspace(self.root),
                           lambda: self.manager.select_workspace(self.root, "onboarding"),
                           lambda: self.manager.restore_private(self.root, checkpoint)):
                with self.subTest(profile=name), self.assertRaisesRegex(ValueError, "active reservations"):
                    action()
            event = {"phase": 1, "identity_sha256": __import__("hashlib").sha256(request.encode()).hexdigest()}
            event.update({"seconds": 1} if "duration_tariff" in profile else {"input_tokens": 1, "output_tokens": 0})
            self.budget.settle(self.identity.owner, profile["scope"], request, [event])
        self.manager.select_workspace(self.root, "onboarding")

    def test_live_or_undrained_server_blocks_selection_and_creation(self):
        self.status.return_value = {"running": True}
        with self.assertRaisesRegex(ValueError, "Stop the private site"):
            self.manager.create_workspace(self.root)
        self.status.return_value = {"running": False}
        self.manager.create_workspace(self.root)
        with self.manager.exclusive(self.root, "server.lock"):
            with self.assertRaises(OSError): self.manager.select_workspace(self.root, "onboarding")

    def test_interrupted_selection_keeps_last_valid_pointer_and_both_saved_states(self):
        self.manager.create_workspace(self.root)
        original = (self.root / "installation.json").read_bytes()
        fiction = self.root / "data/fictional-workspaces/onboarding/state.json"
        saved = fiction.read_bytes()
        with patch.object(self.manager, "write", side_effect=OSError("interrupted pointer")):
            with self.assertRaises(OSError): self.manager.select_workspace(self.root, "onboarding")
        self.assertEqual((self.root / "installation.json").read_bytes(), original)
        self.assertEqual(fiction.read_bytes(), saved)
        self.assertEqual((self.root / "data/state.json").read_bytes(), self.personal)

    def test_metadata_tampering_and_missing_selection_fail_closed(self):
        from tools.local_reviewer.runtime import selected_context
        self.manager.create_workspace(self.root)
        manifest = self.manager.read(self.root / "installation.json")
        descriptor = self.root / "data/fictional-workspaces/onboarding/descriptor.json"
        original = descriptor.read_bytes()
        descriptor.write_bytes(original + b" ")
        with self.assertRaisesRegex(ValueError, "descriptor changed"): selected_context(self.root)
        descriptor.write_bytes(original)
        self.manager.write(self.root / "installation.json", {k: v for k, v in manifest.items() if k != "workspace"})
        with self.assertRaisesRegex(ValueError, "personal fallback refused"): selected_context(self.root)
        for key, value in (("owner", str(uuid4())), ("origin", "https://other.example.ts.net:8444"),
                           ("installation", "another-installation")):
            changed = {**json.loads(original), key: value}; raw = canonical(changed); descriptor.write_bytes(raw)
            self.manager.write(self.root / "installation.json", {**manifest, "workspace": {
                **manifest["workspace"], "descriptor_sha256": __import__("hashlib").sha256(raw).hexdigest()}})
            with self.subTest(key=key), self.assertRaises(ValueError): selected_context(self.root)

    def test_recovery_digest_binds_fictional_context_and_old_rollback_is_refused(self):
        original = self.manager.operator_configuration_digest(self.root, self.manager.read(self.root / "installation.json"))
        self.manager.create_workspace(self.root)
        manifest = self.manager.read(self.root / "installation.json")
        self.assertEqual(self.manager.operator_configuration_digest(self.root, manifest), original)
        self.manager.select_workspace(self.root, "onboarding")
        current = self.manager.read(self.root / "installation.json")
        self.assertNotEqual(self.manager.operator_configuration_digest(self.root, current), original)
        self.manager.write(self.root / "previous.json", {"manifest": self.old, "checkpoint": None})
        with patch.object(self.manager, "stop") as stop:
            with self.assertRaisesRegex(ValueError, "older controllers"):
                self.manager.rollback(self.root)
            stop.assert_not_called()

    def test_controller_update_preserves_selected_context_and_saved_content(self):
        from tools.local_reviewer.runtime import selected_context
        self.manager.create_workspace(self.root)
        self.manager.select_workspace(self.root, "onboarding")
        before = self.manager.read(self.root / "installation.json")
        context = selected_context(self.root)
        saved = context.state_path.read_bytes()
        self.probe.side_effect = None; self.probe.return_value = SimpleNamespace(returncode=0)
        self.prepare.return_value = ("old", {"candidate_state": "accepted-main"}, {})
        self.args.factory = None
        self.manager.install_artifact(self.root, self.args)
        current = self.manager.read(self.root / "installation.json")
        self.assertEqual(current["workspace"], before["workspace"])
        self.assertEqual(selected_context(self.root).binding, context.binding)
        self.assertEqual(context.state_path.read_bytes(), saved)
        self.assertEqual((self.root / "data/state.json").read_bytes(), self.personal)

    def test_workspace_directory_links_are_refused_before_loading_state(self):
        from tools.local_reviewer.runtime import selected_context
        self.manager.create_workspace(self.root)
        target = self.root / "data/fictional-workspaces/onboarding"
        original = Path.is_symlink
        with patch.object(Path, "is_symlink", lambda p: p == target or original(p)):
            with self.assertRaisesRegex(ValueError, "ordinary files"):
                selected_context(self.root)


class FixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Path(os.environ.get("PEERSLATE_LOCAL_REVIEWER_SOURCE", str(Path(__file__).resolve().parents[1]))).resolve()
        cls.stack = ExitStack()
        cls.fixture, cls.app, cls.endpoints, cls.state = build_fixture(cls.source, cls.stack)
        cls.initial = cls.state.capture()

    @classmethod
    def tearDownClass(cls):
        cls.stack.close()

    def setUp(self):
        from werkzeug.test import Client
        from werkzeug.wrappers import Response
        self.state.restore(self.initial)
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.install = Path(self.directory.name)
        self.store = SnapshotStore(self.install / "data" / "state.json", self.state)
        self.store.save()
        self.stop_event = threading.Event()
        self.boundary = Boundary(self.fixture, self.app, self.endpoints, self.store, self.install,
                                 {"port": 53720, "source_sha": "a" * 40, "candidate_state": "reviewed-preview"}, "test-control-token", self.stop_event)
        self.client = Client(self.boundary, Response)
        self.base = "http://127.0.0.1:53720"
        self.headers = {"Origin": self.base, "X-PeerSlate-Request": "same-origin"}

    def request(self, path, method="GET", **kwargs):
        return self.client.open(path, method=method, base_url=self.base, environ_base={"REMOTE_ADDR": "127.0.0.1"}, **kwargs)

    def select(self, member):
        return self.request("/__mvp1_fixture__/" + member)

    def add_skill(self, label):
        response = self.request("/api/resume-intake/me/submissions", method="POST", headers=self.headers,
                                data={"request": json.dumps({"type": "add_submission", "request_id": str(uuid4()), "items": [
                                    {"client_key": "skill", "record_type": "skill", "values": {"name": label, "summary": None}}]})}, content_type="multipart/form-data")
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        self.assertEqual(response.json["summary"]["saved"], 1)
        return response.json

    def command(self, action, payload=None):
        return self.request("/__reviewer__/control/" + action, method="POST", headers={"X-Reviewer-Token": "test-control-token"}, json=payload or {})

    def test_acknowledged_member_edits_roundtrip_disk_without_granting_sharing(self):
        self.select("member-a")
        self.add_skill("Fictional A skill")
        self.select("member-b")
        self.add_skill("Fictional B skill")
        encoded = self.state.capture()
        self.state.restore(self.initial)
        self.store.load()
        self.assertEqual(self.state.capture(), encoded)
        for member, label in (("g-member-a", "Fictional A skill"), ("g-member-b", "Fictional B skill")):
            entries = self.fixture.shared.policy.list_entries(member)["entries"]
            self.assertEqual(entries[0]["values"]["skill_name"], label)
            self.assertFalse(entries[0]["resume_display"])
            self.assertFalse(entries[0]["visitor_ai"])

    def test_failed_disk_publish_refuses_success_and_restores_memory(self):
        self.select("member-a")
        before = self.store.path.read_bytes()
        with patch("tools.local_reviewer.persistence.os.replace", side_effect=OSError("disk full")):
            with self.assertRaises(AssertionError):
                self.add_skill("Must not be acknowledged")
        self.assertEqual(self.store.path.read_bytes(), before)
        self.assertEqual(self.fixture.shared.policy.list_entries("g-member-a")["entries"], [])

    def test_reset_and_restore_preserve_other_member_and_linked_media_originals(self):
        from hashlib import sha256
        for member, label in (("member-a", "A"), ("member-b", "B")):
            self.select(member)
            self.add_skill(label)
            self.fixture.shared.seed_photo("g-" + member, width=12, height=8)
            source = {"source_key": str(uuid4()), "version": 1, "sha256": sha256(label.encode()).hexdigest(), "content_type": "text/plain", "state": "active"}
            self.fixture.intake.original_files.retain("g-" + member, source, label.encode())
        self.store.save()
        expected = self.state.capture()
        member_b = self.fixture.shared.policy.repository._owners["g-member-b"]
        result = self.command("reset", {"member": "g-member-a"})
        self.assertEqual(result.status_code, 200, result.get_data(as_text=True))
        self.assertEqual(self.fixture.shared.policy.list_entries("g-member-a")["entries"], [])
        self.assertEqual(self.fixture.shared.policy.repository._owners["g-member-b"], member_b)
        self.assertEqual(len(self.fixture.intake.original_files.list("g-member-a")), 0)
        self.assertEqual(len(self.fixture.intake.original_files.list("g-member-b")), 1)
        self.assertEqual(len(self.fixture.original_storage.blobs), 1)
        self.assertEqual(len(self.fixture.shared.media_storage._objects), 1)
        restored = self.command("restore", {"checkpoint": result.json["checkpoint"]})
        self.assertEqual(restored.status_code, 200, restored.get_data(as_text=True))
        self.assertEqual(self.state.capture(), expected)
        self.store.load()
        self.assertEqual(self.state.capture(), expected)

    def test_foreign_host_origin_headers_guest_and_old_cookie_cannot_cross_boundaries(self):
        self.assertEqual(self.request("/__reviewer__/status", headers={"Host": "evil.example"}).status_code, 403)
        self.assertEqual(self.request("/__mvp1_fixture__/member-a", headers={"Origin": "https://evil.example"}).status_code, 403)
        self.assertEqual(self.request("/__reviewer__/control/reset").status_code, 405)
        self.assertEqual(self.request("/__reviewer__/control/reset", method="POST", json={"member": "g-member-a"}).status_code, 403)
        self.assertEqual(self.request("/api/resume-intake/me", headers={"X-MS-CLIENT-PRINCIPAL-ID": "g-member-a"}).status_code, 404)
        self.client.set_cookie("mvp1-synthetic-owner", "g-member-a")
        self.assertEqual(self.request("/api/resume-intake/me").status_code, 404)
        self.assertEqual(self.request("/api/chat", method="POST", headers=self.headers, json={}).status_code, 404)
        self.assertEqual(self.request("/__reviewer__/control/restore", method="POST", headers={"X-Reviewer-Token": "test-control-token"}, json={"checkpoint": "../state.json"}).status_code, 400)

    def test_private_assistance_speech_sql_and_external_network_are_unavailable(self):
        import mssql_python
        with self.assertRaises(RuntimeError):
            mssql_python.connect("not-a-real-connection")
        with socket.socket() as sock:
            with self.assertRaises(OSError):
                sock.connect(("192.0.2.1", 443))
        with self.assertRaises(OSError):
            socket.getaddrinfo("example.com", 443)
        self.select("member-a")
        response = self.request("/api/resume-synthesis/me/proposals", method="POST", headers=self.headers, json={})
        self.assertEqual(response.status_code, 503)
        self.assertIn("manual editor", response.get_data(as_text=True))

    def test_private_profile_uses_authenticated_owner_and_preserves_saved_work(self):
        from tools.local_reviewer.private_identity import PrivateIdentity
        config = {"origin": "https://reviewer.example.ts.net:8443", "login": "fictional@example.test",
                  "owner": str(uuid4()), "display_name": "Private Test Profile"}
        (self.install / "private-access.json").write_text(json.dumps(config))
        identity = PrivateIdentity.from_config(config)
        stack = ExitStack()
        self.addCleanup(stack.close)
        identity.bind_principal(stack)
        self.boundary.__init__(self.fixture, self.app, self.endpoints, self.store, self.install,
                               {"port": 53720, "source_sha": "a" * 40, "candidate_state": "reviewed-preview"}, "test-control-token", self.stop_event)
        def remote(path, method="GET", headers=None, **kwargs):
            return self.client.open(path, method=method, base_url=identity.origin,
                                    environ_base={"REMOTE_ADDR": "127.0.0.1"}, headers={
                                    "X-Forwarded-Host": "reviewer.example.ts.net:8443", "X-Forwarded-Proto": "https",
                                    "Tailscale-User-Login": identity.login, **(headers or {})}, **kwargs)
        for login in ("", "other@example.test"):
            self.assertEqual(remote("/app/resume", headers={"Tailscale-User-Login": login}).status_code, 403)
        self.assertEqual(self.request("/app/resume").status_code, 403)
        self.assertEqual(remote("/__mvp1_fixture__/member-a").status_code, 404)
        self.assertEqual(remote("/").headers["Location"], "/app/resume")
        self.client.set_cookie("reviewer-fictional-owner", "g-member-b", domain="reviewer.example.ts.net")
        self.client.set_cookie("mvp1-synthetic-owner", "g-member-c", domain="reviewer.example.ts.net")
        saved = remote("/api/resume-intake/me/draft", method="PUT",
                       headers={"Origin": identity.origin, "X-PeerSlate-Request": "same-origin"},
                       json={"request_id": str(uuid4()), "text": "Fictional private work history"})
        self.assertEqual(saved.status_code, 200, saved.get_data(as_text=True))
        saved_state = self.state.capture()
        self.state.restore(self.initial)
        self.store.load()
        self.assertEqual(self.state.capture(), saved_state)
        self.assertIn(identity.owner, self.fixture.intake.repository._owners)
        self.assertNotIn("g-member-b", self.fixture.intake.repository._owners)
        self.assertNotIn("g-member-c", self.fixture.intake.repository._owners)
        self.assertEqual(remote("/api/resume-intake/me/draft", method="PUT", json={}).status_code, 403)
        for path in ("/__reviewer__/status", "/__reviewer__/control/stop", "/__reviewer__/control/reset"):
            self.assertEqual(remote(path, method="POST" if "control" in path else "GET",
                                    headers={"Origin": identity.origin, "X-Reviewer-Token": "test-control-token"}, json={}).status_code, 403)
        self.assertFalse(self.stop_event.is_set())
        self.assertEqual(self.command("reset", {"member": "g-member-a"}).status_code, 400)
        page = remote("/app/resume")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"PRIVATE TEST SITE", page.data)
        self.assertEqual(page.headers["Cache-Control"], "private, no-store")

    def test_fictional_owner_application_edits_restart_and_stale_tabs_leave_personal_unchanged(self):
        from tools.local_reviewer.private_identity import PrivateIdentity
        from tools.local_reviewer.runtime import selected_context
        from tools.local_reviewer import manager
        from werkzeug.test import Client
        from werkzeug.wrappers import Response
        config = {"origin": "https://reviewer.example.ts.net:8443", "login": "owner@example.test",
                  "owner": str(uuid4()), "display_name": "Private Test Profile"}
        manager.write(self.install / "private-access.json", config)
        identity = PrivateIdentity.from_config(config)
        stack = ExitStack(); self.addCleanup(stack.close); identity.bind_principal(stack)
        manifest = {"installation": "fictional-test", "private_profile": True}
        manager.write(self.install / "installation.json", manifest)
        def client_for(store):
            boundary = Boundary(self.fixture, self.app, self.endpoints, store, self.install,
                {"port": 53720, "source_sha": "a" * 40, "candidate_state": "reviewed-preview"},
                "test-control-token", threading.Event())
            return Client(boundary, Response)
        def remote(client, origin, path, method="GET", **kwargs):
            return client.open(path, method=method, base_url=origin, environ_base={"REMOTE_ADDR": "127.0.0.1"},
                headers={"X-Forwarded-Host": origin.removeprefix("https://"), "X-Forwarded-Proto": "https",
                         "Tailscale-User-Login": identity.login, "Origin": origin,
                         "X-PeerSlate-Request": "same-origin"}, **kwargs)
        personal_client = client_for(self.store)
        response = remote(personal_client, identity.origin, "/api/resume-intake/me/draft", "PUT",
                          json={"request_id": str(uuid4()), "text": "Personal fixture content that must stay private"})
        self.assertEqual(response.status_code, 200)
        original = self.store.path.read_bytes()
        descriptor = {"schema": 1, "workspace": "onboarding", "installation": manifest["installation"],
                      "owner": identity.owner, "personal_origin": identity.origin,
                      "origin": "https://reviewer.example.ts.net:8444",
                      "private_access_sha256": manager.digest(self.install / "private-access.json")}
        raw = canonical(descriptor); namespace = __import__("hashlib").sha256(raw).hexdigest()
        directory = self.install / "data/fictional-workspaces/onboarding"
        manager.atomic_write(directory / "descriptor.json", raw)
        manifest["workspace"] = {"protocol": 1, "descriptor_sha256": namespace, "selected": "onboarding"}
        manager.write(self.install / "installation.json", manifest)
        self.state.restore(self.initial)
        context = selected_context(self.install); store = context.store(self.state); store.save()
        fictional_client = client_for(store)
        for version, text in enumerate(("Fictional first draft", "Fictional revised draft", "Fictional corrected draft")):
            response = remote(fictional_client, context.identity.origin, "/api/resume-intake/me/draft", "PUT",
                              json={"request_id": str(uuid4()), "text": text,
                                    **({"expected_version": version} if version else {})})
            self.assertEqual(response.status_code, 200, response.data)
        page = remote(fictional_client, context.identity.origin, "/app/resume")
        self.assertEqual(page.status_code, 200); self.assertIn(b"FICTIONAL ONBOARDING WORKSPACE", page.data)
        self.assertNotIn(b"Personal fixture content", page.data)
        for method in ("GET", "PUT"):
            self.assertEqual(remote(fictional_client, identity.origin, "/api/resume-intake/me/draft", method,
                                   json={} if method == "PUT" else None).status_code, 403)
        self.state.restore(self.initial)
        restarted = context.store(self.state); restarted.load()
        restarted_client = client_for(restarted)
        result = remote(restarted_client, context.identity.origin, "/api/resume-intake/me/draft")
        self.assertIn(b"Fictional corrected draft", result.data)
        self.assertNotIn(b"Personal fixture content", result.data)
        saved = context.state_path.read_bytes()
        self.assertEqual(self.store.path.read_bytes(), original)
        manager.write(self.install / "installation.json", {**manifest, "workspace": {**manifest["workspace"], "selected": "personal"}})
        self.state.restore(self.initial); self.store.load()
        returned = client_for(self.store)
        self.assertIn(b"Personal fixture content", remote(returned, identity.origin, "/api/resume-intake/me/draft").data)
        self.assertEqual(remote(returned, context.identity.origin, "/api/resume-intake/me/draft", "PUT", json={}).status_code, 403)
        self.assertEqual(context.state_path.read_bytes(), saved)
        self.assertEqual(self.store.path.read_bytes(), original)

    def test_status_remains_token_authenticated_during_long_request(self):
        acquired, release = threading.Event(), threading.Event()
        def operation():
            with self.boundary.lock:
                acquired.set()
                release.wait(3)
        worker = threading.Thread(target=operation)
        worker.start()
        acquired.wait(1)
        try:
            self.assertEqual(self.request("/__reviewer__/status").status_code, 403)
            response = self.request("/__reviewer__/status", headers={"X-Reviewer-Token": "test-control-token"})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json["running"])
        finally:
            release.set()
            worker.join()

    def test_stop_acknowledges_during_active_work_and_preserves_its_save(self):
        started, finish = threading.Event(), threading.Event()
        responses = []
        def active(environ):
            started.set()
            finish.wait(3)
            self.fixture.original_storage.blobs["fictional-active-operation"] = (b"fictional bytes", "etag")
            return self.boundary.response({"saved": True})
        with patch.object(self.boundary, "dispatch", side_effect=active) as dispatch:
            worker = threading.Thread(target=lambda: responses.append(self.request("/")))
            worker.start()
            self.assertTrue(started.wait(1))
            try:
                stopped = self.command("stop")
                self.assertEqual(stopped.status_code, 202)
                self.assertTrue(stopped.json["finishes_current_request"])
                self.assertTrue(worker.is_alive())
                status = self.request("/__reviewer__/status", headers={"X-Reviewer-Token": "test-control-token"})
                self.assertTrue(status.json["stopping"])
                self.assertEqual(self.request("/").status_code, 503)
                self.assertEqual(dispatch.call_count, 1)
            finally:
                finish.set()
            worker.join(3)
        self.assertEqual(responses[0].status_code, 200)
        self.state.restore(self.initial)
        self.store.load()
        self.assertIn("fictional-active-operation", self.fixture.original_storage.blobs)

    def test_fixture_restores_prior_logging_suppression_when_closed(self):
        import logging
        original = logging.root.manager.disable
        try:
            logging.disable(logging.ERROR)
            with ExitStack() as runtime_stack:
                build_fixture(self.source, runtime_stack)
                self.assertEqual(logging.root.manager.disable, logging.CRITICAL)
            self.assertEqual(logging.root.manager.disable, logging.ERROR)
        finally:
            logging.disable(original)

    def test_queued_app_requests_are_fenced_after_stop_and_leave_a_control_worker(self):
        responses, waiting = [], threading.Event()
        original = self.boundary.lock
        count, counter_lock = [0], threading.Lock()
        class ObservedLock:
            def __enter__(inner):
                with counter_lock:
                    count[0] += 1
                    if count[0] == 3:
                        waiting.set()
                original.acquire()
            def __exit__(inner, *args):
                original.release()
        self.boundary.lock = ObservedLock()
        workers = [threading.Thread(target=lambda: responses.append(self.request("/"))) for _ in range(3)]
        with patch.object(self.boundary, "dispatch") as dispatch:
            original.acquire()
            try:
                for worker in workers:
                    worker.start()
                self.assertTrue(waiting.wait(2))
                self.assertEqual(self.request("/").status_code, 503)
                self.assertEqual(self.command("stop").status_code, 202)
                self.assertTrue(self.stop_event.is_set())
            finally:
                original.release()
                for worker in workers:
                    worker.join(3)
            dispatch.assert_not_called()
        self.assertEqual([response.status_code for response in responses], [503, 503, 503])

    def test_private_https_never_admits_direct_network_or_wrong_host(self):
        from tools.local_reviewer.private_identity import PrivateIdentity
        self.boundary.private_access = PrivateIdentity.from_config({"origin": "https://reviewer.example.ts.net", "login": "fictional@example.test", "owner": str(uuid4()), "display_name": "Test"})
        for host, address in (("https://reviewer.example.ts.net", "100.64.0.2"), ("https://evil.example", "127.0.0.1")):
            response = self.client.get("/__mvp1_fixture__/", base_url=host, environ_base={"REMOTE_ADDR": address}, headers={"Tailscale-User-Login": "fictional@example.test"})
            self.assertEqual(response.status_code, 403)

    def test_assets_load_during_full_app_admission_without_touching_saved_state(self):
        from concurrent.futures import ThreadPoolExecutor
        for _ in range(3):
            self.assertTrue(self.boundary.application_slots.acquire(blocking=False))
        try:
            with patch.object(self.store.state, "capture", side_effect=AssertionError("Asset touched saved state")):
                with ThreadPoolExecutor(max_workers=8) as pool:
                    responses = list(pool.map(self.request, ["/static/css/resume-editor.css"] * 8))
                self.assertEqual([r.status_code for r in responses], [200] * 8)
                self.assertTrue(all(r.mimetype == "text/css" for r in responses))
                self.assertTrue(all(r.headers["Cache-Control"] == "private, no-store" for r in responses))
                self.assertEqual(self.request("/api/resume-drafts/me").status_code, 503)
                self.assertEqual(self.command("stop").status_code, 202)
                self.assertEqual(self.request("/static/css/resume-editor.css").status_code, 503)
        finally:
            for _ in range(3):
                self.boundary.application_slots.release()

    def test_private_assets_retain_identity_origin_and_method_boundaries(self):
        from tools.local_reviewer.private_identity import PrivateIdentity
        identity = PrivateIdentity.from_config({"origin": "https://reviewer.example.ts.net:8443",
            "login": "fictional@example.test", "owner": str(uuid4()), "display_name": "Test"})
        self.boundary.private_access = identity
        self.app.config["TRUSTED_HOSTS"] = ["127.0.0.1", "reviewer.example.ts.net"]
        headers = {"X-Forwarded-Host": "reviewer.example.ts.net:8443",
                   "X-Forwarded-Proto": "https", "Tailscale-User-Login": identity.login}
        path = "/static/css/resume-editor.css"
        for extra, expected in (({}, 200), ({"Tailscale-User-Login": "other@example.test"}, 403),
                                ({"Origin": "https://other.example"}, 403)):
            response = self.client.get(path, base_url=identity.origin,
                environ_base={"REMOTE_ADDR": "127.0.0.1"}, headers={**headers, **extra})
            self.assertEqual(response.status_code, expected)
        self.assertEqual(self.request(path).status_code, 403)
        self.assertEqual(self.request(path, method="POST").status_code, 403)

    def test_serve_loopback_host_cannot_bypass_identity_or_admin_boundary(self):
        from tools.local_reviewer.private_identity import PrivateIdentity
        self.boundary.private_access = PrivateIdentity.from_config({"origin": "https://reviewer.example.ts.net", "login": "fictional@example.test", "owner": str(uuid4()), "display_name": "Test"})
        for login in (None, "other@example.test", "fictional@example.test"):
            headers = {"X-Forwarded-Host": self.base.removeprefix("http://"), "X-Forwarded-Proto": "https", "X-Forwarded-For": "100.64.0.2", "X-Reviewer-Token": "test-control-token"}
            if login is not None:
                headers["Tailscale-User-Login"] = login
            for path in ("/__mvp1_fixture__/member-a", "/__reviewer__/status", "/__reviewer__/control/stop"):
                response = self.request(path, method="POST" if "control" in path else "GET", headers=headers)
                self.assertEqual(response.status_code, 403)
        self.assertFalse(self.stop_event.is_set())
        self.boundary.private_access = None
        self.assertEqual(self.request("/__mvp1_fixture__/", headers={"X-Forwarded-Proto": "https"}).status_code, 403)

    def test_private_access_config_defaults_closed_and_rejects_relaxed_values(self):
        from tools.local_reviewer.runtime import private_access
        self.assertIsNone(private_access(self.install))
        for origin in ("http://reviewer.example.ts.net", "https://*.example.ts.net", "https://evil.example", "https://reviewer.example.ts.net/path"):
            (self.install / "private-access.json").write_text(json.dumps({"origin": origin, "login": "fictional@example.test"}))
            with self.assertRaises(ValueError):
                private_access(self.install)

    def test_browser_resource_policy_and_removed_external_font_hints(self):
        self.select("member-a")
        response = self.request("/app/resume", headers={"Accept-Encoding": "gzip"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"fonts.googleapis.com", response.data)
        self.assertNotIn(b"fonts.gstatic.com", response.data)
        policies = response.headers.getlist("Content-Security-Policy")
        self.assertTrue(any("connect-src 'self'" in policy and "font-src 'self'" in policy for policy in policies))
        self.assertGreaterEqual(len(policies), 2)


if __name__ == "__main__":
    unittest.main()
