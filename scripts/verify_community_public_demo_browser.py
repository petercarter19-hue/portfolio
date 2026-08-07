"""Deterministic browser proof for the Community no-publish Voice sandbox.

The real Community JavaScript runs in Chrome. A tiny in-browser MediaRecorder
double supplies a non-empty recording, while Playwright records every request
to the production transcription route. The signed-out exercise must stay
entirely local; the signed-in exercise may receive and insert a reviewable
transcript, but the demo form must still expose no submit control.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request
from contextlib import contextmanager
from pathlib import Path

from playwright.sync_api import Route, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
PREVIEW = ROOT / "scripts" / "preview_community_public_demo.py"
EVIDENCE = (
    ROOT
    / "docs"
    / "initiatives"
    / "PS-COMMUNITY-PUBLIC-PILOT-001"
    / "evidence"
    / "2026-08-07-public-demo"
    / "voice-no-publish-browser-proof.json"
)
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")

MEDIA_RECORDER_DOUBLE = r"""
(() => {
  const track = {stop() { window.__communityTrackStops = (window.__communityTrackStops || 0) + 1; }};
  const stream = {getTracks() { return [track]; }};
  Object.defineProperty(navigator, 'mediaDevices', {
    configurable: true,
    value: {getUserMedia: async () => stream}
  });
  class DeterministicMediaRecorder {
    constructor() { this.mimeType = 'audio/webm'; this.listeners = {}; }
    addEventListener(name, listener) { this.listeners[name] = listener; }
    start() { this.state = 'recording'; }
    stop() {
      this.state = 'inactive';
      this.listeners.dataavailable({data: new Blob(['voice-proof'], {type: this.mimeType})});
      this.listeners.stop();
    }
  }
  Object.defineProperty(window, 'MediaRecorder', {
    configurable: true,
    value: DeterministicMediaRecorder
  });
})();
"""


@contextmanager
def preview_server(*, owner: bool, port: int):
    env = os.environ.copy()
    env["PEERSLATE_PUBLIC_DEMO_PREVIEW_PORT"] = str(port)
    env["PEERSLATE_PUBLIC_DEMO_PREVIEW_OWNER"] = "true" if owner else "false"
    process = subprocess.Popen(
        [sys.executable, str(PREVIEW)],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}/the-slate"
    try:
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError("Community preview server exited before it was ready.")
            try:
                with urllib.request.urlopen(url, timeout=1) as response:
                    if response.status == 200:
                        break
            except OSError:
                time.sleep(0.1)
        else:
            raise RuntimeError("Community preview server did not become ready.")
        yield url
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def exercise(browser, *, owner: bool, port: int) -> dict[str, object]:
    transcription_requests: list[str] = []

    def handle_transcription(route: Route) -> None:
        transcription_requests.append(route.request.url)
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "success": True,
                    "proposal": {
                        "text": "Voice proposal from deterministic browser proof.",
                        "confidence": None,
                    },
                }
            ),
        )

    with preview_server(owner=owner, port=port) as url:
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()
        page.set_default_timeout(10_000)
        page.add_init_script(MEDIA_RECORDER_DOUBLE)
        page.route("**/api/v1/community/voice/transcriptions", handle_transcription)
        page.goto(url, wait_until="domcontentloaded")
        page.locator("[data-demo-quick-compose]").wait_for(state="visible")
        page.get_by_role("button", name="Try a Community post with text or Voice").click()
        dialog = page.locator("[data-demo-composer]")
        dialog.locator("[data-demo-composer-voice]").click()
        dialog.locator('[data-voice-state="recording"]').wait_for()
        dialog.get_by_role("button", name="Stop").click()

        body = dialog.locator('[name="body"]')
        if owner:
            dialog.locator('[data-voice-state="preview"]').wait_for()
            dialog.get_by_role("button", name="Use transcript").click()
            expected = "Voice proposal from deterministic browser proof."
            if body.input_value() != expected:
                raise AssertionError("Signed-in reviewed transcript was not inserted.")
            if len(transcription_requests) != 1:
                raise AssertionError("Signed-in Voice must make exactly one transcription request.")
            voice_state = "reviewed-transcript-inserted"
        else:
            dialog.locator('[data-voice-state="local-review"]').wait_for()
            if transcription_requests:
                raise AssertionError("Signed-out Voice attempted to leave the browser.")
            if body.input_value():
                raise AssertionError("Signed-out local audio invented a transcript.")
            voice_state = "local-review-no-upload"

        submit_controls = dialog.locator(
            'button[type="submit"], input[type="submit"], [data-publish]'
        ).count()
        if submit_controls:
            raise AssertionError("The public demo composer exposed a submit control.")
        if dialog.get_by_text("there is deliberately no Publish button", exact=False).count() != 1:
            raise AssertionError("The no-publish boundary is not explained in the demo.")

        result = {
            "owner": owner,
            "voice_state": voice_state,
            "transcription_request_count": len(transcription_requests),
            "transcript_inserted": bool(body.input_value()),
            "submit_control_count": submit_controls,
            "track_stop_count": page.evaluate("window.__communityTrackStops || 0"),
        }
        context.close()
        return result


def main() -> None:
    if not CHROME.exists():
        raise RuntimeError(f"Google Chrome was not found at {CHROME}.")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=str(CHROME), headless=True)
        try:
            results = {
                "proof": "Community public-demo Voice and no-publish browser boundary",
                "signed_out": exercise(browser, owner=False, port=5087),
                "signed_in_owner": exercise(browser, owner=True, port=5088),
            }
        finally:
            browser.close()
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
