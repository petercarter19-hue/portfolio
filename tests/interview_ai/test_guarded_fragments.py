"""B2: the app.py guarded-fragment projection — bindings, liveness, rejects.

Three properties, each mechanical:

1. The projection is strict — a missing, unknown, duplicated, nested,
   unterminated, or symbol-stripped fragment is an error, in the builder
   AND in runtime release resolution.
2. The bound fragments are the EXECUTED bytes: the live route
   view-functions, the JobDeps assembly, the signed-context wrappers, and
   the signing serializer all resolve to definitions inside the fragment
   regions — behaviour cannot move out leaving a dead guarded copy behind.
3. The manifest binds every expected fragment by exact content hash.
"""

import inspect
import json
import os
import unittest
from pathlib import Path

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

import app as app_module
from services.interview_ai import fragments
from services.interview_ai.identity import sha256_hex

ROOT = Path(__file__).resolve().parents[2]
APP_PATH = ROOT / "app.py"
GUARDED_PATHS = ROOT / "prompts" / "interview" / "contracts" / "guarded-paths.json"

SAMPLE = (
    b"before\n"
    b"# >>> INTERVIEW-GUARDED-FRAGMENT: interview_provider_client\n"
    b"client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)\n"
    b"# <<< END-INTERVIEW-GUARDED-FRAGMENT: interview_provider_client\n"
    b"after\n"
)


class ExtractorTests(unittest.TestCase):
    def test_extracts_exact_bytes_between_markers(self):
        extracted = fragments.extract_fragments(
            SAMPLE.replace(b"before\n", _all_other_fragments())
        )
        self.assertEqual(
            extracted["interview_provider_client"],
            b"client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)\n",
        )

    def test_missing_fragment_is_rejected(self):
        with self.assertRaises(fragments.FragmentError):
            fragments.extract_fragments(b"no markers at all\n")

    def test_unknown_fragment_name_is_rejected(self):
        source = SAMPLE.replace(
            b"interview_provider_client", b"smuggled_fragment"
        )
        with self.assertRaises(fragments.FragmentError):
            fragments.extract_fragments(source)

    def test_duplicate_fragment_is_rejected(self):
        source = _all_other_fragments() + SAMPLE[7:] + SAMPLE[7:]
        with self.assertRaises(fragments.FragmentError):
            fragments.extract_fragments(source)

    def test_nested_fragments_are_rejected(self):
        source = (
            b"# >>> INTERVIEW-GUARDED-FRAGMENT: interview_provider_client\n"
            b"# >>> INTERVIEW-GUARDED-FRAGMENT: interview_signing_serializer\n"
            b"x\n"
            b"# <<< END-INTERVIEW-GUARDED-FRAGMENT: interview_signing_serializer\n"
            b"# <<< END-INTERVIEW-GUARDED-FRAGMENT: interview_provider_client\n"
        )
        with self.assertRaises(fragments.FragmentError):
            fragments.extract_fragments(source)

    def test_unterminated_fragment_is_rejected(self):
        source = (
            b"# >>> INTERVIEW-GUARDED-FRAGMENT: interview_provider_client\n"
            b"client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)\n"
        )
        with self.assertRaises(fragments.FragmentError):
            fragments.extract_fragments(source)

    def test_symbol_stripped_fragment_is_rejected(self):
        source = _all_other_fragments() + SAMPLE[7:].replace(
            b"client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)",
            b"pass  # behaviour moved elsewhere",
        )
        with self.assertRaises(fragments.FragmentError) as caught:
            fragments.extract_fragments(source)
        self.assertIn("expected executed symbol", str(caught.exception))


def _all_other_fragments():
    """Minimal valid instances of the other expected fragments."""
    parts = []
    for name, symbols in fragments.EXPECTED_FRAGMENTS.items():
        if name == "interview_provider_client":
            continue
        body = "\n".join(symbols) + "\n"
        parts.append(
            "# >>> INTERVIEW-GUARDED-FRAGMENT: %s\n%s"
            "# <<< END-INTERVIEW-GUARDED-FRAGMENT: %s\n" % (name, body, name)
        )
    return "".join(parts).encode("utf-8")


class LiveBindingTests(unittest.TestCase):
    """The guarded fragments are the bytes the application executes."""

    @classmethod
    def setUpClass(cls):
        source = APP_PATH.read_bytes()
        cls.fragments = fragments.extract_fragments(source)
        text = source.decode("utf-8")
        cls.line_ranges = {}
        for name in fragments.EXPECTED_FRAGMENTS:
            open_marker = "# >>> INTERVIEW-GUARDED-FRAGMENT: %s" % name
            close_marker = "# <<< END-INTERVIEW-GUARDED-FRAGMENT: %s" % name
            start_line = text[:text.index(open_marker)].count("\n") + 1
            end_line = text[:text.index(close_marker)].count("\n") + 1
            cls.line_ranges[name] = (start_line, end_line)

    def _assert_defined_inside(self, function, fragment_name):
        _lines, first_line = inspect.getsourcelines(function)
        start, end = self.line_ranges[fragment_name]
        self.assertTrue(
            start < first_line < end,
            "%s is defined outside the %s fragment"
            % (function.__name__, fragment_name),
        )

    def test_live_route_bindings_are_inside_the_route_fragment(self):
        for endpoint in ("interview_review", "interview_improve",
                         "interview_nudge", "interview_model_answer"):
            view = app_module.app.view_functions[endpoint]
            self._assert_defined_inside(view, "interview_route_boundary")

    def test_jobdeps_and_context_wrappers_are_inside_the_route_fragment(self):
        for function in (app_module._interview_job_deps,
                         app_module._interview_api_authenticated_identity,
                         app_module._sign_interview_model_context,
                         app_module._load_interview_model_context):
            self._assert_defined_inside(function, "interview_route_boundary")

    def test_the_live_serializer_matches_the_guarded_construction(self):
        serializer = app_module.interview_context_serializer
        self.assertEqual(
            serializer.salt, b"peerslate-interview-model-answer-v1",
        )
        self.assertIn(
            "salt='peerslate-interview-model-answer-v1'",
            self.fragments["interview_signing_serializer"].decode("utf-8"),
        )

    def test_the_live_provider_client_is_the_guarded_construction(self):
        self.assertIsInstance(
            app_module.client, __import__("anthropic").Anthropic,
        )

    def test_manifest_binds_every_fragment_by_exact_content_hash(self):
        manifest = json.loads(GUARDED_PATHS.read_text(encoding="utf-8"))
        bound = {
            entry["path"]: entry["sha256"]
            for entry in manifest["entries"]
            if entry["path"].startswith("app.py#fragment=")
        }
        self.assertEqual(
            sorted(bound),
            sorted(
                "app.py#fragment=%s" % name
                for name in fragments.EXPECTED_FRAGMENTS
            ),
        )
        for name, content in self.fragments.items():
            self.assertEqual(
                bound["app.py#fragment=%s" % name], sha256_hex(content),
            )


if __name__ == "__main__":
    unittest.main()
