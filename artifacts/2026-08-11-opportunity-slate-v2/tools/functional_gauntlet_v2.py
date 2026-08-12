"""Real-browser functional gauntlet for Opportunity Slate v2 R1.

Runs the unregistered blueprint in a throwaway local Flask server with a
stateful database fake at the production service seam.  No network service,
production data, schema, or app.py registration is involved.

Usage: functional_gauntlet_v2.py <evidence.json>
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Thread

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

import opportunity_slate_v2_routes as routes
from services.database_service import DatabaseServiceError
from services.opportunity_slate_v2_service import OpportunitySlateV2Service
from tests.test_opportunity_slate_v2 import make_app


SESSION_KEY = "11111111-1111-1111-1111-111111111111"
SOURCE_KEY = "22222222-2222-2222-2222-222222222222"
SOURCE_ONE = "Employer role wording exactly as captured."
SOURCE_ONE_CORRECTED = "Employer role wording, corrected by the member."
SOURCE_TWO = "Replacement employer wording from a second posting."


def _token(value: int) -> bytes:
    return value.to_bytes(8, "big")


class StatefulDatabase:
    """Small stored-procedure contract fake for browser sequencing."""

    def __init__(self):
        self.calls = []
        self.idempotency = {}
        self.working = None
        self.identity = None
        self.source_version = 0
        self.source_token = 1
        self.session_token = 1
        self.save_count = 0
        self.fail_next = None

    def first_row(self, procedure_name, parameters=None):
        params = dict(parameters or [])
        self.calls.append((procedure_name, params))
        if self.fail_next == procedure_name:
            self.fail_next = None
            raise DatabaseServiceError(f"injected failure: {procedure_name}")

        if procedure_name == "usp_PurgeExpiredOpportunityWorkingData":
            return {"purged_session_count": 0, "purged_version_count": 0}
        if procedure_name == "usp_GetOpportunityWorkingSessionForOwner":
            return self._working_row()
        if procedure_name == "usp_GetOpportunitySourceIdentityForOwner":
            return dict(self.identity) if self.identity else None
        if procedure_name == "usp_SaveOpportunitySourceForOwner":
            return self._save(params)
        if procedure_name == "usp_SaveOpportunitySourceIdentityForOwner":
            if not self._source_token_matches(params.get("@ExpectedRowVersion")):
                return {"outcome": "changed", "source_row_version": None}
            self.identity = {
                "employer_name": params.get("@EmployerName"),
                "role_title": params.get("@RoleTitle"),
                "source_type": "job_posting",
            }
            self.source_token += 1
            return {"outcome": "success", "source_row_version": _token(self.source_token)}
        if procedure_name == "usp_CorrectOpportunitySourceForOwner":
            if not self._source_token_matches(params.get("@ExpectedRowVersion")):
                return {
                    "outcome": "changed",
                    "source_row_version": None,
                    "version_number": None,
                }
            self.working["member_corrected_text"] = params["@CorrectedText"]
            self.working["corrected_at_utc"] = datetime.now(timezone.utc).isoformat()
            self.working["confirmed_version_number"] = None
            self.working["confirmed_at_utc"] = None
            self.source_token += 1
            return {
                "outcome": "success",
                "source_row_version": _token(self.source_token),
                "version_number": self.source_version,
            }
        if procedure_name == "usp_ConfirmOpportunitySourceForOwner":
            if not self._source_token_matches(params.get("@ExpectedRowVersion")):
                return {
                    "outcome": "changed",
                    "source_row_version": None,
                    "confirmed_version_number": None,
                }
            self.working["confirmed_version_number"] = self.source_version
            self.working["confirmed_at_utc"] = datetime.now(timezone.utc).isoformat()
            return {
                "outcome": "success",
                "source_row_version": _token(self.source_token),
                "confirmed_version_number": self.source_version,
            }
        if procedure_name == "usp_DeleteOpportunityWorkingSessionForOwner":
            if not self.working or params.get("@ExpectedRowVersion") != _token(self.session_token):
                return {"outcome": "changed", "deleted_version_count": None}
            deleted = self.source_version
            self.working = None
            self.identity = None
            return {"outcome": "success", "deleted_version_count": deleted}
        raise AssertionError(f"unexpected procedure: {procedure_name}")

    def _source_token_matches(self, expected) -> bool:
        return self.working is not None and expected == _token(self.source_token)

    def _save(self, params):
        key = params["@IdempotencyKey"]
        if key in self.idempotency:
            return self._save_row("existing")
        if self.working and params["@SourceText"] == self.working["original_text"]:
            self.idempotency[key] = self.source_version
            return self._save_row("unchanged")

        self.source_version += 1
        self.source_token += 1
        self.session_token += 1
        self.save_count += 1
        self.identity = None
        self.working = {
            "original_text": params["@SourceText"],
            "member_corrected_text": None,
            "corrected_at_utc": None,
            "confirmed_version_number": None,
            "confirmed_at_utc": None,
            "capture_method": params["@CaptureMethod"],
        }
        self.idempotency[key] = self.source_version
        return self._save_row("success")

    def _save_row(self, outcome):
        return {
            "outcome": outcome,
            "working_session_key": SESSION_KEY,
            "source_key": SOURCE_KEY,
            "version_number": self.source_version,
            "workbench_state": "review_source",
            "session_row_version": _token(self.session_token),
            "source_row_version": _token(self.source_token),
        }

    def _working_row(self):
        if not self.working:
            return None
        return {
            "working_session_key": SESSION_KEY,
            "workbench_state": "review_source",
            "expires_at_utc": "2999-01-01T00:00:00+00:00",
            "session_row_version": _token(self.session_token),
            "source_key": SOURCE_KEY,
            "current_version_number": self.source_version,
            "confirmed_version_number": self.working["confirmed_version_number"],
            "confirmed_at_utc": self.working["confirmed_at_utc"],
            "source_row_version": _token(self.source_token),
            "capture_method": self.working["capture_method"],
            "original_text": self.working["original_text"],
            "member_corrected_text": self.working["member_corrected_text"],
            "corrected_at_utc": self.working["corrected_at_utc"],
            "captured_at_utc": "2025-04-30T12:00:00+00:00",
        }

    def clear_working_state(self):
        """Reset only the disposable member state between independent
        browser scenarios; cumulative call/save evidence stays intact."""
        self.idempotency = {}
        self.working = None
        self.identity = None
        self.source_version = 0
        self.source_token = 1
        self.session_token = 1
        self.fail_next = None


class LocalServer:
    def __init__(self, app):
        self.server = make_server("127.0.0.1", 0, app)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)

    @property
    def base_url(self):
        return f"http://127.0.0.1:{self.server.server_port}"

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_exc):
        self.server.shutdown()
        self.thread.join(timeout=5)


def main(output_path: Path):
    checks = []
    console_errors = []
    page_errors = []
    bad_responses = []
    deliberate_http_failures = []

    def check(name, condition, detail=None):
        checks.append({"name": name, "passed": bool(condition), "detail": detail})
        if not condition:
            raise AssertionError(f"{name}: {detail}")

    app, _unused_database, patcher = make_app()
    app.config["TESTING"] = False
    app.add_url_rule(
        "/auth/session",
        endpoint="gauntlet_auth_session",
        view_func=lambda: {"authenticated": True},
    )
    database = StatefulDatabase()
    routes.opportunity_slate_v2_service = OpportunitySlateV2Service(database=database)

    with LocalServer(app) as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 1372, "height": 1146})
        context.add_init_script(
            """
            window.__os2CLS = 0;
            new PerformanceObserver((list) => {
              for (const entry of list.getEntries()) {
                if (!entry.hadRecentInput) window.__os2CLS += entry.value;
              }
            }).observe({type: 'layout-shift', buffered: true});
            """
        )
        page = context.new_page()
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on(
            "response",
            lambda response: bad_responses.append({"url": response.url, "status": response.status})
            if response.status >= 400
            else None,
        )
        room_url = server.base_url + "/opportunity-slate"

        response = page.goto(room_url, wait_until="networkidle")
        check("stage 1 opens", response.status == 200 and page.locator("h1").inner_text() == "Bring in a role.")
        check("stage 1 initial CLS", page.evaluate("window.__os2CLS") < 0.01, page.evaluate("window.__os2CLS"))
        check("empty review action disabled", page.locator("[data-os2-review-source]").get_attribute("aria-disabled") == "true")
        page.locator("#os2-source-text").fill(SOURCE_ONE)
        check("typing enables review", page.locator("[data-os2-review-source]").get_attribute("aria-disabled") == "false")
        page.locator("#os2-source-text").focus()
        page.keyboard.press("Tab")
        check("keyboard reaches Dictate", page.evaluate("document.activeElement.matches('[data-os2-dictate-button]')"))
        check(
            "visible keyboard focus",
            page.locator("[data-os2-dictate-button]").evaluate("el => getComputedStyle(el).outlineWidth === '2px'"),
        )

        original_upload = routes.extract_uploaded_document
        original_import = routes.extract_imported_link

        def slow_failed_upload(_document):
            time.sleep(0.75)
            raise routes.OpportunitySourceIntakeError("cancelled test upload")

        def slow_failed_import(_url):
            time.sleep(0.75)
            raise routes.OpportunitySourceIntakeError("cancelled test import")

        routes.extract_uploaded_document = slow_failed_upload
        page.locator("[data-os2-upload-panel]").locator("xpath=ancestor::details/summary").click()
        page.locator("#os2-upload-document").set_input_files(
            {"name": "role.txt", "mimeType": "text/plain", "buffer": b"cancel me"}
        )
        page.locator('[data-os2-transfer-kind="upload"]').click()
        upload_cancel = page.locator("[data-os2-upload-panel] [data-os2-transfer-cancel]")
        check(
            "upload cancel is visible in flight",
            upload_cancel.is_visible(),
            {
                "message": page.locator("[data-os2-upload-panel] [data-os2-transfer-message]").inner_text(),
                "page_errors": page_errors,
                "console_errors": console_errors,
            },
        )
        check("in-flight upload disables paste capture", page.locator("[data-os2-review-source]").is_disabled())
        check("in-flight upload disables competing import", page.locator('[data-os2-transfer-kind="import"]').is_disabled())
        submit_was_blocked = page.locator("#os2-source-form").evaluate(
            """form => {
              const review = document.querySelector('[data-os2-review-source]');
              const event = new SubmitEvent('submit', {bubbles: true, cancelable: true, submitter: review});
              return !form.dispatchEvent(event);
            }"""
        )
        check("in-flight transfer blocks a competing form submit", submit_was_blocked)
        upload_cancel.click()
        check(
            "upload cancellation is explicit",
            "cancelled" in page.locator("[data-os2-upload-panel] [data-os2-transfer-message]").inner_text().lower(),
        )
        check("upload cancel preserves typed draft", page.locator("#os2-source-text").input_value() == SOURCE_ONE)
        check("upload cancel releases capture actions", not page.locator("[data-os2-review-source]").is_disabled())
        page.wait_for_timeout(900)

        seen_uploads = []

        def successful_upload(document):
            seen_uploads.append(document.filename if document else None)
            return "Enhanced upload role wording.", False

        routes.extract_uploaded_document = successful_upload
        database.fail_next = "usp_SaveOpportunitySourceForOwner"
        page.locator("#os2-upload-document").set_input_files(
            {"name": "unknown-role.txt", "mimeType": "text/plain", "buffer": b"unknown upload"}
        )
        page.locator('[data-os2-transfer-kind="upload"]').click()
        page.locator("[data-os2-upload-panel] .os2-card--error").wait_for()
        deliberate_http_failures.append({"path": "/opportunity-slate/source/upload", "status": 503})
        bad_responses[:] = [
            item for item in bad_responses
            if not (item["url"].endswith("/opportunity-slate/source/upload") and item["status"] == 503)
        ]
        check("unknown enhanced upload keeps the typed draft", page.locator("#os2-source-text").input_value() == SOURCE_ONE)
        check("unknown enhanced upload requires reload before retry", page.locator("[data-os2-review-source]").is_disabled())
        console_errors[:] = [
            item for item in console_errors
            if "status of 503" not in item
        ]

        page.goto(room_url, wait_until="networkidle")
        page.locator("#os2-source-text").fill(SOURCE_ONE)
        page.locator("[data-os2-upload-panel]").locator("xpath=ancestor::details/summary").click()
        seen_uploads.clear()
        page.locator("#os2-upload-document").set_input_files(
            {"name": "role.txt", "mimeType": "text/plain", "buffer": b"enhanced upload"}
        )
        page.locator('[data-os2-transfer-kind="upload"]').click()
        page.locator("h1", has_text="Review captured source").wait_for()
        check("enhanced upload sends the selected document", seen_uploads == ["role.txt"], seen_uploads)
        check("enhanced upload reaches captured-source review", page.locator("#os2-corrected-text").input_value() == "Enhanced upload role wording.")
        check("enhanced upload records the right capture method", database.working["capture_method"] == "uploaded")
        database.clear_working_state()
        routes.extract_uploaded_document = original_upload
        page.goto(room_url, wait_until="networkidle")

        routes.extract_imported_link = slow_failed_import
        page.locator("#os2-source-text").fill(SOURCE_ONE)
        page.locator("[data-os2-import-panel]").locator("xpath=ancestor::details/summary").click()
        page.locator("#os2-import-url").fill("https://example.com/role")
        page.locator('[data-os2-transfer-kind="import"]').click()
        page.locator("[data-os2-import-panel] [data-os2-transfer-cancel]").click()
        check(
            "import cancellation is explicit",
            "cancelled" in page.locator("[data-os2-import-panel] [data-os2-transfer-message]").inner_text().lower(),
        )
        check("import cancel preserves typed draft", page.locator("#os2-source-text").input_value() == SOURCE_ONE)
        check("import cancel preserves URL draft", page.locator("#os2-import-url").input_value() == "https://example.com/role")
        page.wait_for_timeout(900)

        seen_imports = []

        def successful_import(url):
            seen_imports.append(url)
            return "Enhanced import role wording.", False, url

        routes.extract_imported_link = successful_import
        page.locator("[data-os2-upload-panel]").locator("xpath=ancestor::details/summary").click()
        page.locator("#os2-upload-document").set_input_files(
            {"name": "large-role.pdf", "mimeType": "application/pdf", "buffer": b"x" * (3 * 1024 * 1024)}
        )
        page.locator("#os2-import-url").fill("https://example.com/enhanced-role")
        page.locator('[data-os2-transfer-kind="import"]').click()
        page.locator("h1", has_text="Review captured source").wait_for()
        check("enhanced import sends the public URL", seen_imports == ["https://example.com/enhanced-role"], seen_imports)
        check("enhanced import omits a selected large document", page.locator("#os2-corrected-text").input_value() == "Enhanced import role wording.")
        check("enhanced import records the right capture method", database.working["capture_method"] == "imported")
        database.clear_working_state()

        no_script_context = browser.new_context(java_script_enabled=False, viewport={"width": 1372, "height": 1146})
        no_script_page = no_script_context.new_page()
        no_script_page.goto(room_url, wait_until="networkidle")
        no_script_page.locator("[data-os2-upload-panel]").locator("xpath=ancestor::details/summary").click()
        no_script_page.locator("#os2-upload-document").set_input_files(
            {"name": "large-unused.pdf", "mimeType": "application/pdf", "buffer": b"x" * (3 * 1024 * 1024)}
        )
        no_script_page.locator("[data-os2-import-panel]").locator("xpath=ancestor::details/summary").click()
        no_script_page.locator("#os2-import-url").fill("https://example.com/no-script-role")
        no_script_page.locator('[data-os2-transfer-kind="import"]').click()
        no_script_page.wait_for_load_state("networkidle")
        check("plain-HTML import omits a selected large document", no_script_page.locator("#os2-corrected-text").input_value() == "Enhanced import role wording.")
        check("plain-HTML import sends its URL", seen_imports[-1] == "https://example.com/no-script-role", seen_imports)
        no_script_context.close()
        database.clear_working_state()
        routes.extract_imported_link = original_import
        page.goto(room_url, wait_until="networkidle")

        mobile_first_fold = browser.new_context(viewport={"width": 390, "height": 844}).new_page()
        mobile_first_fold.goto(room_url, wait_until="networkidle")
        primary_box = mobile_first_fold.locator("[data-os2-review-source]").bounding_box()
        alt_box = mobile_first_fold.locator(".os2-intake__alt").bounding_box()
        check("390x844 first fold includes primary action", primary_box["y"] + primary_box["height"] <= 844, primary_box)
        check("mobile alternatives follow primary action", alt_box["y"] >= primary_box["y"] + primary_box["height"], {"primary": primary_box, "alternatives": alt_box})
        mobile_first_fold.locator("#os2-source-text").fill(SOURCE_ONE)
        mobile_first_fold.locator("[data-os2-dictate-button]").focus()
        mobile_first_fold.keyboard.press("Tab")
        check("mobile focus reaches primary before alternatives", mobile_first_fold.evaluate("document.activeElement.matches('[data-os2-review-source]')"))
        mobile_first_fold.keyboard.press("Tab")
        check("mobile focus reaches upload after primary", mobile_first_fold.evaluate("document.activeElement.matches('.os2-alt-entry')"))
        mobile_first_fold.close()

        unsupported_context = browser.new_context(viewport={"width": 390, "height": 844})
        unsupported_context.add_init_script(
            "Object.defineProperty(window, 'SpeechRecognition', {value: undefined});"
            "Object.defineProperty(window, 'webkitSpeechRecognition', {value: undefined});"
        )
        unsupported_page = unsupported_context.new_page()
        unsupported_page.goto(room_url, wait_until="networkidle")
        check("unsupported dictation disables its control", unsupported_page.locator("[data-os2-dictate-button]").is_disabled())
        check("unsupported dictation has visible text alternative", "unavailable" in unsupported_page.locator("[data-os2-dictate-status]").inner_text().lower())
        unsupported_context.close()

        database.fail_next = "usp_SaveOpportunitySourceForOwner"
        paste_failure = page.request.post(
            server.base_url + "/opportunity-slate/source",
            form={"source_text": SOURCE_ONE, "idempotency_key": "browser-paste-failure"},
            headers={"Origin": server.base_url, "Sec-Fetch-Site": "same-origin"},
            fail_on_status_code=False,
        )
        deliberate_http_failures.append({"path": "/opportunity-slate/source", "status": paste_failure.status})
        check("failed paste returns 503", paste_failure.status == 503, paste_failure.status)
        page.set_content(paste_failure.text(), wait_until="networkidle")
        check("failed paste preserves typed draft", page.locator("#os2-source-text").input_value() == SOURCE_ONE)
        check("failed paste reports unknown outcome", "could not verify whether the last change reached storage" in page.locator(".os2-card--error").inner_text())
        check("unknown paste outcome requires reload before retry", page.locator("[data-os2-review-source]").is_disabled())

        page.goto(room_url, wait_until="networkidle")
        page.locator("#os2-source-text").fill(SOURCE_ONE)
        page.locator("[data-os2-upload-panel]").locator("xpath=ancestor::details/summary").click()
        page.locator("#os2-upload-document").set_input_files(
            {"name": "large-unused.pdf", "mimeType": "application/pdf", "buffer": b"x" * (3 * 1024 * 1024)}
        )
        page.locator("[data-os2-review-source]").click()
        page.wait_for_load_state("networkidle")
        check("paste ignores a selected large document and reaches review", page.locator("h1").inner_text() == "Review captured source")
        check("captured wording preserved", page.locator("#os2-corrected-text").input_value() == SOURCE_ONE)

        page.locator("#os2-employer-name").fill("Meridian Aerospace")
        page.locator("#os2-role-title").fill("Senior Systems Engineering Manager")
        page.locator("#os2-corrected-text").fill("Unsaved wording survives identity save")
        check("identity save reveals only after edit", page.locator('[data-os2-save-kind="identity"]').is_visible())
        check("dirty review disables confirmation", page.locator("[data-os2-confirm-source]").get_attribute("aria-disabled") == "true")
        page.locator('[data-os2-save-kind="identity"]').click()
        page.wait_for_load_state("networkidle")
        check("identity survives save", page.locator(".os2-rail__employer").inner_text() == "Meridian Aerospace")
        check("identity save preserves unsaved wording", page.locator("#os2-corrected-text").input_value() == "Unsaved wording survives identity save")
        check("confirmation stays disabled for preserved draft", page.locator("[data-os2-confirm-source]").get_attribute("aria-disabled") == "true")

        database.fail_next = "usp_CorrectOpportunitySourceForOwner"
        page.locator("#os2-corrected-text").fill("This correction must fail.")
        correction_form = page.locator("[data-os2-review-form]")
        correction_data = correction_form.evaluate("form => Object.fromEntries(new FormData(form))")
        correction_response = page.request.post(
            server.base_url + "/opportunity-slate/source/corrections",
            form=correction_data,
            headers={"Origin": server.base_url, "Sec-Fetch-Site": "same-origin"},
            fail_on_status_code=False,
        )
        deliberate_http_failures.append({"path": "/opportunity-slate/source/corrections", "status": correction_response.status})
        check("failed correction returns 503", correction_response.status == 503, correction_response.status)
        page.set_content(correction_response.text(), wait_until="networkidle")
        check("failed correction reports unknown outcome", "could not verify whether the last change reached storage" in page.locator(".os2-card--error").inner_text())
        check("failed correction preserves attempted wording", page.locator("#os2-corrected-text").input_value() == "This correction must fail.")

        page.goto(room_url, wait_until="networkidle")
        page.locator("#os2-corrected-text").fill(SOURCE_ONE_CORRECTED)
        page.locator('[data-os2-save-kind="wording"]').click()
        page.wait_for_load_state("networkidle")
        check("correction survives save", page.locator("#os2-corrected-text").input_value() == SOURCE_ONE_CORRECTED)
        page.locator("[data-os2-confirm-source]").click()
        page.wait_for_load_state("networkidle")
        check("confirmation becomes visible truth", "Confirmed role source" in page.locator(".os2-rail__meta").inner_text())

        narrow = browser.new_context(viewport={"width": 320, "height": 800}, reduced_motion="reduce").new_page()
        narrow.goto(room_url, wait_until="networkidle")
        check("320px reflow has no horizontal overflow", narrow.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"))
        check("narrow rail follows dominant document", narrow.locator(".os2-rail").bounding_box()["y"] > narrow.locator(".os2-main").bounding_box()["y"])
        narrow.close()

        zoom_context = browser.new_context(viewport={"width": 686, "height": 800}, device_scale_factor=2, reduced_motion="reduce")
        zoom_page = zoom_context.new_page()
        zoom_page.goto(room_url, wait_until="networkidle")
        check("200 percent equivalent reflows without horizontal overflow", zoom_page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"))
        zoom_context.close()

        page.locator(".os2-review__footer-back").click()
        page.wait_for_load_state("networkidle")
        replace_fields = page.locator("input[name='replace']")
        check(
            "Back opens bounded replacement intake",
            replace_fields.count() == 1
            and replace_fields.first.get_attribute("value") == "1",
            replace_fields.count(),
        )
        page.go_back(wait_until="networkidle")
        check("browser Back restores review", page.locator("h1").inner_text() == "Review captured source")
        page.go_forward(wait_until="networkidle")
        check("browser Forward restores replace intake", page.locator("h1").inner_text() == "Bring in a role.")

        page.locator("#os2-source-text").fill(SOURCE_TWO)
        fetch_statuses = page.locator("#os2-source-form").evaluate(
            """async form => {
              const data = new FormData(form);
              const submitter = document.querySelector('[data-os2-review-source]');
              data.set(submitter.name, submitter.value);
              const body = new URLSearchParams(data);
              const options = {method: 'POST', body};
              const responses = await Promise.all([fetch(form.action, options), fetch(form.action, options)]);
              return responses.map(response => response.status);
            }"""
        )
        page.goto(room_url, wait_until="networkidle")
        check("double submit requests both complete", fetch_statuses == [200, 200], fetch_statuses)
        check("double submit creates one replacement", database.source_version == 2, {"source_version": database.source_version, "save_count": database.save_count})
        check("replacement wording is current", page.locator("#os2-corrected-text").input_value() == SOURCE_TWO)
        check("replacement increments once", "Version 2" in page.locator(".os2-rail__meta").inner_text())

        page.locator(".os2-disclosure--danger details").evaluate("el => el.open = true")
        check("delete warning names irreversibility", "cannot be undone" in page.locator(".os2-disclosure__warning").inner_text().lower())
        database.fail_next = "usp_DeleteOpportunityWorkingSessionForOwner"
        delete_form = page.locator("[data-os2-delete-form]")
        delete_data = delete_form.evaluate("form => Object.fromEntries(new FormData(form))")
        delete_url = page.locator(".os2-disclosure--danger button").get_attribute("formaction")
        delete_response = page.request.post(
            server.base_url + delete_url,
            form=delete_data,
            headers={"Origin": server.base_url, "Sec-Fetch-Site": "same-origin"},
            fail_on_status_code=False,
        )
        deliberate_http_failures.append({"path": "/opportunity-slate/source/delete", "status": delete_response.status})
        check("failed delete returns 503", delete_response.status == 503, delete_response.status)
        page.set_content(delete_response.text(), wait_until="networkidle")
        check("failed delete reports unknown outcome", "could not verify whether the last change reached storage" in page.locator(".os2-card--error").inner_text())
        check("failed delete leaves review intact", page.locator("#os2-corrected-text").input_value() == SOURCE_TWO)
        page.goto(room_url, wait_until="networkidle")
        page.locator(".os2-disclosure--danger details").evaluate("el => el.open = true")
        page.locator(".os2-disclosure--danger button").click()
        page.wait_for_load_state("networkidle")
        check("confirmed delete returns to empty intake", page.locator("h1").inner_text() == "Bring in a role.")

        check("no unexpected browser HTTP failures", not bad_responses, bad_responses)
        check("no console errors", not console_errors, console_errors)
        check("no page errors", not page_errors, page_errors)
        context.close()
        browser.close()

    patcher.stop()

    # Exact package error-injection factory requested by the handoff.
    error_app, _error_database, error_patcher = make_app(error=DatabaseServiceError("injected database failure"))
    error_app.config["TESTING"] = False
    error_app.add_url_rule(
        "/auth/session",
        endpoint="gauntlet_error_auth_session",
        view_func=lambda: {"authenticated": True},
    )
    with LocalServer(error_app) as error_server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1372, "height": 1146})
        response = page.goto(error_server.base_url + "/opportunity-slate", wait_until="networkidle")
        check("make_app(error=...) returns 503", response.status == 503, response.status)
        check("make_app(error=...) renders honest unavailable state", "couldn't open your Opportunity Slate" in page.locator(".os2-card--error").inner_text())
        check("make_app(error=...) exposes Retry-After", response.headers.get("retry-after") == "5", response.headers.get("retry-after"))
        browser.close()
    error_patcher.stop()

    evidence = {
        "instrument": "functional_gauntlet_v2.py",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "summary": {
            "passed": sum(1 for item in checks if item["passed"]),
            "failed": sum(1 for item in checks if not item["passed"]),
            "console_errors": console_errors,
            "page_errors": page_errors,
            "deliberate_http_failures": deliberate_http_failures,
            "database_save_count": database.save_count,
            "database_call_count": len(database.calls),
        },
    }
    output_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence["summary"], indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: functional_gauntlet_v2.py <evidence.json>")
    main(Path(sys.argv[1]))
