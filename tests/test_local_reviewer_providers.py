import json
import os
from hashlib import sha256
from contextlib import ExitStack, closing
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from tools.local_reviewer.provider_budget import FINISH, RESERVE, ProviderBudget

SOURCE = Path(os.environ.get("PEERSLATE_LOCAL_REVIEWER_SOURCE", str(Path(__file__).resolve().parents[1]))).resolve()


def configuration(owner):
    # Qualified app constructor envelopes; fake transports never leave the process.
    models = {"interview": ("gpt-6-sol", "eval0930-gpt-6-sol", "low", 32768, 5000000, 15000000, 824320, 5000000),
              "extraction": ("gpt-6-luna", "gpt-6-luna", "low", 128000, 1000000, 6000000, 998400, 6000000),
              "synthesis": ("gpt-6.1-sol", "peerslate-resume-sol61", "high", 16384, 100000000, 100000000, 8294400, 50000000)}
    profiles, contract = {}, {}
    for name, (model, alias, effort, output, iprice, oprice, reservation, cap) in models.items():
        profiles[name] = {"model": model, "reasoning_effort": effort, "service_tier": "default", "scope": "test-" + name,
                          "maximum_calls": 100, "hard_cap_micro_usd": cap, "reservation_micro_usd": reservation, "concurrent_requests": 1,
                          "input_tokens": 230400 if name == "extraction" else 66560, "output_tokens": output,
                          "input_micro_usd_per_million": iprice, "output_micro_usd_per_million": oprice}
        contract[name] = {"model": model, "alias": alias, "effort": effort, "tier": "default",
                          "wire_bytes": 229376 if name == "extraction" else 65536,
                          "input_tokens": 230400 if name == "extraction" else 66560,
                          "output_tokens": output, "safety_prices_per_million_micro_usd": [iprice, oprice]}
    for name, reservation, cap in (("public", 329728, 2000000), ("speech", 100000, 600000)):
        profiles[name] = {"scope": "test-" + name, "maximum_calls": 100, "hard_cap_micro_usd": cap,
                          "reservation_micro_usd": reservation, "concurrent_requests": 1}
    profiles["public"].update(model="gpt-6-luna", reasoning_effort="low", service_tier="default",
        input_tokens_per_phase=66560, output_tokens_per_phase=16384, maximum_phases=2,
        input_micro_usd_per_million=1000000, output_micro_usd_per_million=6000000)
    profiles["speech"]["duration_tariff"] = {"operator_micro_usd_per_audio_hour": 1200000,
        "billing_quantum_seconds": 1, "minimum_seconds": 1, "maximum_decoded_seconds": 300}
    return {"owner": owner, "allocation_sha256": "a" * 64, "profiles": profiles, "signing_key": "b" * 64,
            "factory": {"files_sha256": {}, "profile_contract": contract, "limits_maxima": {
                "maximum_task_bytes": 20000, "maximum_input_bytes": 65536, "maximum_output_bytes": 100000,
                "maximum_field_bytes": 8000, "proof_max_age_seconds": 900}}}


class PrivateFactoryIntegrityTests(unittest.TestCase):
    def setUp(self):
        from copy import deepcopy
        from types import SimpleNamespace
        from tools.local_reviewer import providers
        from tools.local_reviewer.persistence import canonical
        self.providers, self.canonical = providers, canonical
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = self.root / "source"
        self.source.mkdir()
        (self.source / "service.py").write_bytes(b"synthetic reviewed source")
        self.identity = SimpleNamespace(owner=str(uuid4()))
        self.config = configuration(self.identity.owner)
        self.config["factory"]["files_sha256"] = {"service.py": sha256((self.source / "service.py").read_bytes()).hexdigest()}
        allocation = canonical({"profiles": self.config["profiles"]})
        self.config["allocation_sha256"] = sha256(allocation).hexdigest()
        (self.root / "ai-allocation.json").write_bytes(allocation)
        runtime = self.root / "ocr"
        filenames = ["bin/tesseract.exe", "tessdata/eng.traineddata", "tessdata/osd.traineddata",
                     "python-packages/pypdfium2/__init__.py", "python-packages/pypdfium2_raw/__init__.py"]
        filenames += ["bin/dependency-" + str(i) for i in range(214)]
        pins = {}
        for name in filenames:
            path = runtime / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(("synthetic pinned dependency " + name).encode())
            pins[str(path)] = sha256(path.read_bytes()).hexdigest()
        manifest = {"schema_version": 1, "runtime_root": str(runtime), "tesseract": str(runtime / filenames[0]),
                    "tessdata": str(runtime / "tessdata"), "renderer": "pypdfium2", "renderer_version": "5.14.0",
                    "files_sha256": pins}
        self.manifest = self.root / "ocr-manifest.json"
        self.manifest.write_bytes(canonical(manifest))
        self.proof = deepcopy(providers.PRIVATE_ONBOARDING_QUALIFICATION)
        self.proof["resume_ocr"] = {"manifest_path": str(self.manifest), "manifest_sha256": sha256(self.manifest.read_bytes()).hexdigest()}
        self.interface = {**self.config["factory"], "ongoing_budget_port": providers.ONGOING_BINDINGS,
                          "private_onboarding_qualification": self.proof}
        self.factory = canonical(self.interface)
        self.original = canonical({**self.config["factory"], "ongoing_budget_port": providers.ONGOING_BINDINGS})
        (self.root / "live-ai.json").write_bytes(canonical(self.config))
        (self.root / "ai-factory.json").write_bytes(self.original)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(providers, "ALLOCATION_SHA256", self.config["allocation_sha256"]))
        self.stack.enter_context(patch.object(providers, "FACTORY_SHA256", sha256(self.original).hexdigest()))
        self.stack.enter_context(patch.object(providers, "PRIVATE_DELIVERY_FACTORY_SHA256", sha256(self.factory).hexdigest()))
        self.stack.enter_context(patch.object(providers, "PRIVATE_ONBOARDING_QUALIFICATION", self.proof))
        self.select_pair(self.config, self.factory)

    def select_pair(self, config, factory):
        pair = self.canonical({"live_ai": config, "factory_utf8": factory.decode()})
        selected = sha256(pair).hexdigest()
        directory = self.root / "data/provider-configurations"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / (selected + ".json")).write_bytes(pair)
        (self.root / "installation.json").write_bytes(self.canonical({"provider_configuration": selected}))
        return selected

    def test_exact_factory_selects_all_219_verified_native_pins_without_provider_dispatch(self):
        self.assertEqual(self.providers.load_configuration(self.root, self.identity, self.source), self.config)
        self.assertEqual(self.providers.selected_ocr_configuration(self.root), str(self.manifest))
        self.assertFalse((self.root / "data/provider-budget-v1.sqlite3").exists())
        self.assertEqual(self.providers.selected_configuration(self.root, original=True)[1], json.loads(self.original))
        self.assertIsNone(self.providers.selected_ocr_configuration(self.root, original=True))
        with self.assertRaisesRegex(ValueError, "one explicit"):
            self.providers.selected_configuration(self.root, "a" * 64, original=True)

    def test_manifest_native_pin_and_unpinned_import_changes_fail_closed(self):
        from services.resume_onboarding_document_reader import ResumeDocumentReadError
        raw = self.manifest.read_bytes()
        self.manifest.write_bytes(raw + b" ")
        with self.assertRaisesRegex(ValueError, "manifest changed"):
            self.providers.selected_ocr_configuration(self.root)
        self.manifest.write_bytes(raw)
        native = self.root / "ocr/bin/dependency-0"
        native.write_bytes(b"altered")
        with self.assertRaisesRegex(ResumeDocumentReadError, "ocr_dependency_changed"):
            self.providers.selected_ocr_configuration(self.root)
        native.write_bytes(b"synthetic pinned dependency bin/dependency-0")
        (self.root / "ocr/python-packages/unpinned.py").write_bytes(b"unreviewed import")
        with self.assertRaisesRegex(ResumeDocumentReadError, "ocr_dependency_unpinned"):
            self.providers.selected_ocr_configuration(self.root)

    def test_unreviewed_factory_and_ocr_in_closed_live_ai_are_rejected(self):
        changed = json.loads(self.factory)
        changed["private_onboarding_qualification"]["resume_ocr"]["manifest_path"] = "unreviewed.json"
        with self.assertRaisesRegex(ValueError, "factory binding"):
            self.providers.bound_factory(self.canonical(changed), for_promotion=True)
        self.select_pair({**self.config, "resume_ocr": str(self.manifest)}, self.factory)
        with self.assertRaisesRegex(ValueError, "Invalid private AI configuration"):
            self.providers.load_configuration(self.root, self.identity, self.source)

    def test_fresh_child_receives_verified_path_after_isolation_before_lazy_capture(self):
        import subprocess
        import sys
        selected = self.providers.selected_ocr_configuration(self.root)
        program = """
import json,os,sys
from contextlib import ExitStack
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from tools.local_reviewer.runtime import build_fixture
from services.resume_intake_policy import selected_policy_for_tests
os.environ['PEERSLATE_RESUME_OCR_CONFIGURATION']='inherited-unreviewed-value'
with ExitStack() as stack:
 fixture,app,_,state=build_fixture(Path(sys.argv[1]),stack,ocr_configuration=sys.argv[2],ocr_manifest_sha256=sys.argv[3])
 adapter=fixture.intake.document_adapter
 assert adapter._reader is None
 assert os.environ['PEERSLATE_RESUME_OCR_CONFIGURATION']==sys.argv[2]
 first=adapter.parse('text/plain',b'Synthetic bounded text',selected_policy_for_tests())
 assert first.ok and first.text=='Synthetic bounded text'
 assert adapter._reader.configuration==sys.argv[2]
 os.environ['PEERSLATE_RESUME_OCR_CONFIGURATION']='later-unreviewed-value'
 second=adapter.parse('text/plain',b'Second bounded text',selected_policy_for_tests())
 assert second.ok and adapter._reader.configuration==sys.argv[2]
 print(json.dumps({'bindings':len(state.bindings),'constructors':len(state.codec.classes),'native_ocr_executions':0}))
"""
        child = subprocess.run([sys.executable, "-I", "-B", "-c", program, str(SOURCE), selected,
                                self.proof["resume_ocr"]["manifest_sha256"]],
                               capture_output=True, text=True, timeout=30)
        self.assertEqual(child.returncode, 0, child.stderr[-2000:])
        self.assertEqual(json.loads(child.stdout), {"bindings": 29, "constructors": 54, "native_ocr_executions": 0})

    def test_first_lazy_capture_rejects_changed_manifest_or_native_dependency_pin(self):
        from services.resume_intake_policy import selected_policy_for_tests
        from tools.local_reviewer.runtime import build_fixture
        original = self.manifest.read_bytes()
        expected = self.proof["resume_ocr"]["manifest_sha256"]
        dependency = self.root / "ocr/bin/dependency-0"
        for change in ("whitespace", "dependency_and_pin"):
            with self.subTest(change=change), ExitStack() as stack:
                self.manifest.write_bytes(original)
                dependency.write_bytes(b"synthetic pinned dependency bin/dependency-0")
                selected = self.providers.selected_ocr_configuration(self.root)
                fixture, _, _, _ = build_fixture(SOURCE, stack, ocr_configuration=selected,
                                                ocr_manifest_sha256=expected)
                adapter = fixture.intake.document_adapter
                self.assertIsNone(adapter._reader)
                if change == "whitespace":
                    self.manifest.write_bytes(original + b" ")
                else:
                    dependency.write_bytes(b"unreviewed replacement dependency")
                    settings = json.loads(original)
                    settings["files_sha256"][str(dependency)] = sha256(dependency.read_bytes()).hexdigest()
                    self.manifest.write_bytes(self.canonical(settings))
                result = adapter.parse("text/plain", b"Synthetic literal document", selected_policy_for_tests())
                self.assertFalse(result.ok)
                self.assertEqual(result.reason, "ocr_dependency_changed")
                self.assertIsNone(adapter._reader)
                self.assertIsNone(result.ocr_configuration_sha256)
        self.manifest.write_bytes(original)
        dependency.write_bytes(b"synthetic pinned dependency bin/dependency-0")

    def test_reviewed_lazy_capture_reverifies_expected_hash_after_first_read(self):
        from services.resume_intake_policy import selected_policy_for_tests
        from tools.local_reviewer.runtime import build_fixture
        selected = self.providers.selected_ocr_configuration(self.root)
        expected = self.proof["resume_ocr"]["manifest_sha256"]
        with ExitStack() as stack:
            fixture, _, _, _ = build_fixture(SOURCE, stack, ocr_configuration=selected,
                                            ocr_manifest_sha256=expected)
            adapter = fixture.intake.document_adapter
            self.assertIsNone(adapter._reader)
            first = adapter.parse("text/plain", b"Synthetic literal document", selected_policy_for_tests())
            self.assertTrue(first.ok)
            self.assertEqual(first.ocr_configuration_sha256, expected)
            self.manifest.write_bytes(self.manifest.read_bytes() + b" ")
            second = adapter.parse("text/plain", b"Second document", selected_policy_for_tests())
            self.assertFalse(second.ok)
            self.assertEqual(second.reason, "ocr_dependency_changed")

    def test_source_link_cannot_hide_behind_resolve(self):
        original = Path.is_symlink
        target = self.source / "service.py"
        ordinary = self.source / "ordinary.py"
        ordinary.write_bytes(target.read_bytes())
        try:
            linked = self.source / "linked.py"
            linked.symlink_to(ordinary)
        except OSError:
            with patch.object(Path, "is_symlink", autospec=True,
                              side_effect=lambda path: path == target or original(path)):
                with self.assertRaisesRegex(ValueError, "Factory source path unavailable"):
                    self.providers.load_configuration(self.root, self.identity, self.source)
        else:
            target.unlink()
            linked.rename(target)
            with self.assertRaisesRegex(ValueError, "Factory source path unavailable"):
                self.providers.load_configuration(self.root, self.identity, self.source)


