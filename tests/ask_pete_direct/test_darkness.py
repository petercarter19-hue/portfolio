"""The feature is dark by construction. These are the tests that keep it so.

Two independent facts, each asserted here rather than assumed:

1. No production module imports or registers ``ask_pete_direct``. That is the
   outer gate, and it is not a configuration setting anyone can flip by
   accident - it is the absence of two lines in ``app.py``.
2. The flag defaults off and is documented as such, so even once the blueprint
   IS registered, the routes stay unreachable until a deliberate enablement.

If a later leg registers the blueprint, ``test_the_blueprint_is_not_registered
_by_any_production_module`` is expected to fail. That is the point: it is the
tripwire that forces the registration to be a reviewed, recorded act rather
than something that happens quietly.
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BLUEPRINT_MODULE = "ask_pete_direct_routes"
ENV_EXAMPLE = ROOT / ".env.example"

# Every Python module that is part of the running application, i.e. everything
# at the repository root plus services/, excluding tests and tooling.
def _production_modules():
    modules = sorted(path for path in ROOT.glob("*.py"))
    modules += sorted(path for path in (ROOT / "services").rglob("*.py"))
    return [path for path in modules if path.name != f"{BLUEPRINT_MODULE}.py"]


class DarknessTests(unittest.TestCase):
    def test_the_blueprint_is_not_registered_by_any_production_module(self):
        offenders = []
        for path in _production_modules():
            source = path.read_text(encoding="utf-8")
            if BLUEPRINT_MODULE in source or "register_blueprint(ask_pete_direct" in source:
                offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual(
            offenders,
            [],
            "ask_pete_direct_routes is referenced by production code. The "
            "feature is supposed to be unreachable until its recorded "
            "registration leg.",
        )

    def test_the_service_is_reached_only_through_the_unregistered_blueprint(self):
        """The storage seam is real, but nothing that runs today calls it."""
        offenders = []
        for path in _production_modules():
            if path.name == "ask_pete_direct_service.py":
                continue
            if "ask_pete_direct_service" in path.read_text(encoding="utf-8"):
                offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual(offenders, [])

    def test_app_py_is_untouched_by_this_package(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        for token in (
            "ask_pete_direct",
            "recruiter_question",
            "PEERSLATE_ASK_PETE_DIRECT_ENABLED",
        ):
            with self.subTest(token=token):
                self.assertNotIn(token, source)

    def test_the_blueprint_imports_nothing_from_app(self):
        """A reusable blueprint must never import the module that registers it."""
        tree = ast.parse((ROOT / f"{BLUEPRINT_MODULE}.py").read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertNotIn("app", imported)

    def test_the_module_docstring_states_the_registration_is_a_later_leg(self):
        import ask_pete_direct_routes

        docstring = ask_pete_direct_routes.__doc__
        self.assertIn("NOT REGISTERED", docstring)
        self.assertIn("PEERSLATE_ASK_PETE_DIRECT_ENABLED", docstring)


class FlagDocumentationTests(unittest.TestCase):
    def test_the_flag_is_documented_off_in_env_example(self):
        text = ENV_EXAMPLE.read_text(encoding="utf-8")
        self.assertIn("PEERSLATE_ASK_PETE_DIRECT_ENABLED=false", text)

    def test_the_env_entry_says_the_blueprint_is_unregistered(self):
        text = ENV_EXAMPLE.read_text(encoding="utf-8")
        block = _env_block(text, "PEERSLATE_ASK_PETE_DIRECT_ENABLED")
        self.assertIn("unregistered", block.lower())

    def test_the_env_entry_names_the_owner_key_prerequisite(self):
        """Turning the flag on without a single owner user key would leave the
        form visible and every send answering 503. Say so where it is set."""
        block = _env_block(
            ENV_EXAMPLE.read_text(encoding="utf-8"), "PEERSLATE_ASK_PETE_DIRECT_ENABLED"
        )
        self.assertIn("PEERSLATE_OWNER_USER_KEYS", block)


def _env_block(text, key):
    """The comment block immediately above an .env.example assignment."""
    lines = text.splitlines()
    index = next(i for i, line in enumerate(lines) if line.startswith(f"{key}="))
    start = index
    while start > 0 and (lines[start - 1].startswith("#") or not lines[start - 1].strip()):
        if not lines[start - 1].strip():
            break
        start -= 1
    return "\n".join(lines[start : index + 1])


if __name__ == "__main__":
    unittest.main()
