"""Fake-only adversarial coverage for the sealed Workshop document guard."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import unittest
from urllib.parse import urlparse

from qa.synthetic_member import sealed_credential_broker as broker


class GuardPage:
    def __init__(self, *, redirect_to: str | None = None):
        self.url = broker.ALLOWED_SITE_ORIGIN + "/app/workshop"
        self.redirect_to = redirect_to
        self.targets: list[str] = []
        self.document_checks = 0

    @staticmethod
    def _canonical(value: str) -> bool:
        parsed = urlparse(value)
        return (
            parsed.scheme == "https"
            and parsed.netloc == "peerslate.com"
            and parsed.hostname == "peerslate.com"
            and parsed.port is None
            and parsed.username is None
            and parsed.password is None
        )

    def goto(self, target, *, wait_until):
        if wait_until != "domcontentloaded":
            raise AssertionError("unexpected navigation wait")
        self.targets.append(target)
        self.url = self.redirect_to or target

    def reload(self, *, wait_until):
        if wait_until != "domcontentloaded":
            raise AssertionError("unexpected reload wait")
        if self.redirect_to:
            self.url = self.redirect_to

    def evaluate(self, _expression, payload):
        self.document_checks += 1
        if (
            payload.get("expectedOrigin") != broker.ALLOWED_SITE_ORIGIN
            or not self._canonical(self.url)
        ):
            raise RuntimeError("hostile Workshop document")
        return True


class GuardHandle:
    def __init__(self, locator):
        self.locator = locator
        self.disposed = False

    def evaluate(self, _expression, payload):
        page = self.locator.page
        if self.locator.redirect_on_handle:
            page.url = "https://evil.example/app/workshop"
        if self.locator.hostile_owner or not page._canonical(page.url):
            raise RuntimeError("hostile Workshop owner document")
        self.locator.writes.append(dict(payload))
        return True

    def dispose(self):
        self.disposed = True


class GuardLocator:
    def __init__(
        self,
        page,
        *,
        count: int = 1,
        hostile_owner: bool = False,
        redirect_on_read: bool = False,
        redirect_on_handle: bool = False,
    ):
        self.page = page
        self.count = count
        self.hostile_owner = hostile_owner
        self.redirect_on_read = redirect_on_read
        self.redirect_on_handle = redirect_on_handle
        self.writes: list[dict[str, object]] = []
        self.reads: list[dict[str, object]] = []

    def evaluate_all(self, expression, payload):
        self.reads.append(dict(payload))
        if self.redirect_on_read:
            self.page.url = "https://evil.example/app/workshop"
        if self.hostile_owner or not self.page._canonical(self.page.url):
            raise RuntimeError("hostile Workshop owner document")
        if payload.get("operation") == "count":
            return self.count
        if payload.get("operation") == "text":
            if self.count != 1:
                raise RuntimeError("unexpected cardinality")
            return "private generated value"
        if payload.get("operation") == "input_value":
            if self.count != 1:
                raise RuntimeError("unexpected cardinality")
            return "sealed-version"
        if payload.get("operation") == "attribute":
            if self.count != 1:
                raise RuntimeError("unexpected cardinality")
            return "/app/workshop?item=opaque"
        if payload.get("term") == "Downstream use":
            raise AssertionError(
                "exact disclosure must execute the production evaluator"
            )
        raise AssertionError("unexpected guarded evaluator read")

    def element_handle(self):
        return GuardHandle(self) if self.count == 1 else None


_NODE_DESCRIPTION_EVALUATOR_RUNNER = r"""
const [source, fixtureJson, payloadJson] = process.argv.slice(1);
const fixture = JSON.parse(fixtureJson);
const payload = JSON.parse(payloadJson);
class HTMLElement {}
const window = {
  top: null,
  location: { href: fixture.url },
  HTMLElement,
};
window.top = window;
const document = { defaultView: window };
const foreignDocument = { defaultView: window };
global.window = window;
global.document = document;
function element(tagName, textContent, children = []) {
  const element = new HTMLElement();
  element.tagName = tagName;
  element.textContent = textContent || "";
  element.children = children;
  element.isConnected = true;
  element.ownerDocument = document;
  return element;
}
function row(shape) {
  const children = [];
  if (Object.hasOwn(shape, "term")) {
    children.push(element("DT", shape.term));
  }
  if (Object.hasOwn(shape, "description")) {
    children.push(element("DD", shape.description));
  }
  if (Object.hasOwn(shape, "nestedTerm")) {
    children.push(
      element("DIV", "", [
        element("DT", shape.nestedTerm),
        element("DD", shape.nestedDescription || ""),
      ])
    );
  }
  const result = element("DIV", "", children);
  if (shape.foreignOwner === true) {
    result.ownerDocument = foreignDocument;
  }
  return result;
}
const rows = fixture.rows.map(row);
if (fixture.redirectTo) {
  window.location.href = fixture.redirectTo;
}
const evaluator = eval("(" + source + ")");
if (evaluator(rows, payload) !== true) {
  throw new Error("production evaluator did not accept the exact disclosure");
}
"""


def _five_row_template(*, downstream: dict[str, object] | None = None) -> list[dict[str, object]]:
    return [
        {"term": "Status", "description": "Active"},
        {"term": "Audience", "description": "Private"},
        {"term": "Classification", "description": "Unclassified"},
        downstream
        or {"term": "Downstream use", "description": "Not used elsewhere"},
        {"term": "Source", "description": "Member"},
    ]


class ProductionDescriptionLocator:
    """Fake browser boundary that executes the supplied production evaluator."""

    def __init__(self, fixture: dict[str, object]):
        self.fixture = fixture
        self.calls: list[tuple[str, dict[str, object]]] = []

    def evaluate_all(self, expression, payload):
        if expression != broker.WORKSHOP_EXACT_DESCRIPTION_EVALUATOR:
            raise AssertionError("unexpected production evaluator")
        self.calls.append((expression, dict(payload)))
        node = shutil.which("node")
        if not node:
            raise AssertionError("node is required for production evaluator coverage")
        result = subprocess.run(
            [
                node,
                "-e",
                _NODE_DESCRIPTION_EVALUATOR_RUNNER,
                expression,
                json.dumps(self.fixture),
                json.dumps(payload),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            raise RuntimeError("production evaluator refused the fixture")
        return True


class WorkshopEvaluatorTests(unittest.TestCase):
    def test_navigation_rejects_ports_userinfo_and_redirect_races(self):
        page = GuardPage()
        evaluator = broker.WorkshopEvaluator(page)
        for hostile in (
            "https://peerslate.com:443/app/workshop",
            "https://member@peerslate.com/app/workshop",
            "https://peerslate.com@evil.example/app/workshop",
        ):
            with self.subTest(hostile=hostile), self.assertRaisesRegex(
                broker.BrokerIndeterminate, "sealed_browser_operation_indeterminate"
            ):
                evaluator.navigate(hostile)
        self.assertEqual(page.targets, [])

        redirected = GuardPage(redirect_to="https://evil.example/app/workshop")
        with self.assertRaisesRegex(
            broker.BrokerIndeterminate, "sealed_browser_operation_indeterminate"
        ):
            broker.WorkshopEvaluator(redirected).navigate(
                "https://peerslate.com/app/workshop"
            )
        self.assertEqual(redirected.targets, ["https://peerslate.com/app/workshop"])

    def test_private_reads_and_generated_writes_refuse_hostile_owner_documents(self):
        page = GuardPage()
        evaluator = broker.WorkshopEvaluator(page)
        self.assertEqual(evaluator.count(GuardLocator(page)), 1)
        self.assertEqual(evaluator.text(GuardLocator(page)), "private generated value")

        hostile_read = GuardLocator(page, hostile_owner=True)
        with self.assertRaisesRegex(
            broker.BrokerIndeterminate, "sealed_browser_operation_indeterminate"
        ):
            evaluator.count(hostile_read)

        redirected_page = GuardPage()
        redirected_read = GuardLocator(redirected_page, redirect_on_read=True)
        with self.assertRaisesRegex(
            broker.BrokerIndeterminate, "sealed_browser_operation_indeterminate"
        ):
            broker.WorkshopEvaluator(redirected_page).count(redirected_read)

        write_page = GuardPage()
        redirected_write = GuardLocator(write_page, redirect_on_handle=True)
        with self.assertRaisesRegex(
            broker.BrokerIndeterminate, "sealed_browser_operation_indeterminate"
        ):
            broker.WorkshopEvaluator(write_page).fill(
                redirected_write, "generated private wording"
            )
        self.assertEqual(redirected_write.writes, [])

    def test_downstream_disclosure_executes_the_production_guard_on_five_rows(self):
        template = (
            Path(__file__).resolve().parents[2]
            / "templates"
            / "partials"
            / "workshop"
            / "_item_detail.html"
        ).read_text(encoding="utf-8")
        self.assertEqual(template.count('class="wk-detail__meta-row"'), 5)

        exact_fixture = {
            "url": "https://peerslate.com/app/workshop?item=opaque",
            "rows": _five_row_template(),
        }
        locator = ProductionDescriptionLocator(exact_fixture)
        broker.WorkshopEvaluator(GuardPage()).exact_description(
            locator,
            term="Downstream use",
            description="Not used elsewhere",
        )
        self.assertEqual(len(locator.calls), 1)
        self.assertEqual(len(exact_fixture["rows"]), 5)
        self.assertEqual(
            locator.calls[0][1],
            {
                "expectedOrigin": broker.ALLOWED_SITE_ORIGIN,
                "term": "Downstream use",
                "description": "Not used elsewhere",
            },
        )

        failures = {
            "nested_only": {
                "url": "https://peerslate.com/app/workshop",
                "rows": _five_row_template(
                    downstream={
                        "nestedTerm": "Downstream use",
                        "nestedDescription": "Not used elsewhere",
                    }
                ),
            },
            "split_row": {
                "url": "https://peerslate.com/app/workshop",
                "rows": _five_row_template(
                    downstream={
                        "term": "Downstream use",
                        "description": "Unavailable",
                    }
                )[:-1]
                + [{"term": "Source", "description": "Not used elsewhere"}],
            },
            "duplicate_row": {
                "url": "https://peerslate.com/app/workshop",
                "rows": [
                    {"term": "Status", "description": "Active"},
                    {
                        "term": "Downstream use",
                        "description": "Not used elsewhere",
                    },
                    {"term": "Audience", "description": "Private"},
                    {
                        "term": "Downstream use",
                        "description": "Not used elsewhere",
                    },
                    {"term": "Source", "description": "Member"},
                ],
            },
            "hostile_owner": {
                "url": "https://peerslate.com/app/workshop",
                "rows": _five_row_template(
                    downstream={
                        "term": "Downstream use",
                        "description": "Not used elsewhere",
                        "foreignOwner": True,
                    }
                ),
            },
            "explicit_port": {
                "url": "https://peerslate.com:443/app/workshop",
                "rows": _five_row_template(),
            },
            "userinfo": {
                "url": "https://member@peerslate.com/app/workshop",
                "rows": _five_row_template(),
            },
            "redirect_race": {
                "url": "https://peerslate.com/app/workshop",
                "redirectTo": "https://evil.example/app/workshop",
                "rows": _five_row_template(),
            },
        }
        for name, fixture in failures.items():
            with self.subTest(name=name), self.assertRaisesRegex(
                broker.BrokerIndeterminate,
                "sealed_browser_operation_indeterminate",
            ):
                broker.WorkshopEvaluator(GuardPage()).exact_description(
                    ProductionDescriptionLocator(fixture),
                    term="Downstream use",
                    description="Not used elsewhere",
                )


if __name__ == "__main__":
    unittest.main()