class ProviderCompositionTests(unittest.TestCase):
    def setUp(self):
        from tools.local_reviewer.runtime import build_fixture
        from tools.local_reviewer.private_identity import PrivateIdentity
        from tools.local_reviewer.providers import configure_private_providers
        from tests.test_resume_intake_runtime import SelectedPrivateTransport
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.fixture, self.app, _, self.state = build_fixture(SOURCE, self.stack)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.identity = PrivateIdentity.from_config({"origin": "https://test.example.ts.net:8443", "login": "owner@example.test",
                                                   "owner": str(uuid4()), "display_name": "Private Test Profile"})
        self.config = configuration(self.identity.owner)
        ProviderBudget.initialize(self.root / "data/provider-budget-v1.sqlite3", owner=self.identity.owner,
                                  allocation_sha256=self.config["allocation_sha256"], profiles=self.config["profiles"])
        class NativeTestTransport(SelectedPrivateTransport):
            def post(self, url, **kwargs):
                response = super().post(url, **kwargs)
                original = response.json
                native_id = "resp_" + uuid4().hex
                response.json = lambda: {**original(), "id": native_id}
                return response
        self.transport = NativeTestTransport()
        self.tokens = Mock(return_value="offline-placeholder")
        self.original_repository = self.fixture.intake.repository
        self.budget = configure_private_providers(self.fixture, self.app, self.root, self.identity, self.config,
                                                  token_provider=self.tokens, transport=self.transport)

    def test_composition_keeps_original_storage_and_defers_credentials(self):
        from tools.local_reviewer.providers import _ScopedBaseResumeIntakeService
        self.assertIsInstance(self.fixture.intake, _ScopedBaseResumeIntakeService)
        self.assertIs(self.fixture.intake.repository, self.original_repository)
        self.assertIs(self.app.config["RESUME_INTAKE_SERVICE"], self.fixture.intake)
        self.assertIsNotNone(self.app.config["RESUME_PRIVATE_ASSISTANCE_SERVICE"])
        self.assertIs(self.app.config["MEMBER_VISITOR_AI_SERVICE"], self.fixture.ai)
        self.tokens.assert_not_called()
        self.assertEqual(self.transport.calls, [])
        for profile in self.config["profiles"].values():
            self.assertEqual(self.budget.snapshot(profile["scope"])["budget"]["dispatched_calls"], 0)

    def test_two_saved_state_contexts_share_exact_owner_ledger_counts_and_caps(self):
        self.transport.post = Mock(side_effect=AssertionError("Zero-provider context proof cannot dispatch"))
        from tools.local_reviewer.providers import configure_private_providers
        from tools.local_reviewer.persistence import SnapshotStore
        identity = self.identity.fictional_origin("https://test.example.ts.net:8444")
        personal = self.root / "data/state.json"
        SnapshotStore(personal, self.state).save()
        original = personal.read_bytes()
        from tools.local_reviewer.runtime import build_fixture
        fixture, app, _, state = build_fixture(SOURCE, self.stack)
        with patch.object(ProviderBudget, "initialize", side_effect=AssertionError("no second ledger")):
            fiction_budget = configure_private_providers(fixture, app, self.root, identity, self.config,
                                                         token_provider=self.tokens, transport=self.transport)
        self.assertEqual(fiction_budget.path, self.budget.path)
        self.assertEqual(fiction_budget.profiles, self.budget.profiles)
        for name, profile in self.config["profiles"].items():
            request = str(uuid4())
            values = {"@UserKey": self.identity.owner, "@Scope": profile["scope"], "@RequestId": request,
                      "@ReservationMicroUsd": profile["reservation_micro_usd"], "@MaximumCalls": profile["maximum_calls"],
                      "@HardCapMicroUsd": profile["hard_cap_micro_usd"], "@ConcurrentRequests": 1}
            self.assertTrue(self.budget.reserve(values))
            self.assertFalse(fiction_budget.reserve({**values, "@RequestId": str(uuid4())}))
            event = {"phase": 1, "identity_sha256": sha256(request.encode()).hexdigest()}
            event.update({"seconds": 1} if "duration_tariff" in profile else {"input_tokens": 1, "output_tokens": 0})
            self.budget.settle(self.identity.owner, profile["scope"], request, [event])
            self.assertEqual(fiction_budget.snapshot(profile["scope"])["budget"]["dispatched_calls"], 1)
        before = {name: fiction_budget.snapshot(profile["scope"]) for name, profile in self.config["profiles"].items()}
        fiction = SnapshotStore(self.root / "data/fictional-workspaces/onboarding/state.json", state, namespace="a" * 64)
        fiction.save(); fiction.load(); fiction.save()
        self.assertEqual({name: fiction_budget.snapshot(profile["scope"]) for name, profile in self.config["profiles"].items()}, before)
        self.assertEqual(personal.read_bytes(), original)
        self.tokens.assert_not_called()
        self.transport.post.assert_not_called()
        self.assertEqual(self.transport.calls, [])

    def test_private_providers_use_distinct_durable_scopes_and_content_free_logs(self):
        from services.resume_intake_runtime import SYNTHESIS_SCHEMA
        providers = self.app.config["RESUME_PRIVATE_ASSISTANCE_SERVICE"].providers
        for name in ("synthesis", "interview"):
            providers[name](owner=self.identity.owner, request_id=str(uuid4()), instructions="Fictional test",
                            task="DO-NOT-LOG-MY-DOCUMENT", context={}, response_schema=SYNTHESIS_SCHEMA)
            self.assertEqual(self.budget.snapshot("test-" + name)["budget"]["dispatched_calls"], 1)
            self.assertFalse(self.budget.has_active(["test-" + name]))
        self.assertEqual(self.tokens.call_count, 2)
        events = (self.root / "logs/provider-usage.jsonl").read_text()
        self.assertNotIn("DO-NOT-LOG", events)
        self.assertNotIn("offline-placeholder", events)
        self.assertEqual(len(events.splitlines()), 2)

    def test_foreign_owner_cannot_consume_private_ai_or_request_credentials(self):
        from services.resume_intake_runtime import SYNTHESIS_SCHEMA
        from services.ai_foundation.errors import ProviderUnavailableError
        provider = self.app.config["RESUME_PRIVATE_ASSISTANCE_SERVICE"].providers["interview"]
        with self.assertRaises(ProviderUnavailableError):
            provider(owner=str(uuid4()), request_id=str(uuid4()), instructions="Fiction", task="Help",
                     context={}, response_schema=SYNTHESIS_SCHEMA)
        self.tokens.assert_not_called()
        self.assertEqual(self.transport.calls, [])

    def test_private_interview_and_extraction_do_not_silently_use_fixture_answers(self):
        self.transport.payload = {"response": "Tell me about your contribution.", "next_question": "What did you document?", "candidates": []}
        service = self.app.config["RESUME_PRIVATE_ASSISTANCE_SERVICE"]
        before = self.state.capture()
        result = service.interview(self.identity.owner, {"request_id": str(uuid4()), "expected_draft_version": 0,
                                                        "statement": "I documented a class prototype."})
        self.assertFalse(result["saved"])
        self.assertEqual(len(self.transport.calls), 1)
        self.transport.payload = {"candidates": []}
        from types import SimpleNamespace
        self.fixture.intake._extract_with_adapter(self.identity.owner, SimpleNamespace(source_text="I documented a class prototype."))
        self.assertEqual(len(self.transport.calls), 2)
        self.assertEqual(self.budget.snapshot("test-extraction")["budget"]["dispatched_calls"], 1)
        self.assertEqual(self.state.capture(), before)

    def test_configuration_hash_claim_cannot_replace_bound_allocation_bytes(self):
        from tools.local_reviewer.providers import ALLOCATION_SHA256, ONGOING_BINDINGS, load_configuration
        config = {**self.config, "allocation_sha256": ALLOCATION_SHA256}
        (self.root / "live-ai.json").write_text(json.dumps(config))
        (self.root / "ai-allocation.json").write_text(json.dumps({"profiles": config["profiles"]}))
        factory = self.root / "ai-factory.json"
        factory.write_text(json.dumps({**config["factory"], "ongoing_budget_port": ONGOING_BINDINGS}))
        with patch("tools.local_reviewer.providers.FACTORY_SHA256", sha256(factory.read_bytes()).hexdigest()):
            with self.assertRaisesRegex(ValueError, "binding changed"):
                load_configuration(self.root, self.identity, SOURCE)

    def test_speech_decodes_audio_and_reserves_for_private_owner_before_credentials(self):
        from io import BytesIO
        import wave
        from types import SimpleNamespace
        from tools.local_reviewer.providers import build_native_speech_port
        audio = BytesIO()
        with wave.open(audio, "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(8000)
            output.writeframes(b"\0\0" * 8000)
        session = Mock()
        session.post.return_value = SimpleNamespace(status_code=200, headers={"apim-request-id": "offline-speech"},
            json=lambda: {"combinedPhrases": [{"text": "Fictional planning contribution."}], "durationMilliseconds": 1000})
        def token():
            self.assertTrue(self.budget.has_active(["test-speech"]))
            return "offline-placeholder"
        port = build_native_speech_port(database=self.budget, token_provider=token, owner=self.identity.owner,
                                        profile=self.config["profiles"]["speech"], session=session)
        validated = port.adapter.admit_bytes("audio/wav", audio.getvalue(), 50.0, port.policy)
        self.assertEqual(validated.duration_seconds, 1.0)
        with port.owner_scope(self.identity.owner, str(uuid4())):
            self.assertTrue(port.adapter.transcribe(validated, port.policy).ok)
        session.post.assert_called_once()
        snapshot = self.budget.snapshot("test-speech")
        self.assertEqual(snapshot["reservations"][0]["owner"], self.identity.owner)
        self.assertEqual(snapshot["reservations"][0]["state"], "finished")

    def test_private_upload_persists_originals_and_never_logs_document_text(self):
        import io
        import threading
        from werkzeug.test import Client
        from werkzeug.wrappers import Response
        from tools.local_reviewer.runtime import Boundary
        from tools.local_reviewer.persistence import SnapshotStore
        from dataclasses import asdict
        (self.root / "private-access.json").write_text(json.dumps(asdict(self.identity)))
        self.identity.bind_principal(self.stack)
        store = SnapshotStore(self.root / "data/state.json", self.state)
        store.save()
        initial = self.state.capture()
        boundary = Boundary(self.fixture, self.app, {r.endpoint for r in self.app.url_map.iter_rules()
                            if r.endpoint.startswith("resume_intake.")}, store, self.root,
                            {"port": 53720}, "test-control", threading.Event())
        client = Client(boundary, Response)
        document = b"FICTIONAL PRIVATE DOCUMENT. I documented a class prototype."
        response = client.post("/api/resume-intake/me/submissions", base_url=self.identity.origin,
            environ_base={"REMOTE_ADDR": "127.0.0.1"}, headers={"Origin": self.identity.origin,
            "X-Forwarded-Host": "test.example.ts.net:8443", "X-Forwarded-Proto": "https",
            "Tailscale-User-Login": self.identity.login, "X-PeerSlate-Request": "same-origin"},
            content_type="multipart/form-data", data={"request": json.dumps({"type": "add_submission",
                "request_id": str(uuid4()), "attachments": [{"client_key": "d1", "kind": "document",
                "declared_content_type": "text/plain", "filename": "fictional-resume.txt"}]}),
                "file:d1": (io.BytesIO(document), "fictional-resume.txt", "text/plain")})
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        self.assertEqual(len(self.transport.calls), 1)
        self.assertEqual(len(self.fixture.intake.original_files.list(self.identity.owner)), 1)
        persisted = self.state.capture()
        self.state.restore(initial)
        store.load()
        self.assertEqual(self.state.capture(), persisted)
        self.assertEqual(len(self.fixture.intake.original_files.list(self.identity.owner)), 1)
        self.assertEqual(self.fixture.intake.original_files.list(str(uuid4())), [])
        self.assertNotIn("FICTIONAL PRIVATE DOCUMENT", (self.root / "logs/provider-usage.jsonl").read_text())

    def test_azure_cli_errors_do_not_expose_captured_token_or_diagnostics(self):
        from types import SimpleNamespace
        from tools.local_reviewer.providers import azure_cli_token_callback
        from services.ai_foundation.errors import ProviderUnavailableError
        with patch("shutil.which", return_value="az.cmd"), patch("subprocess.run", return_value=SimpleNamespace(
            returncode=1, stdout="fictional-token", stderr="fictional-private-provider-error")) as run:
            callback = azure_cli_token_callback()
            run.assert_not_called()
            with self.assertRaises(ProviderUnavailableError) as caught:
                callback()
            self.assertNotIn("fictional-token", str(caught.exception))
            self.assertNotIn("fictional-private", str(caught.exception))

    def test_private_setup_creates_one_identity_and_never_reinitializes_its_budget(self):
        from types import SimpleNamespace
        from tools.local_reviewer.providers import ONGOING_BINDINGS
        from tools.local_reviewer.manager import setup_private, require_private_files
        from tools.local_reviewer.persistence import SnapshotStore
        from tools.local_reviewer.runtime import build_fixture
        target = self.root / "setup-test"
        target.mkdir()
        (target / "installation.json").write_text(json.dumps({"installation": "test"}))
        SnapshotStore(target / "data/state.json", self.state).save()
        allocation = {"ledger_path": str(target / "data/provider-budget-v1.sqlite3"), "profiles": self.config["profiles"]}
        allocation_file, factory_file = self.root / "allocation-test.json", self.root / "factory-test.json"
        allocation_file.write_text(json.dumps(allocation))
        factory_file.write_text(json.dumps({**self.config["factory"], "ongoing_budget_port": ONGOING_BINDINGS}))
        def documents(path, expected):
            return allocation if "allocation" in Path(path).name else {**self.config["factory"], "ongoing_budget_port": ONGOING_BINDINGS}
        args = SimpleNamespace(origin=self.identity.origin, login=self.identity.login,
                               allocation=allocation_file, factory=factory_file)
        with patch("tools.local_reviewer.manager.verify_release", return_value=target), \
                patch("tools.local_reviewer.runtime.build_fixture", side_effect=lambda _source, stack: build_fixture(SOURCE, stack)), \
                patch("tools.local_reviewer.manager.owned_status", return_value={"running": False}), \
                patch("tools.local_reviewer.manager.private_permissions"), \
                patch("tools.local_reviewer.providers.FACTORY_SHA256", sha256(factory_file.read_bytes()).hexdigest()), \
                patch("tools.local_reviewer.providers.bound_document", side_effect=documents), \
                patch("tools.local_reviewer.providers.azure_cli_token_callback", return_value=self.tokens):
            result = setup_private(target, args)
            self.assertTrue(result["private_profile_configured"])
            require_private_files(target)
            original = (target / "live-ai.json").read_bytes()
            with self.assertRaises(ValueError):
                setup_private(target, args)
            self.assertEqual((target / "live-ai.json").read_bytes(), original)
            self.tokens.assert_not_called()
            (target / "data/state.json").rename(target / "data/preserved-state.json")
            with self.assertRaisesRegex(ValueError, "automatic reset refused"):
                require_private_files(target)

    def test_private_seventh_call_uses_validated_usage_and_wire_refusal_precedes_reservation(self):
        from services.resume_intake_runtime import SYNTHESIS_SCHEMA, SynthesisError
        provider = self.app.config["RESUME_PRIVATE_ASSISTANCE_SERVICE"].providers["interview"]
        for _ in range(7):
            provider(owner=self.identity.owner, request_id=str(uuid4()), instructions="Fiction", task="Help",
                     context={}, response_schema=SYNTHESIS_SCHEMA)
        self.assertEqual(self.tokens.call_count, 7)
        self.assertEqual(self.budget.snapshot("test-interview")["budget"]["settled_micro_usd"], 560)
        with self.assertRaises(SynthesisError):
            provider(owner=self.identity.owner, request_id=str(uuid4()), instructions="x" * 65537, task="Help",
                     context={}, response_schema=SYNTHESIS_SCHEMA)
        self.assertEqual(self.tokens.call_count, 7)
        self.assertEqual(self.budget.snapshot("test-interview")["budget"]["dispatched_calls"], 7)

    def test_transport_observation_then_foundation_failure_keeps_uncertain_reservation(self):
        from types import SimpleNamespace
        from services.resume_intake_runtime import SYNTHESIS_SCHEMA
        from services.ai_foundation.errors import ProviderUnavailableError
        provider = self.app.config["RESUME_PRIVATE_ASSISTANCE_SERVICE"].providers["interview"]
        self.transport.post = Mock(return_value=SimpleNamespace(status_code=200, json=lambda: {
            "model": "eval0930-gpt-6-sol", "id": "resp_badoutput", "status": "completed",
            "usage": {"input_tokens": 4, "output_tokens": 4}, "output": []}))
        with self.assertRaises(ProviderUnavailableError):
            provider(owner=self.identity.owner, request_id=str(uuid4()), instructions="Fiction", task="Help",
                     context={}, response_schema=SYNTHESIS_SCHEMA)
        state = self.budget.snapshot("test-interview")
        self.assertEqual(state["budget"]["prepaid_micro_usd"], 824320)
        self.assertEqual(state["budget"]["settled_micro_usd"], 0)
        self.assertTrue(self.budget.has_active(["test-interview"]))
        self.assertEqual(self.tokens.call_count, 1)



    def actual_private_visitor_client(self):
        """Use the real request-derived fixture identity, not a static owner stub."""
        import threading
        from dataclasses import asdict
        from types import SimpleNamespace
        from werkzeug.test import Client
        from werkzeug.wrappers import Response
        from tools.local_reviewer.runtime import Boundary
        from tools.local_reviewer.persistence import SnapshotStore
        self.identity.bind_principal(self.stack)
        (self.root / "private-access.json").write_text(json.dumps(asdict(self.identity)))
        store = SnapshotStore(self.root / "data/state.json", self.state)
        store.save()
        boundary = Boundary(self.fixture, self.app, {r.endpoint for r in self.app.url_map.iter_rules()},
                            store, self.root, {"port": 53720}, "offline-control", threading.Event())
        client = Client(boundary, Response)
        options = {"base_url": self.identity.origin, "environ_base": {"REMOTE_ADDR": "127.0.0.1"},
            "headers": {"Origin": self.identity.origin, "X-Forwarded-Host": "test.example.ts.net:8443",
                "X-Forwarded-Proto": "https", "Tailscale-User-Login": self.identity.login,
                "X-PeerSlate-Request": "same-origin"}}
        text = "Reviewed twelve fictional inventory records."
        seed = {"type": "add_submission", "request_id": str(uuid4()), "items": [{
            "client_key": "fictional-role", "record_type": "role", "values": {
                "role_title": "Fictional QA Coordinator", "employer_name": "Fictional Acorn Lab",
                "location_text": None, "summary": text, "start_date": "2023-01-01", "end_date": None,
                "date_precision": "month", "employment_type": "full_time", "current_role": True}}]}
        response = client.post("/api/resume-intake/me/submissions", **options,
                               content_type="multipart/form-data", data={"request": json.dumps(seed)})
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        response.close()
        response = client.get("/api/resume/me/visitor-preview/sources", **options)
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        choices = response.get_json()
        response.close()
        self.assertEqual(len(choices["choices"]), 1)
        def post(url, **kwargs):
            wire = json.loads(kwargs["json"]["input"])
            if ":support" in wire["request"]["request_id"]:
                output = {"verdict": "supported", "summary_supported": True,
                          "claims": [{"claim_id": "c1", "supported": True}]}
            else:
                source = wire["sources"][0]
                start = source["content"].index(text)
                output = {"answer_id": wire["request"]["request_id"], "state": "supported", "summary": text,
                    "claims": [{"claim_id": "c1", "text": text, "kind": "evidence", "state": "supported",
                        "limitation": None, "citations": [{"claim_id": "c1", "source_version_key": source["source_version_key"],
                            "start": start, "end": start + len(text), "excerpt": text}]}],
                    "follow_up_questions": [], "handoff": None, "model_name": None, "prompt_contract_version": None}
            native = {"id": "resp_" + uuid4().hex, "status": "completed", "model": "gpt-6-luna",
                "usage": {"input_tokens": 10, "output_tokens": 10},
                "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(output)}]}]}
            return SimpleNamespace(status_code=200, json=lambda: native)
        self.transport.post = Mock(side_effect=post)
        payload = {"question": "What contribution is established?", "draft_revision": choices["draft_revision"],
                   "choices": [{"entry_key": choices["choices"][0]["entry_key"], "selected": True}]}
        return client, options, payload

    def test_actual_private_http_context_survives_all_currentness_fences_and_citation_read(self):
        client, options, payload = self.actual_private_visitor_client()
        response = client.post("/api/resume/me/visitor-preview/questions", **options, json=payload)
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        result = response.get_json()
        self.assertEqual(result["state"], "supported")
        self.assertEqual(len(result["citations"]), 1)
        response.close()
        self.assertFalse(self.budget.has_active(["test-public"]))
        self.assertEqual(self.budget.snapshot("test-public")["budget"]["settled_micro_usd"], 140)
        citation = client.get(result["citations"][0]["url"], **options)
        self.assertEqual(citation.status_code, 200, citation.get_data(as_text=True))
        citation.close()
        wrong = {**options, "headers": {**options["headers"], "Tailscale-User-Login": "other@example.test"}}
        denied = client.post("/api/resume/me/visitor-preview/questions", **wrong, json=payload)
        self.assertEqual(denied.status_code, 403)
        denied.close()
        self.assertEqual(self.transport.post.call_count, 2)

    def test_actual_private_http_added_fence_still_refuses_changed_authority(self):
        from services.resume_publication_contracts import ReadState
        client, options, payload = self.actual_private_visitor_client()
        with patch.object(self.fixture.ai.currentness, "recheck", side_effect=[ReadState.CURRENT, ReadState.STALE]) as check:
            response = client.post("/api/resume/me/visitor-preview/questions", **options, json=payload)
            self.assertEqual(response.status_code, 503)
            response.close()
            self.assertEqual(check.call_count, 2)
        self.fixture.ai_runtime.close()
        self.assertTrue(self.budget.has_active(["test-public"]))
        self.assertEqual(self.budget.snapshot("test-public")["budget"]["prepaid_micro_usd"], 329728)
        self.assertEqual(self.budget.snapshot("test-public")["budget"]["settled_micro_usd"], 0)

    def test_actual_private_source_without_request_context_refuses_before_transport(self):
        from werkzeug.wrappers import Response
        from services.member_visitor_ai_service import OperationalRefusal
        _, _, payload = self.actual_private_visitor_client()
        source = self.fixture.ai_runtime.source
        with self.app.test_request_context("/", environ_overrides={"local_reviewer.private_owner": self.identity.owner}):
            binding = source.prepare_preview(expected_draft_revision=payload["draft_revision"],
                choices=tuple((c["entry_key"], c["selected"]) for c in payload["choices"]))
        with self.assertRaises(OperationalRefusal):
            self.fixture.ai_runtime.run_response(lambda: self.fixture.ai.ask_preview(binding=binding,
                question="What is established?", request_id=str(uuid4())), lambda _: Response("bad"), client_key="no-context")
        self.fixture.ai_runtime.close()
        self.transport.post.assert_not_called()
        self.assertTrue(self.budget.has_active(["test-public"]))

    def public_operation(self, *, phases=2, preview=True):
        from types import SimpleNamespace
        from services.member_visitor_ai_repository import SqlMemberVisitorAiRepository
        from tests.test_member_visitor_ai_repository import SnapshotDatabase
        from tests.test_member_visitor_ai_sources import snapshot, SAVED_TEXT
        from tools.local_reviewer.providers import BoundPublicSources
        document = snapshot(owner=self.identity.owner, preview=preview)
        source_db = SnapshotDatabase(document)
        repo = SqlMemberVisitorAiRepository(source_db,
            identity=SimpleNamespace(current_owner_key=lambda: self.identity.owner))
        binding = repo.prepare_preview(expected_draft_revision=2, choices=(("entry-a", phases != 0),)) if preview else None
        service, runtime = self.fixture.ai, self.fixture.ai_runtime
        service.sources, service.currentness = BoundPublicSources(repo, self.fixture.private_public_port), repo
        runtime.source = repo
        def post(url, **kwargs):
            wire = json.loads(kwargs["json"]["input"])
            if ":support" in wire["request"]["request_id"]:
                output = {"verdict": "supported", "summary_supported": True,
                          "claims": [{"claim_id": "c1", "supported": True}]}
            else:
                source = wire["sources"][0]
                start = source["content"].index(SAVED_TEXT)
                output = {"answer_id": "answer1", "state": "not_established" if phases == 1 else "supported",
                    "summary": "Unknown" if phases == 1 else SAVED_TEXT,
                    "claims": [] if phases == 1 else [{"claim_id": "c1", "text": SAVED_TEXT, "kind": "evidence",
                        "state": "supported", "limitation": None, "citations": [{"claim_id": "c1",
                            "source_version_key": source["source_version_key"], "start": start,
                            "end": start + len(SAVED_TEXT), "excerpt": SAVED_TEXT}]}],
                    "follow_up_questions": [], "handoff": None, "model_name": None, "prompt_contract_version": "v1"}
            payload = {"id": "resp_" + uuid4().hex, "status": "completed", "model": "gpt-6-luna",
                "usage": {"input_tokens": 10, "output_tokens": 10},
                "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(output)}]}]}
            return SimpleNamespace(status_code=200, json=lambda: payload)
        self.transport.post = Mock(side_effect=post)
        callback = ((lambda: service.ask_preview(binding=binding, question="What is established?", request_id=str(uuid4())))
                    if preview else (lambda: service.ask_guest(slug="private-test", question="What is established?", request_id=str(uuid4()))))
        return callback, source_db

    def test_public_two_phase_response_keeps_private_reservation_until_close(self):
        from werkzeug.wrappers import Response
        callback, _ = self.public_operation(phases=2)
        response = self.fixture.ai_runtime.run_response(callback, lambda value: Response(value.state.value), client_key="private")
        self.assertEqual(response.get_data(as_text=True), "supported")
        self.assertTrue(self.budget.has_active(["test-public"]))
        self.assertEqual(self.budget.snapshot("test-public")["budget"]["prepaid_micro_usd"], 329728)
        response.close()
        self.assertFalse(self.budget.has_active(["test-public"]))
        self.assertEqual(self.transport.post.call_count, 2)
        self.assertEqual(self.budget.snapshot("test-public")["budget"]["settled_micro_usd"], 140)

    def test_public_one_phase_uses_only_actual_phase_and_can_exceed_six_questions(self):
        from werkzeug.wrappers import Response
        callback, _ = self.public_operation(phases=1)
        for _ in range(7):
            response = self.fixture.ai_runtime.run_response(callback, lambda value: Response(value.state.value), client_key="private")
            self.assertEqual(response.get_data(as_text=True), "unsupported")
            response.close()
        self.assertEqual(self.transport.post.call_count, 7)
        self.assertEqual(self.budget.snapshot("test-public")["budget"]["settled_micro_usd"], 490)

    def test_public_authorized_empty_source_consumes_call_but_no_money_after_close(self):
        from werkzeug.wrappers import Response
        callback, _ = self.public_operation(phases=0)
        for _ in range(2):
            response = self.fixture.ai_runtime.run_response(callback, lambda value: Response(value.state.value), client_key="private")
            self.assertEqual(response.get_data(as_text=True), "unsupported")
            self.assertTrue(self.budget.has_active(["test-public"]))
            response.close()
        self.tokens.assert_not_called()
        self.transport.post.assert_not_called()
        snapshot = self.budget.snapshot("test-public")
        self.assertEqual(snapshot["budget"]["settled_micro_usd"], 0)
        self.assertEqual(snapshot["budget"]["dispatched_calls"], 2)
        self.assertFalse(self.budget.has_active(["test-public"]))

    def test_public_source_failure_caught_by_service_is_not_zero_completion(self):
        from werkzeug.wrappers import Response
        from services.member_visitor_ai_service import OperationalRefusal
        callback, source_db = self.public_operation(phases=0)
        source_db.fail = True
        with self.assertRaises(OperationalRefusal):
            self.fixture.ai_runtime.run_response(callback, lambda value: Response(value.state.value), client_key="private")
        self.fixture.ai_runtime.close()
        self.assertTrue(self.budget.has_active(["test-public"]))
        self.tokens.assert_not_called()

    def test_public_finalizer_failure_keeps_native_cost_fully_reserved(self):
        callback, _ = self.public_operation(phases=1)
        with self.assertRaises(ValueError):
            self.fixture.ai_runtime.run_response(callback, Mock(side_effect=ValueError("finalizer")), client_key="private")
        self.fixture.ai_runtime.close()
        self.assertEqual(self.budget.snapshot("test-public")["budget"]["prepaid_micro_usd"], 329728)
        self.assertTrue(self.budget.has_active(["test-public"]))

    def test_public_final_deadline_failure_cannot_use_earlier_success(self):
        from werkzeug.wrappers import Response
        from services.member_visitor_ai_service import OperationalRefusal
        callback, _ = self.public_operation(phases=0)
        clock = [0]
        def finalizer(value):
            clock[0] = 1000
            return Response(value.state.value)
        with patch("services.member_visitor_ai_service.monotonic", side_effect=lambda: clock[0]):
            with self.assertRaises(OperationalRefusal):
                self.fixture.ai_runtime.run_response(callback, finalizer, client_key="private")
        self.fixture.ai_runtime.close()
        self.assertTrue(self.budget.has_active(["test-public"]))
        self.assertEqual(self.budget.snapshot("test-public")["budget"]["settled_micro_usd"], 0)

    def test_read_only_route_does_not_reserve_and_cannot_dispatch_native_credentials(self):
        from werkzeug.wrappers import Response
        from services.ai_foundation.errors import ProviderUnavailableError
        from flask import request
        runtime = self.fixture.ai_runtime
        with self.app.test_request_context("/api/resume/me/visitor-preview/sources", method="GET"):
            self.assertEqual(request.endpoint, "resume_publication.preview_ai_sources")
            for _ in range(8):
                response = runtime.run_response(lambda: None, lambda _: Response("sources"), client_key="read")
                response.close()
            with self.assertRaises(ProviderUnavailableError):
                runtime.run_response(self.fixture.private_public_port.token_provider, lambda _: Response("bad"), client_key="read")
        self.tokens.assert_not_called()
        self.assertEqual(self.budget.snapshot("test-public")["budget"]["dispatched_calls"], 0)

    def citation_route_case(self, *, preview):
        from werkzeug.wrappers import Response
        from tests.test_member_visitor_ai_sources import SAVED_TEXT
        callback, source_db = self.public_operation(phases=2, preview=preview)
        self.identity.bind_principal(self.stack)
        captured = {}
        def answer():
            captured["answer"] = callback()
            return captured["answer"]
        response = self.fixture.ai_runtime.run_response(answer, lambda value: Response(value.state.value), client_key="citation")
        self.assertEqual(response.get_data(as_text=True), "supported")
        response.close()
        handle = captured["answer"].citations[0].handle
        path = ("/api/resume/me/visitor-preview/citations/" if preview
                else "/api/public/profiles/private-test/ai/citations/") + handle
        client = self.app.test_client()
        # The separately tested private edge supplies this server-only binding.
        client.environ_base["local_reviewer.private_owner"] = self.identity.owner
        before = self.budget.snapshot("test-public")
        valid = client.get(path)
        self.assertEqual(valid.status_code, 200, valid.get_data(as_text=True))
        self.assertEqual(valid.get_json()["excerpt"], SAVED_TEXT)
        if preview:
            identity = self.fixture.ai.sources.source.identity
            identity.current_owner_key = lambda: str(uuid4())
            foreign = client.get(path)
            identity.current_owner_key = lambda: self.identity.owner
        else:
            foreign = client.get(path.replace("/private-test/", "/foreign-member/"))
        self.assertEqual(foreign.status_code, 404)
        self.assertNotIn(SAVED_TEXT, foreign.get_data(as_text=True))
        source_db.document["sharing_epoch"] += 1
        stale = client.get(path)
        self.assertEqual(stale.status_code, 404)
        self.assertNotIn(SAVED_TEXT, stale.get_data(as_text=True))
        self.assertEqual(self.budget.snapshot("test-public"), before)
        self.assertEqual(self.tokens.call_count, 2)
        self.assertEqual(self.transport.post.call_count, 2)

    def test_actual_preview_citation_route_keeps_valid_foreign_and_stale_authority(self):
        self.citation_route_case(preview=True)

    def test_actual_guest_citation_route_keeps_valid_foreign_and_stale_authority(self):
        self.citation_route_case(preview=False)

    def test_read_context_refuses_native_transport_even_with_a_prior_native_lease(self):
        from werkzeug.wrappers import Response
        from services.ai_foundation.errors import ProviderUnavailableError
        from tools.local_reviewer.providers import _CURRENT
        runtime, port = self.fixture.ai_runtime, self.fixture.private_public_port
        lease = port.reserve("native", runtime.limits)
        old_context = _CURRENT.get()
        def unexpected_transport():
            token = _CURRENT.set(old_context)
            try:
                return port.post("https://peerslate-foundry.openai.azure.com/openai/v1/responses",
                                 headers={}, json={}, timeout=(1, 1))
            finally:
                _CURRENT.reset(token)
        with self.app.test_request_context("/api/resume/me/visitor-preview/citations/fake", method="GET"):
            with self.assertRaises(ProviderUnavailableError):
                runtime.run_response(unexpected_transport, lambda value: Response("bad"), client_key="read")
        port.release(lease)
        self.tokens.assert_not_called()
        self.assertEqual(self.transport.calls, [])
        self.assertTrue(self.budget.has_active(["test-public"]))

    def test_public_third_phase_is_refused_and_remains_fenced(self):
        from werkzeug.wrappers import Response
        from services.ai_foundation.errors import ProviderUnavailableError
        callback, _ = self.public_operation(phases=2)
        def third():
            callback()
            self.fixture.private_public_port.token_provider()
        with self.assertRaises(ProviderUnavailableError):
            self.fixture.ai_runtime.run_response(third, lambda value: Response("bad"), client_key="private")
        self.fixture.ai_runtime.close()
        self.assertEqual(self.transport.post.call_count, 2)
        self.assertEqual(self.tokens.call_count, 2)
        self.assertTrue(self.budget.has_active(["test-public"]))

    def test_public_credential_failure_with_no_http_keeps_full_reservation(self):
        from werkzeug.wrappers import Response
        from services.member_visitor_ai_service import OperationalRefusal
        callback, _ = self.public_operation(phases=1)
        self.tokens.side_effect = ValueError("credential unavailable")
        with self.assertRaises(OperationalRefusal):
            self.fixture.ai_runtime.run_response(callback, lambda value: Response("bad"), client_key="private")
        self.fixture.ai_runtime.close()
        self.transport.post.assert_not_called()
        self.assertTrue(self.budget.has_active(["test-public"]))

    def test_public_authority_change_before_finalizer_cannot_settle_zero(self):
        from werkzeug.wrappers import Response
        from services.member_visitor_ai_service import OperationalRefusal
        callback, database = self.public_operation(phases=0)
        def change():
            answer = callback()
            database.document["sharing_epoch"] += 1
            return answer
        finalizer = Mock(side_effect=lambda value: Response(value.state.value))
        with self.assertRaises(OperationalRefusal):
            self.fixture.ai_runtime.run_response(change, finalizer, client_key="private")
        self.fixture.ai_runtime.close()
        finalizer.assert_not_called()
        self.assertTrue(self.budget.has_active(["test-public"]))



    def test_public_timeout_remains_active_after_port_recreation(self):
        from tools.local_reviewer.providers import build_native_public_port
        from services.ai_foundation.errors import ProviderUnavailableError
        from services.member_visitor_ai_service import OperationalRefusal
        port, runtime = self.fixture.private_public_port, self.fixture.ai_runtime
        self.transport.post = Mock(side_effect=TimeoutError("Fictional timeout"))
        lease = port.reserve("private-test-client", runtime.limits)
        port.token_provider()
        with self.assertRaises(ProviderUnavailableError):
            port.post("https://peerslate-foundry.openai.azure.com/openai/v1/responses", headers={},
                      json={"model": "gpt-6-luna", "store": False, "max_output_tokens": 16384}, timeout=(1, 2))
        port.release(lease)
        restored = build_native_public_port(database=self.budget, token_provider=self.tokens, owner=self.identity.owner,
                                            profile=self.config["profiles"]["public"], transport=self.transport)
        with self.assertRaises(OperationalRefusal):
            restored.reserve("another-client", runtime.limits)
        self.assertEqual(self.tokens.call_count, 1)
        self.assertTrue(self.budget.has_active(["test-public"]))


class ProviderBudgetTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "provider.sqlite3"
        self.owner = str(uuid4())
        self.profiles = {name: {"scope": "test-" + name, "maximum_calls": 100,
                               "hard_cap_micro_usd": 60, "reservation_micro_usd": 10,
                               "concurrent_requests": 1, "input_tokens": 10, "output_tokens": 0,
                               "input_micro_usd_per_million": 1000000, "output_micro_usd_per_million": 1000000}
                         for name in ("interview", "extraction", "synthesis", "public", "speech")}
        self.arguments = dict(owner=self.owner, allocation_sha256="a" * 64, profiles=self.profiles)
        self.budget = ProviderBudget.initialize(self.path, **self.arguments)

    def reserve(self, request, *, owner=None, scope="test-extraction", maximum=100):
        return self.budget.first_row(RESERVE, [("@UserKey", owner or self.owner), ("@Scope", scope),
            ("@RequestId", request), ("@ReservationMicroUsd", 10), ("@MaximumCalls", maximum),
            ("@HardCapMicroUsd", 60), ("@ConcurrentRequests", 1)])["reserved"]

    def finish(self, request, *, owner=None):
        from tools.local_reviewer.provider_budget import identity_digest
        try:
            self.budget.settle(owner or self.owner, "test-extraction", request,
                [{"phase": 1, "identity_sha256": identity_digest(request), "input_tokens": 2, "output_tokens": 0}])
            return True
        except ValueError:
            return False

    def test_uncertainty_survives_reopen_and_blocks_another_dispatch(self):
        request = str(uuid4())
        self.assertTrue(self.reserve(request))
        self.budget = ProviderBudget(self.path, **self.arguments)
        self.assertFalse(self.reserve(str(uuid4())))
        self.assertFalse(self.reserve(request))
        self.assertTrue(self.budget.has_active(["test-extraction"]))
        self.assertEqual(self.budget.snapshot("test-extraction")["budget"]["dispatched_calls"], 1)

    def test_more_than_six_complete_then_refuse_exactly_when_next_reservation_cannot_fit(self):
        for _ in range(26):
            request = str(uuid4())
            self.assertTrue(self.reserve(request))
            self.assertTrue(self.finish(request))
            self.assertTrue(self.finish(request))
        self.budget = ProviderBudget(self.path, **self.arguments)
        self.assertFalse(self.reserve(str(uuid4())))
        snapshot = self.budget.snapshot("test-extraction")["budget"]
        self.assertEqual((snapshot["dispatched_calls"], snapshot["prepaid_micro_usd"]), (26, 52))

    def test_other_owner_or_new_scope_cannot_use_or_expand_allocation(self):
        self.assertFalse(self.reserve(str(uuid4()), owner=str(uuid4())))
        self.assertFalse(self.reserve(str(uuid4()), scope="new-unallocated-scope"))
        self.assertFalse(self.reserve(str(uuid4()), maximum=101))
        request = str(uuid4())
        self.assertTrue(self.reserve(request))
        self.assertFalse(self.finish(request, owner=str(uuid4())))
        self.assertTrue(self.budget.has_active(["test-extraction"]))

    def test_changed_configuration_and_repeat_initialization_preserve_ledger(self):
        self.assertTrue(self.reserve(str(uuid4())))
        with self.assertRaises(FileExistsError):
            ProviderBudget.initialize(self.path, **self.arguments)
        changed = json.loads(json.dumps(self.profiles))
        changed["interview"]["scope"] = "a-new-scope"
        with self.assertRaises(ValueError):
            ProviderBudget(self.path, **{**self.arguments, "profiles": changed})
        self.assertEqual(self.budget.snapshot("test-extraction")["budget"]["dispatched_calls"], 1)

    def test_missing_ledger_is_not_recreated_during_startup(self):
        moved = self.path.with_suffix(".preserved")
        self.path.rename(moved)
        with self.assertRaises(ValueError):
            ProviderBudget(self.path, **self.arguments)
        self.assertFalse(self.path.exists())
        self.assertTrue(moved.exists())


    def event(self, request, count=2):
        from tools.local_reviewer.provider_budget import identity_digest
        return [{"phase": 1, "identity_sha256": identity_digest(request), "input_tokens": count, "output_tokens": 0}]

    def test_immutable_events_conflicting_replay_and_duplicate_native_id(self):
        import sqlite3
        first, second = str(uuid4()), str(uuid4())
        self.assertTrue(self.reserve(first))
        self.assertTrue(self.finish(first))
        with self.assertRaises(ValueError):
            self.budget.settle(self.owner, "test-extraction", first, self.event(first, 3))
        self.assertTrue(self.reserve(second))
        with self.assertRaises(ValueError):
            self.budget.settle(self.owner, "test-extraction", second, self.event(first))
        self.assertTrue(self.budget.has_active(["test-extraction"]))
        with closing(sqlite3.connect(self.path)) as db:
            for table in ("metadata", "reservations", "settlements", "native_responses", "releases"):
                with self.assertRaises(sqlite3.IntegrityError):
                    db.execute("DELETE FROM " + table)
        self.assertEqual(self.budget.snapshot("test-extraction")["budget"]["settled_micro_usd"], 2)

    def test_malformed_usage_and_known_overrun_never_reduce_encumbrance(self):
        request = str(uuid4())
        self.assertTrue(self.reserve(request))
        for count in (True, -1, 1.5, None):
            with self.subTest(count=count), self.assertRaises(ValueError):
                self.budget.settle(self.owner, "test-extraction", request, self.event(request, count))
        with self.assertRaises(ValueError):
            self.budget.settle(self.owner, "test-extraction", request, self.event(request, 11))
        state = self.budget.snapshot("test-extraction")
        self.assertEqual(state["overruns"][0]["observed_charge"], 11)
        self.assertEqual(state["budget"]["settled_micro_usd"], 0)
        self.assertFalse(self.reserve(str(uuid4())))

    def test_settlement_without_release_remains_active_across_restart(self):
        request = str(uuid4())
        self.assertTrue(self.reserve(request))
        self.budget.settle(self.owner, "test-extraction", request, self.event(request), release=False)
        self.budget = ProviderBudget(self.path, **self.arguments)
        self.assertTrue(self.budget.has_active(["test-extraction"]))
        self.assertFalse(self.reserve(str(uuid4())))
        self.budget.settle(self.owner, "test-extraction", request, self.event(request), release=True)
        self.assertFalse(self.budget.has_active(["test-extraction"]))
        self.assertEqual(self.budget.snapshot("test-extraction")["budget"]["settled_micro_usd"], 2)

    def test_partial_and_changed_allocation_fail_closed(self):
        import sqlite3
        partial = self.path.parent / "partial.sqlite3"
        partial.touch()
        with self.assertRaises(ValueError):
            ProviderBudget(partial, **self.arguments)
        changed = json.loads(json.dumps(self.profiles))
        changed["extraction"]["hard_cap_micro_usd"] += 1
        with self.assertRaises(ValueError):
            ProviderBudget(self.path, **{**self.arguments, "profiles": changed})
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("DROP TRIGGER immutable_reservations_DELETE")
            db.commit()
        with self.assertRaises(ValueError):
            ProviderBudget(self.path, **self.arguments)

    def test_two_real_processes_have_exactly_one_reservation_winner(self):
        import subprocess, sys
        config = self.path.parent / "configuration.json"
        config.write_text(json.dumps(self.arguments))
        barrier = self.path.parent / "go"
        script = """import json,sys,time
from pathlib import Path
from uuid import uuid4
from tools.local_reviewer.provider_budget import ProviderBudget
while not Path(sys.argv[3]).exists(): time.sleep(.01)
b=ProviderBudget(sys.argv[1],**json.loads(Path(sys.argv[2]).read_text()))
p=b.profiles['extraction']
print(b.reserve({'@UserKey':b.owner,'@Scope':p['scope'],'@RequestId':str(uuid4()),
'@ReservationMicroUsd':p['reservation_micro_usd'],'@MaximumCalls':p['maximum_calls'],
'@HardCapMicroUsd':p['hard_cap_micro_usd'],'@ConcurrentRequests':1}))
"""
        workers = [subprocess.Popen([sys.executable, "-B", "-c", script, str(self.path), str(config), str(barrier)],
                   cwd=SOURCE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(2)]
        try:
            barrier.touch()
            outputs = [worker.communicate(timeout=15) for worker in workers]
            self.assertEqual(sorted(out.strip() for out, err in outputs), ["False", "True"], outputs)
            self.assertTrue(all(worker.returncode == 0 for worker in workers), outputs)
        finally:
            for worker in workers:
                if worker.poll() is None:
                    worker.kill()
                    worker.wait()
        self.assertEqual(self.budget.snapshot("test-extraction")["budget"]["dispatched_calls"], 1)


    def test_failed_settlement_transaction_keeps_full_reservation(self):
        import sqlite3
        request = str(uuid4())
        self.assertTrue(self.reserve(request))
        original = sqlite3.connect
        class FailingCommit(sqlite3.Connection):
            def commit(self):
                raise sqlite3.OperationalError("simulated accounting failure")
        with patch("tools.local_reviewer.provider_budget.sqlite3.connect",
                   side_effect=lambda *args, **kwargs: original(*args, **kwargs, factory=FailingCommit)):
            with self.assertRaises(ValueError):
                self.budget.settle(self.owner, "test-extraction", request, self.event(request))
        self.budget = ProviderBudget(self.path, **self.arguments)
        state = self.budget.snapshot("test-extraction")
        self.assertEqual(state["budget"]["prepaid_micro_usd"], 10)
        self.assertEqual(state["budget"]["settled_micro_usd"], 0)
        self.assertTrue(self.budget.has_active(["test-extraction"]))

    def test_call_ceiling_still_applies_to_zero_token_completions(self):
        for _ in range(100):
            request = str(uuid4())
            self.assertTrue(self.reserve(request))
            self.budget.settle(self.owner, "test-extraction", request, self.event(request, 0))
        self.assertFalse(self.reserve(str(uuid4())))
        self.assertEqual(self.budget.snapshot("test-extraction")["budget"]["dispatched_calls"], 100)

    def test_explicit_public_zero_settlement_is_idempotent_and_conflicts_refuse(self):
        request = str(uuid4())
        self.assertTrue(self.reserve(request, scope="test-public"))
        with self.assertRaises(ValueError):
            self.budget.settle(self.owner, "test-public", request, [])
        self.budget.settle(self.owner, "test-public", request, [], zero_completion=True)
        self.budget.settle(self.owner, "test-public", request, [], zero_completion=True)
        with self.assertRaises(ValueError):
            self.budget.settle(self.owner, "test-public", request, self.event(request))
        self.assertEqual(self.budget.snapshot("test-public")["budget"]["dispatched_calls"], 1)


class PrivateCompletionProofTests(unittest.TestCase):
    def test_structured_result_must_match_native_observation(self):
        from dataclasses import replace
        from types import SimpleNamespace
        from tools.local_reviewer.providers import OngoingPrivateBudgetPort, make_private_settings
        from services.ai_foundation.contracts import StructuredResult
        from services.ai_foundation.azure_foundry import RESPONSE_IDENTITY_CONFIGURED_DEPLOYMENT
        from services.ai_foundation.errors import ProviderUnavailableError
        mutations = {"wrong-request": {"request_id": str(uuid4())}, "wrong-schema": {"schema_name": "wrong"},
            "wrong-model": {"model_name": "gpt-6-luna"}, "wrong-deployment": {"deployment_name": "wrong"},
            "wrong-version": {"configured_model_version": "2026-01-01"}, "wrong-totals": {"input_tokens": 5},
            "bool-tokens": {"input_tokens": True}, "wrong-native-model": {"response_model_name": "gpt-6-luna"}}
        with tempfile.TemporaryDirectory() as folder:
            for index, (label, changes) in enumerate({**mutations, "matching": {}}.items()):
                with self.subTest(label=label):
                    owner, request = str(uuid4()), str(uuid4())
                    config = configuration(owner)
                    budget = ProviderBudget.initialize(Path(folder) / (str(index) + ".sqlite3"),
                        owner=owner, allocation_sha256="a" * 64, profiles=config["profiles"])
                    port = OngoingPrivateBudgetPort(budget, config["factory"])
                    settings = make_private_settings(config["factory"]["profile_contract"]["interview"], config["profiles"]["interview"])
                    self.assertIs(port.validate_profile(profile="interview", settings=settings, reservation=824320), True)
                    port.reserve(owner, request, settings["budget"], 824320)
                    result = StructuredResult(request_id=request, schema_name="resume_interview_v1",
                        model_name="gpt-6-sol", payload={"sentinel": "PRIVATE-DATA-NOT-ACCOUNTING"},
                        input_tokens=4, output_tokens=4, deployment_name="eval0930-gpt-6-sol",
                        configured_model_version="2026-09-22", response_model_name="eval0930-gpt-6-sol",
                        response_model_version=None, response_identity_source=RESPONSE_IDENTITY_CONFIGURED_DEPLOYMENT)
                    with self.assertRaises(ProviderUnavailableError):
                        port.settle_completed(owner, request, "test-interview", result)
                    port.credential(("interview",), lambda: "test-token")
                    port.before_dispatch("https://peerslate-foundry.openai.azure.com/openai/v1/responses", {
                        "model": "eval0930-gpt-6-sol", "store": False, "service_tier": "default",
                        "reasoning": {"effort": "low"}, "max_output_tokens": 32768,
                        "text": {"format": {"name": "resume_interview_v1"}}})
                    port.observe(SimpleNamespace(status_code=200, json=lambda: {
                        "id": "resp_" + request, "status": "completed", "model": "eval0930-gpt-6-sol",
                        "usage": {"input_tokens": 4, "output_tokens": 4}}))
                    if changes:
                        changed = replace(result)
                        for key, value in changes.items():
                            object.__setattr__(changed, key, value)
                        with self.assertRaises(ProviderUnavailableError):
                            port.settle_completed(owner, request, "test-interview", changed)
                        self.assertTrue(budget.has_active(["test-interview"]))
                    else:
                        port.settle_completed(owner, request, "test-interview", result)
                        port.settle_completed(owner, request, "test-interview", result)
                        self.assertFalse(budget.has_active(["test-interview"]))
                    self.assertNotIn("PRIVATE-DATA", budget.path.read_bytes().decode("latin1"))


class SpeechAccountingTests(unittest.TestCase):
    def test_duration_validation_rounding_and_decoded_lower_bound(self):
        from io import BytesIO
        import wave
        from types import SimpleNamespace
        from tools.local_reviewer.providers import build_native_speech_port
        scenarios = [({"duration": .1}, 1, 334), ({"durationMilliseconds": 1001}, 1, 667),
            ({"duration": 300}, 300, 100000), ({"duration": .5}, 1, 334),
            ({}, 1, None), ({"duration": True}, 1, None), ({"duration": float("nan")}, 1, None),
            ({"duration": float("inf")}, 1, None), ({"duration": -1}, 1, None),
            ({"durationMilliseconds": "invalid", "duration": 1}, 1, None), ({"duration": 301}, 1, None)]
        with tempfile.TemporaryDirectory() as folder:
            for index, (duration, decoded, expected) in enumerate(scenarios):
                with self.subTest(duration=duration):
                    owner, request = str(uuid4()), str(uuid4())
                    config = configuration(owner)
                    budget = ProviderBudget.initialize(Path(folder) / (str(index) + ".sqlite3"),
                        owner=owner, allocation_sha256="a" * 64, profiles=config["profiles"])
                    audio = BytesIO()
                    with wave.open(audio, "wb") as output:
                        output.setnchannels(1)
                        output.setsampwidth(2)
                        output.setframerate(8000)
                        output.writeframes(b"\0\0" * 8000 * decoded)
                    session, tokens = Mock(), Mock(return_value="PRIVATE-TOKEN")
                    session.post.return_value = SimpleNamespace(status_code=200,
                        headers={"apim-request-id": request}, json=lambda: {
                            "combinedPhrases": [{"text": "PRIVATE-TRANSCRIPT-SENTINEL"}], **duration})
                    port = build_native_speech_port(database=budget, token_provider=tokens, owner=owner,
                        profile=config["profiles"]["speech"], session=session)
                    validated = port.adapter.admit_bytes("audio/wav", audio.getvalue(), decoded, port.policy)
                    with port.owner_scope(owner, request):
                        result = port.adapter.transcribe(validated, port.policy)
                    state = budget.snapshot("test-speech")
                    self.assertEqual(result.ok, expected is not None)
                    self.assertEqual(state["budget"]["settled_micro_usd"], expected or 0)
                    self.assertEqual(budget.has_active(["test-speech"]), expected is None)
                    self.assertNotIn("PRIVATE-", budget.path.read_bytes().decode("latin1"))
                    tokens.assert_called_once()
                    session.post.assert_called_once()


if __name__ == "__main__":
    unittest.main()

class OperatorResolutionTests(unittest.TestCase):
    setUp = ProviderBudgetTests.setUp
    reserve = ProviderBudgetTests.reserve
    event = ProviderBudgetTests.event
    def recovery(self, original_request, **changes):
        values = dict(owner=self.owner, scope='test-public', request=original_request, amount=10,
            evidence={'proof_sha256':'b'*64, 'configuration_sha256':'c'*64, 'review_sha256':'d'*64})
        values.update(changes)
        return self.budget.resolve_failed_public(**values)

    def test_failure_charges_full_reservation_keeps_count_and_never_becomes_success(self):
        request = str(uuid4())
        self.assertTrue(self.reserve(request, scope='test-public'))
        self.recovery(request)
        self.recovery(request)
        self.budget = ProviderBudget(self.path, **self.arguments)
        state = self.budget.snapshot('test-public')
        self.assertEqual((state['budget']['dispatched_calls'], state['budget']['prepaid_micro_usd'],
                          state['budget']['settled_micro_usd'], state['budget']['failed_charge_micro_usd']), (1,10,0,10))
        self.assertEqual(state['reservations'][0]['state'], 'failed_operator_resolved')
        self.assertIsNone(state['reservations'][0]['charge'])
        self.assertFalse(self.budget.has_active(['test-public']))
        self.assertFalse(self.reserve(request, scope='test-public'))
        with self.assertRaises(ValueError):
            self.budget.settle(self.owner, 'test-public', request, self.event(request))
        with self.assertRaises(ValueError):
            self.recovery(request, evidence={'proof_sha256':'e'*64,'configuration_sha256':'c'*64,'review_sha256':'d'*64})
        for _ in range(5):
            next_request = str(uuid4())
            self.assertTrue(self.reserve(next_request, scope='test-public'))
            self.recovery(next_request)
        self.assertFalse(self.reserve(str(uuid4()), scope='test-public'))
        import sqlite3
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM native_responses').fetchone()[0], 0)
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute('DELETE FROM operator_resolutions')

    def test_refuses_wrong_binding_missing_partial_overrun_and_rolls_back_schema(self):
        request = str(uuid4())
        self.assertTrue(self.reserve(request, scope='test-public'))
        for changes in ({'owner':str(uuid4())},{'scope':'test-extraction'},{'amount':9},{'amount':True},
                        {'request':str(uuid4())},{'evidence':{} }):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.recovery(request, **changes)
        self.budget.settle(self.owner, 'test-public', request, self.event(request), release=False)
        with self.assertRaises(ValueError): self.recovery(request)
        import sqlite3
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 2)
        self.budget.settle(self.owner,'test-public', request,self.event(request))
        another = str(uuid4())
        self.assertTrue(self.reserve(another, scope='test-public'))
        self.budget.observe_overrun(self.owner,'test-public',another,self.event(another,11))
        with self.assertRaises(ValueError): self.recovery(another)
        self.assertTrue(self.budget.has_active(['test-public']))

    def test_failed_resolution_commit_preserves_v2_and_original_full_fence(self):
        import sqlite3
        request = str(uuid4())
        self.assertTrue(self.reserve(request, scope='test-public'))
        original = sqlite3.connect
        class FailingCommit(sqlite3.Connection):
            def commit(self): raise sqlite3.OperationalError('simulated resolution failure')
        with patch('tools.local_reviewer.provider_budget.sqlite3.connect',
                   side_effect=lambda *a, **kw: original(*a, **kw, factory=FailingCommit)):
            with self.assertRaises(ValueError): self.recovery(request)
        self.budget = ProviderBudget(self.path, **self.arguments)
        self.assertTrue(self.budget.has_active(['test-public']))
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],2)
            self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='operator_resolutions'").fetchone())

    def test_concurrent_operator_repeats_are_one_immutable_event(self):
        from concurrent.futures import ThreadPoolExecutor
        request = str(uuid4())
        self.assertTrue(self.reserve(request,scope='test-public'))
        with ThreadPoolExecutor(max_workers=2) as workers:
            results=list(workers.map(lambda _:self.recovery(request),range(2)))
        self.assertEqual(results[0],results[1])
        self.assertEqual(len(self.budget.snapshot('test-public')['operator_resolutions']),1)

    def test_schema_validation_uses_one_snapshot_during_atomic_upgrade(self):
        import sqlite3
        from concurrent.futures import ThreadPoolExecutor
        from threading import get_ident
        request = str(uuid4())
        self.assertTrue(self.reserve(request, scope='test-public'))
        original, reader = sqlite3.connect, get_ident()
        intercepted = []
        with ThreadPoolExecutor(max_workers=1) as worker:
            class ReadVersion:
                def __init__(self, cursor): self.cursor = cursor
                def fetchone(inner):
                    row = inner.cursor.fetchone()
                    self.assertEqual(row[0], 2)
                    # Commit the valid v3 upgrade after this reader has observed
                    # v2 but before it checks the tables and immutable triggers.
                    worker.submit(self.recovery, request).result(timeout=5)
                    return row
            class InterleavedRead(sqlite3.Connection):
                def execute(inner, sql, *args):
                    cursor = super().execute(sql, *args)
                    if sql == 'PRAGMA user_version' and get_ident() == reader and not intercepted:
                        intercepted.append(True)
                        return ReadVersion(cursor)
                    return cursor
            with patch('tools.local_reviewer.provider_budget.sqlite3.connect',
                       side_effect=lambda *a, **kw: original(*a, **kw, factory=InterleavedRead)):
                with self.budget.connection():
                    pass
        self.assertEqual(intercepted, [True])
        snapshot = self.budget.snapshot('test-public')
        self.assertEqual(len(snapshot['operator_resolutions']), 1)
        self.assertEqual(snapshot['budget']['dispatched_calls'], 1)
        self.assertFalse(self.budget.has_active(['test-public']))

    def test_one_shot_diagnostic_is_bound_and_never_captures_following_requests(self):
        from tools.local_reviewer.providers import PublicDiagnostic
        root=self.path.parent
        directory=root/'logs/public-diagnostic'
        directory.mkdir(parents=True)
        (directory/'armed.json').write_text(json.dumps({'owner':self.owner,'allocation_sha256':'a'*64,
            'scope':'test-public','previous_calls':0}))
        request=str(uuid4())
        self.assertTrue(self.reserve(request,scope='test-public'))
        diagnostic=PublicDiagnostic(root,self.budget)
        state={'request_id':request}
        diagnostic.claim(state)
        diagnostic.capture(state,{'phase':1,'wire':{'fictional':'source'},'native_response':{'status':'incomplete'}})
        diagnostic.capture(state,{'terminal':True,'uncertain':True})
        later={'request_id':str(uuid4())}
        diagnostic.claim(later)
        diagnostic.capture(later,{'phase':1,'private':'MUST-NOT-CAPTURE'})
        self.assertNotIn('diagnostic',later)
        self.assertNotIn('MUST-NOT-CAPTURE',(directory/'phase-1.json').read_text())
        self.assertFalse((directory/'armed.json').exists())
        with self.assertRaises(FileExistsError): diagnostic.capture(state,{'phase':1})

    def test_operator_live_listener_or_retained_worker_lock_refuses(self):
        from tools.local_reviewer.manager import private_operator, exclusive
        root=self.path.parent
        with patch('tools.local_reviewer.manager.read',return_value={}), \
             patch('tools.local_reviewer.manager.verify_release'), \
             patch('tools.local_reviewer.manager.require_private_files'), \
             patch('tools.local_reviewer.manager.owned_status',return_value={'running':True}):
            with self.assertRaises(ValueError), private_operator(root): pass
        with patch('tools.local_reviewer.manager.read',return_value={}), \
             patch('tools.local_reviewer.manager.verify_release'), \
             patch('tools.local_reviewer.manager.require_private_files'), \
             patch('tools.local_reviewer.manager.owned_status',return_value={'running':False}), exclusive(root,'server.lock'):
            with self.assertRaises(OSError), private_operator(root): pass

    def test_reviewed_proof_binding_is_required_before_any_operator_mutation(self):
        from tools.local_reviewer import manager
        from contextlib import contextmanager
        from types import SimpleNamespace
        root=self.path.parent
        request=str(uuid4())
        self.assertTrue(self.reserve(request,scope='test-public'))
        evidence={}
        for name in ('transport','outcome','shutdown'):
            file=root/(name+'.json'); file.write_text('{}'); evidence[str(file)]=manager.digest(file)
        proof={'schema_version':1,'installation':'test-installation','owner':self.owner,
            'allocation_sha256':'a'*64,'configuration_sha256':'c'*64,'scope':'test-public','request_id':request,
            'amount':10,'transport_quiescence':'synchronous_response_connection_closed',
            'original_worker_quiescence':'original_server_lifetime_lock_released','evidence_files':evidence}
        proof_path=root/'proof.json'; proof_path.write_text(json.dumps(proof))
        review={'schema_version':1,'result':'pass','proof_sha256':manager.digest(proof_path),
            'recovery_source_sha256':manager.operator_source_digest(),'reviewer_ref':'independent-test-reviewer'}
        review_path=root/'review.json'; review_path.write_text(json.dumps(review))
        @contextmanager
        def context(_root):
            yield {'installation':'test-installation'}, SimpleNamespace(owner=self.owner), {'allocation_sha256':'a'*64}, self.budget
        with patch.object(manager,'private_operator',context), patch.object(manager,'operator_configuration_digest',return_value='f'*64):
            with self.assertRaises(ValueError): manager.resolve_failed_public(root,proof_path,review_path)
        for key,value in (('result','pending'),('proof_sha256','f'*64),('recovery_source_sha256','f'*64)):
            review_path.write_text(json.dumps({**review,key:value}))
            with self.assertRaises(ValueError): manager.resolve_failed_public(root,proof_path,review_path)
        review_path.write_text(json.dumps(review))
        with patch.object(manager,'private_operator',context), patch.object(manager,'operator_configuration_digest',return_value='c'*64):
            result=manager.resolve_failed_public(root,proof_path,review_path)
        self.assertEqual(result['state'],'failed_operator_resolved')
        (root/'shutdown.json').write_text('{"changed":true}')
        with self.assertRaises(ValueError): manager.resolve_failed_public(root,proof_path,review_path)

    def test_explicit_next_diagnostic_keeps_previous_capture_and_never_overwrites_permit(self):
        from contextlib import contextmanager
        from types import SimpleNamespace
        from tools.local_reviewer import manager
        from tools.local_reviewer.providers import PublicDiagnostic
        root=self.path.parent;(root/'logs').mkdir()
        @contextmanager
        def context(_):
            yield {},SimpleNamespace(owner=self.owner), {'allocation_sha256':'a'*64,'profiles':self.profiles},self.budget
        with patch.object(manager,'private_operator',context):
            manager.arm_public_diagnostic(root)
            with self.assertRaises(ValueError): manager.arm_public_diagnostic(root)
            first=str(uuid4());self.assertTrue(self.reserve(first,scope='test-public'))
            diagnostic=PublicDiagnostic(root,self.budget);state={'request_id':first};diagnostic.claim(state)
            diagnostic.capture(state,{'phase':1,'fictional':'original evidence'})
            old_path=root/'logs/public-diagnostic/operation-1/phase-1.json';before=old_path.read_bytes()
            self.recovery(first)
            manager.arm_public_diagnostic(root)
            second=str(uuid4());self.assertTrue(self.reserve(second,scope='test-public'))
            state={'request_id':second};diagnostic.claim(state)
            diagnostic.capture(state,{'phase':1,'fictional':'new evidence'})
            self.assertEqual(old_path.read_bytes(),before)
            self.assertTrue((root/'logs/public-diagnostic/operation-2/phase-1.json').exists())
            self.recovery(second)
            third=str(uuid4());self.assertTrue(self.reserve(third,scope='test-public'))
            state={'request_id':third};diagnostic.claim(state)
            self.assertNotIn('diagnostic',state)
            self.assertFalse((root/'logs/public-diagnostic/operation-3').exists())
