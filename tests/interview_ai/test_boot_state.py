"""Consolidated B3: the boot-immutable Interview release state.

Ready-boot, invalid-boot, missing-config, and post-boot mutation: once a
process freezes its state, no configuration change, registry edit, or
evaluation-manifest change can alter what the running process serves —
only a restart (simulated by the test-only reset) re-runs verification.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-for-ci-only")

from services.interview_ai import boot

from tests.interview_ai.test_release_resolution import (
    RELEASE_ID,
    _scratch_release_root,
)


class BootStateTests(unittest.TestCase):
    def setUp(self):
        boot.reset_for_tests()
        self.addCleanup(boot.reset_for_tests)

    def test_ready_boot_freezes_the_verified_release(self):
        state = boot.initialize(RELEASE_ID)
        self.assertEqual(state.status, boot.READY)
        self.assertIsNotNone(state.release)
        self.assertEqual(state.release.release_set_id, RELEASE_ID)
        self.assertIs(boot.state(), state)

    def test_invalid_boot_freezes_service_not_configured(self):
        state = boot.initialize("f" * 64)
        self.assertEqual(state.status, boot.SERVICE_NOT_CONFIGURED)
        self.assertIsNone(state.release)
        # Fixing the configuration afterwards does NOT help: the frozen
        # state answers until the process restarts.
        self.assertIs(boot.initialize(RELEASE_ID), state)
        self.assertEqual(boot.state().status, boot.SERVICE_NOT_CONFIGURED)

    def test_missing_config_freezes_service_not_configured(self):
        state = boot.initialize(None)
        self.assertEqual(state.status, boot.SERVICE_NOT_CONFIGURED)
        self.assertIsNone(state.release)

    def test_boot_state_object_is_immutable(self):
        state = boot.initialize(None)
        with self.assertRaises(AttributeError):
            state.status = boot.READY
        with self.assertRaises(AttributeError):
            state.release = object()

    def test_post_boot_registry_mutation_cannot_alter_the_running_state(self):
        with tempfile.TemporaryDirectory() as scratch:
            scratch_root = _scratch_release_root(scratch)
            state = boot.initialize(RELEASE_ID, root=scratch_root)
            self.assertEqual(state.status, boot.READY)
            registry_path = (
                scratch_root / "prompts" / "interview" / "control"
                / "registry.json"
            )
            registry_path.write_text("{}", encoding="utf-8")
            self.assertIs(boot.initialize(RELEASE_ID, root=scratch_root), state)
            self.assertEqual(boot.state().status, boot.READY)
            self.assertIs(boot.state().release, state.release)

    def test_post_boot_evaluation_manifest_mutation_cannot_alter_state(self):
        with tempfile.TemporaryDirectory() as scratch:
            scratch_root = _scratch_release_root(scratch)
            state = boot.initialize(RELEASE_ID, root=scratch_root)
            self.assertEqual(state.status, boot.READY)
            manifest_path = (
                scratch_root / "prompts" / "interview" / "contracts"
                / "evaluation-set-1.json"
            )
            manifest_path.unlink()
            self.assertEqual(boot.state().status, boot.READY)
            # A restart (reset) DOES see the mutation and fails closed.
            boot.reset_for_tests()
            rebooted = boot.initialize(RELEASE_ID, root=scratch_root)
            self.assertEqual(rebooted.status, boot.SERVICE_NOT_CONFIGURED)

    def test_tampered_boot_stays_failed_after_restoration_until_restart(self):
        with tempfile.TemporaryDirectory() as scratch:
            scratch_root = _scratch_release_root(scratch)
            registry_path = (
                scratch_root / "prompts" / "interview" / "control"
                / "registry.json"
            )
            genuine = registry_path.read_text(encoding="utf-8")
            registry_path.write_text("{}", encoding="utf-8")
            state = boot.initialize(RELEASE_ID, root=scratch_root)
            self.assertEqual(state.status, boot.SERVICE_NOT_CONFIGURED)
            registry_path.write_text(genuine, encoding="utf-8")
            self.assertIs(boot.initialize(RELEASE_ID, root=scratch_root), state)
            boot.reset_for_tests()
            rebooted = boot.initialize(RELEASE_ID, root=scratch_root)
            self.assertEqual(rebooted.status, boot.READY)

    def test_absent_boot_state_answers_503_without_initializing(self):
        """B3 second round: a request against an unbooted process fails
        closed as service_not_configured and NEVER performs release
        initialization or file resolution."""
        import unittest.mock as mock
        import app as app_module
        from services import database_service as database_service_module
        from services import interview_ai
        limiter_was_enabled = app_module.limiter.enabled
        app_module.limiter.enabled = False
        try:
            with mock.patch.object(
                boot, "initialize",
                side_effect=AssertionError(
                    "a request invoked boot.initialize"
                ),
            ) as initialize_mock, mock.patch.object(
                database_service_module.database_service,
                "execute_procedure", new=lambda *a, **k: [],
            ):
                response = app_module.app.test_client().post(
                    "/api/interview/nudge",
                    json={"question": "Q?", "profile_slug": "petec"},
                    base_url="http://localhost",
                )
            self.assertEqual(response.status_code, 503)
            self.assertEqual(
                response.get_json()["error"],
                interview_ai.SERVICE_NOT_CONFIGURED_COPY,
            )
            initialize_mock.assert_not_called()
        finally:
            app_module.limiter.enabled = limiter_was_enabled

    def test_ready_request_path_never_invokes_initialize(self):
        import unittest.mock as mock
        import anthropic
        import httpx
        import app as app_module
        from services import database_service as database_service_module
        boot.initialize(RELEASE_ID)
        limiter_was_enabled = app_module.limiter.enabled
        app_module.limiter.enabled = False

        def exploding_create(**_kwargs):
            raise anthropic.APIConnectionError(
                request=httpx.Request("POST", "https://api.anthropic.com")
            )

        try:
            with mock.patch.object(
                boot, "initialize",
                side_effect=AssertionError(
                    "a request invoked boot.initialize"
                ),
            ) as initialize_mock, mock.patch.object(
                app_module.client.messages, "create", new=exploding_create,
            ), mock.patch.object(
                database_service_module.database_service,
                "execute_procedure", new=lambda *a, **k: [],
            ):
                response = app_module.app.test_client().post(
                    "/api/interview/nudge",
                    json={"question": "Q?", "profile_slug": "petec"},
                    base_url="http://localhost",
                )
            # The boot state was READY, so the request reached the (failed)
            # provider dispatch — proving it read the frozen state and
            # never re-initialized.
            self.assertEqual(response.status_code, 500)
            initialize_mock.assert_not_called()
        finally:
            app_module.limiter.enabled = limiter_was_enabled

    def test_runtime_request_code_never_names_the_lazy_resolver(self):
        """resolve_active_release is a verification/tooling seam; the
        request path (jobs) must not reference it at all."""
        jobs_source = (
            Path(__file__).resolve().parents[2]
            / "services" / "interview_ai" / "jobs.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("resolve_active_release", jobs_source)

    def test_fresh_process_freezes_state_at_import(self):
        """A brand-new interpreter that merely imports app holds a frozen
        boot state before any request exists."""
        import os
        import subprocess
        import sys
        env = dict(os.environ)
        env.setdefault("ANTHROPIC_API_KEY", "test-key-for-ci-only")
        completed = subprocess.run(
            [sys.executable, "-c",
             "import app\n"
             "from services.interview_ai import boot\n"
             "state = boot.state()\n"
             "assert state is not None, 'no frozen boot state after import'\n"
             "print(state.status)\n"],
            capture_output=True, text=True, timeout=300,
            cwd=str(Path(__file__).resolve().parents[2]), env=env,
        )
        self.assertEqual(
            completed.returncode, 0,
            "fresh-process import failed: %s" % completed.stderr[-500:],
        )
        self.assertIn(
            completed.stdout.strip(),
            {"ready", "service_not_configured"},
        )

    def test_app_import_ran_the_boundary_boot_initializer(self):
        # The application module freezes its own state at import; this
        # process imported app (directly or via a sibling suite), so a
        # frozen state must exist once app is in sys.modules.
        import sys
        if "app" not in sys.modules:
            import app  # noqa: F401  (freezes boot state at import)
        # The suite-level resets above cleared it; re-import proves the
        # initializer is import-time, not request-time: a fresh interpreter
        # would hold the state frozen before any request. Here we assert
        # the call SITE is inside the guarded route-boundary fragment.
        source = (
            Path(__file__).resolve().parents[2] / "app.py"
        ).read_text(encoding="utf-8")
        boundary_start = source.index(
            ">>> INTERVIEW-GUARDED-FRAGMENT: interview_route_boundary"
        )
        boundary_end = source.index(
            "<<< END-INTERVIEW-GUARDED-FRAGMENT: interview_route_boundary"
        )
        self.assertIn(
            "interview_ai.boot.initialize(",
            source[boundary_start:boundary_end],
        )


if __name__ == "__main__":
    unittest.main()
