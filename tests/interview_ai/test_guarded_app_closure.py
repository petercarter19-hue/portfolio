"""Correction B2 (consolidated review): the guarded app.py closure.

Four properties are enforced mechanically:

1. Transitive free-name closure: every identifier each guarded fragment
   reads resolves to guarded source, a hash-locked distribution, an
   allowlisted stdlib module, a builtin, or the one documented boundary
   global — analyzed by services.interview_ai.app_closure.
2. The locked-distribution allowlist is honest: every distribution it
   names is present in the recorded external runtime lock.
3. Liveness: the LIVE registered Interview routes, the before_request
   gate, the response hooks, and the error handlers the Interview
   contract can reach all execute from inside guarded fragment regions.
4. Any after_request hook that is NOT guarded must be a no-op for an
   Interview API JSON response — status, headers, and body unchanged.
"""

import inspect
import json
import os
import unittest
from pathlib import Path

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-for-ci-only")

ROOT = Path(__file__).resolve().parents[2]

from services.interview_ai import app_closure
from services.interview_ai.fragments import EXPECTED_FRAGMENTS, extract_fragments

import app as app_module


APP_SOURCE = (ROOT / "app.py").read_bytes()
FRAGMENT_RANGES = app_closure.fragment_line_ranges(APP_SOURCE)


def _is_fragment_guarded(function):
    """True when the function's complete source lies inside one fragment."""
    import functools
    unwrapped = inspect.unwrap(function)
    while isinstance(unwrapped, functools.partial):
        unwrapped = inspect.unwrap(unwrapped.func)
    lines, start = inspect.getsourcelines(unwrapped)
    end = start + len(lines) - 1
    return any(
        start >= fragment_start and end <= fragment_end
        for fragment_start, fragment_end in FRAGMENT_RANGES.values()
    )


class TransitiveClosureTests(unittest.TestCase):
    def test_closure_has_no_violations(self):
        self.assertEqual(app_closure.analyze_app_closure(APP_SOURCE), [])

    def test_every_expected_fragment_is_present_and_extracted(self):
        fragments = extract_fragments(APP_SOURCE)
        self.assertEqual(sorted(fragments), sorted(EXPECTED_FRAGMENTS))
        self.assertEqual(sorted(FRAGMENT_RANGES), sorted(EXPECTED_FRAGMENTS))

    def test_locked_distribution_allowlist_matches_runtime_lock(self):
        manifest = json.loads(
            (ROOT / "prompts" / "interview" / "contracts"
             / "external-runtime-1.json").read_text(encoding="utf-8")
        )
        locked_names = {
            distribution["name"].lower().replace("_", "-")
            for distribution in manifest["distributions"]
        }
        for import_root, distribution in sorted(
            app_closure.LOCKED_DISTRIBUTION_IMPORT_ROOTS.items()
        ):
            self.assertIn(
                distribution.lower().replace("_", "-"),
                locked_names,
                "app_closure allows import %r via distribution %r, which "
                "is not in the recorded runtime lock" % (import_root, distribution),
            )

    def test_removing_a_fragment_is_reported_as_a_violation(self):
        text = APP_SOURCE.decode("utf-8")
        mutated = text.replace(
            "# >>> INTERVIEW-GUARDED-FRAGMENT: interview_entitlements_and_evidence\n",
            "",
        ).replace(
            "# <<< END-INTERVIEW-GUARDED-FRAGMENT: interview_entitlements_and_evidence\n",
            "",
        )
        violations = app_closure.analyze_app_closure(mutated.encode("utf-8"))
        self.assertTrue(
            any("get_interview_entitlements" in violation for violation in violations),
            violations,
        )


class LiveRegistrationTests(unittest.TestCase):
    """The running Flask app must execute the guarded bytes, not copies."""

    INTERVIEW_ENDPOINTS = (
        "interview_review",
        "interview_improve",
        "interview_nudge",
        "interview_model_answer",
        # The retired legacy endpoint's 410 contract is guarded too
        # (consolidated B2 follow-up).
        "interview_coach",
    )

    def test_live_interview_routes_execute_from_guarded_fragments(self):
        for endpoint in self.INTERVIEW_ENDPOINTS:
            view = app_module.app.view_functions[endpoint]
            self.assertTrue(
                _is_fragment_guarded(view),
                "live view %r is not inside a guarded fragment" % endpoint,
            )

    def test_live_before_request_gate_is_guarded(self):
        hooks = app_module.app.before_request_funcs.get(None, [])
        gate = [hook for hook in hooks
                if hook.__name__ == "keep_portfolio_on_canonical_path"]
        self.assertEqual(len(gate), 1)
        self.assertTrue(_is_fragment_guarded(gate[0]))

    def test_live_error_handlers_are_guarded(self):
        handled = []
        for handlers in app_module.app.error_handler_spec.get(None, {}).values():
            for handler in handlers.values():
                handled.append(handler)
        self.assertGreaterEqual(len(handled), 5)
        for handler in handled:
            self.assertTrue(
                _is_fragment_guarded(handler),
                "app-level error handler %r is not inside a guarded fragment"
                % handler.__name__,
            )

    def test_live_rate_limiter_and_key_are_guarded(self):
        self.assertTrue(_is_fragment_guarded(app_module._client_rate_limit_key))
        # The LIVE limiter instance must key requests through the guarded
        # function object, not a stale or replaced copy.
        key_func = getattr(app_module.limiter, "_key_func", None) or getattr(
            app_module.limiter, "key_func", None
        )
        self.assertIs(key_func, app_module._client_rate_limit_key)

    def test_unguarded_after_request_hooks_are_noops_for_interview_json(self):
        flask_app = app_module.app
        hooks = flask_app.after_request_funcs.get(None, [])
        self.assertGreaterEqual(len(hooks), 3)
        unguarded = [hook for hook in hooks if not _is_fragment_guarded(hook)]
        with flask_app.test_request_context(
            "/api/interview/review",
            method="POST",
            json={"question": "q"},
        ):
            for hook in unguarded:
                response = flask_app.response_class(
                    response=json.dumps({"probe": True}),
                    status=200,
                    mimetype="application/json",
                )
                before = (
                    response.status_code,
                    dict(response.headers),
                    response.get_data(),
                )
                returned = hook(response)
                after = (
                    returned.status_code,
                    dict(returned.headers),
                    returned.get_data(),
                )
                hook_name = getattr(
                    hook, "__name__",
                    getattr(getattr(hook, "func", None), "__name__", repr(hook)),
                )
                self.assertEqual(
                    before,
                    after,
                    "unguarded after_request hook %r altered an Interview "
                    "API JSON response; guard it as a fragment" % hook_name,
                )


if __name__ == "__main__":
    unittest.main()
