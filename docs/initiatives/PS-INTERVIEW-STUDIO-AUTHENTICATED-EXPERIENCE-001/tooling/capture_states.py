"""Fable state-capture harness v2: drives the REAL client flow with
route-intercepted fixture responses, so every captured state is produced by
the actual state machinery (no DOM injection).

Usage: python capture_states.py <state> [...]   (no args = all)
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

WT = r"C:\Users\peter\Documents\portfolio-interview-studio-auth-20260811"
VENV_PY = r"C:\Users\peter\Documents\portfolio\venv\Scripts\python.exe"
OUT = os.path.join(WT, "artifacts", "2026-08-11-interview-studio-authenticated", "fable-rebuild")
PORT = 5013
BASE = f"http://127.0.0.1:{PORT}"

ENV = {
    **os.environ,
    "ANTHROPIC_API_KEY": "test-placeholder-key",
    "PEERSLATE_INTERVIEW_STUDIO_AUTHENTICATED": "true",
    "PEERSLATE_ALLOW_DEV_IDENTITY": "true",
    "PEERSLATE_DEV_USER_KEY": "fable-rebuild-owner",
    "PEERSLATE_OWNER_USER_KEYS": "fable-rebuild-owner",
    "PORT": str(PORT),
}

DESKTOP = {"width": 1672, "height": 941}
MOBILE = {"width": 864, "height": 1821}

DRAFT = ("When priorities conflict, I start by clarifying the goal, the "
         "constraint, and who is most affected. Then I weigh the trade-offs and "
         "focus on the option that creates the most value now without hurting "
         "the long-term outcome.\n\nI align with stakeholders on what matters "
         "most, make the call, and communicate it clearly. If new information "
         "changes the picture, I adjust quickly.")

BEHAVIORAL_DIMS = ["situation_clarity", "action_ownership", "evidence", "outcome", "reflection"]

REVIEW = {"review": {
    "verdict": "Strong foundation",
    "encouragement": "Clear ownership and a useful result.",
    "whatCameThroughClearly": ["You named a concrete situation.", "Your ownership is visible."],
    "dimensions": [
        {"key": k, "status": ("clear" if i < 2 else "developing"),
         "rationale": f"{k.replace('_', ' ').title()} is specific.",
         "nextAction": f"Strengthen {k.replace('_', ' ')}."}
        for i, k in enumerate(BEHAVIORAL_DIMS)
    ],
    "strengths": ["Clear ownership.", "Professional judgment."],
    "improvements": ["Clarify the task.", "Quantify the result."],
    "strongerApproach": "Open with the challenge, explain your action, and close with one observable result.",
    "focusedFollowUp": "What changed after your action?",
    "evidenceSuggestions": [],
    "reviewVersion": "v2",
}}

IMPROVE = {"improvement": {
    "draft": ("When priorities conflict, I start by clarifying the goal, the "
              "constraint, and who is most affected. In one situation, "
              "[Describe the moment and what priorities were in conflict.] I "
              "decided to [Describe the decision you personally made and why.] "
              "I aligned with the right people, explained the trade-offs, and "
              "focused on the option that created the most value at that time. "
              "As a result, [Describe the outcome or what changed.] If new "
              "information changed the picture, I adjusted quickly."),
    "changes": ["Adds a concrete situation.", "Names your personal decision.", "Closes with an observable outcome."],
    "confirmations": [
        "[Describe the moment and what priorities were in conflict.]",
        "[Describe the decision you personally made and why.]",
        "[Describe the outcome or what changed.]",
    ],
    "evidenceUsed": [],
}}

MODEL_GENERIC = {"mode": "best_practice",
    "modelAnswer": {"status": "answered", "generic": True,
        "answer": ("In a product launch, engineering needed more time while sales had "
                   "committed to a date. I clarified that protecting customer trust was "
                   "the shared goal, separated must-have work from work we could phase, "
                   "and recommended a smaller, reliable first release. We launched the "
                   "core experience on time, avoided critical defects, and delivered the "
                   "remaining improvements the following week."),
        "whyItWorks": ["Frames the shared outcome.", "Owns the decision.", "Ends with an observable result."],
        "evidenceUsed": []},
    "contextToken": "", "profile": {"displayName": "Pete Carter", "firstName": "Pete"}}

MODEL_INSUFFICIENT = {"mode": "member_history",
    "modelAnswer": {"status": "insufficient",
        "answer": "PeerSlate does not have enough approved profile evidence to answer this question without guessing.",
        "whyItWorks": ["Avoids unsupported claims and makes the evidence gap explicit."],
        "evidenceUsed": []},
    "contextToken": "", "profile": {"displayName": "Pete Carter", "firstName": "Pete"}}


def start_server():
    proc = subprocess.Popen([VENV_PY, "app.py"], cwd=WT, env=ENV,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        try:
            urllib.request.urlopen(BASE + "/healthz", timeout=1)
            return proc
        except Exception:
            time.sleep(0.5)
    proc.kill()
    raise RuntimeError("server did not start")


def fulfill(route, payload, status=200, delay=0):
    if delay:
        time.sleep(delay)
    route.fulfill(status=status, content_type="application/json", body=json.dumps(payload))


def goto(page, path, viewport_note=""):
    page.goto(BASE + path, wait_until="load")
    page.wait_for_timeout(1600)


def seed_and_submit(page):
    goto(page, "/interview-studio?mode=me")
    page.fill("#is-answer", DRAFT)
    page.wait_for_timeout(400)
    page.click("[data-is-review]")
    page.wait_for_timeout(1200)


def shoot(page, name):
    page.evaluate("document.activeElement && document.activeElement.blur()")
    page.wait_for_timeout(350)
    page.screenshot(path=os.path.join(OUT, name + ".png"), full_page=False)
    print("captured", name)


def scroll_to(page, selector):
    page.eval_on_selector(selector, "el => el.scrollIntoView({block: 'start'})")
    page.wait_for_timeout(300)


def run(names):
    from playwright.sync_api import sync_playwright
    os.makedirs(OUT, exist_ok=True)
    proc = start_server()
    errors = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=[
                "--use-fake-device-for-media-capture",
                "--use-fake-ui-for-media-stream",
            ])

            MEDIA_SHIM = """
                (() => {
                    const draw = (canvas) => {
                        const c = canvas.getContext('2d');
                        const g = c.createLinearGradient(0, 0, canvas.width, canvas.height);
                        g.addColorStop(0, '#233a55');
                        g.addColorStop(1, '#101d31');
                        const tick = () => {
                            c.fillStyle = g;
                            c.fillRect(0, 0, canvas.width, canvas.height);
                            c.fillStyle = 'rgba(255,255,255,0.55)';
                            c.beginPath();
                            c.arc(canvas.width / 2, canvas.height / 2 - 40, 90, 0, Math.PI * 2);
                            c.fill();
                            c.fillRect(canvas.width / 2 - 150, canvas.height / 2 + 80, 300, 160);
                            requestAnimationFrame(tick);
                        };
                        tick();
                    };
                    navigator.mediaDevices.getUserMedia = async (constraints) => {
                        const canvas = document.createElement('canvas');
                        canvas.width = 1280; canvas.height = 720;
                        draw(canvas);
                        const stream = canvas.captureStream(30);
                        if (constraints && constraints.audio) {
                            const ac = new AudioContext();
                            const osc = ac.createOscillator();
                            const dest = ac.createMediaStreamDestination();
                            const gain = ac.createGain();
                            gain.gain.value = 0.001;
                            osc.connect(gain); gain.connect(dest); osc.start();
                            dest.stream.getAudioTracks().forEach(t => stream.addTrack(t));
                        }
                        return stream;
                    };
                })();
            """

            def new_page(viewport, media=False):
                kwargs = {"viewport": viewport, "device_scale_factor": 1}
                if media:
                    kwargs["permissions"] = ["camera", "microphone"]
                ctx = browser.new_context(**kwargs)
                pg = ctx.new_page()
                if media:
                    pg.add_init_script(MEDIA_SHIM)
                pg.on("pageerror", lambda e: errors.append(str(e)))
                return ctx, pg

            if "02-interview-me-review-processing" in names:
                ctx, page = new_page(DESKTOP)
                held = []
                page.route("**/api/interview/review", lambda r: held.append(r))
                goto(page, "/interview-studio?mode=me")
                page.fill("#is-answer", DRAFT)
                page.wait_for_timeout(400)
                page.click("[data-is-review]")
                page.wait_for_timeout(1500)
                shoot(page, "02-interview-me-review-processing")
                for r in held:
                    try:
                        r.abort()
                    except Exception:
                        pass
                ctx.close()

            if "03-interview-me-review-failure" in names:
                ctx, page = new_page(DESKTOP)
                page.route("**/api/interview/review",
                           lambda r: fulfill(r, {"error": "The coach returned an unreadable review. Please try again."}, status=502))
                seed_and_submit(page)
                page.wait_for_timeout(2500)
                shoot(page, "03-interview-me-review-failure")
                ctx.close()

            if "04-06 chain" or True:
                pass

            chain = {"04a-interview-me-coaching-appended-top", "04b-interview-me-coaching-detail-actions",
                     "05-interview-me-improvement-appended", "06-interview-me-revised-coaching"} & set(names)
            if chain:
                ctx, page = new_page(DESKTOP)
                page.route("**/api/interview/review", lambda r: fulfill(r, REVIEW))
                page.route("**/api/interview/improve", lambda r: fulfill(r, IMPROVE))
                seed_and_submit(page)
                page.wait_for_timeout(2000)
                if "04a-interview-me-coaching-appended-top" in names:
                    scroll_to(page, "[data-is-submitted], .is__answer-card")
                    shoot(page, "04a-interview-me-coaching-appended-top")
                if "04b-interview-me-coaching-detail-actions" in names:
                    scroll_to(page, ".is-stack__table")
                    shoot(page, "04b-interview-me-coaching-detail-actions")
                if "05-interview-me-improvement-appended" in names:
                    page.click(".is-stack__action-btn--primary:has-text('Improve My Answer')")
                    page.wait_for_timeout(2200)
                    scroll_to(page, "[data-is-stack-answer-context], .is-stack__actions")
                    shoot(page, "05-interview-me-improvement-appended")
                ctx.close()

            if "06-interview-me-revised-coaching" in names:
                ctx, page = new_page(DESKTOP)
                page.route("**/api/interview/review", lambda r: fulfill(r, REVIEW))
                page.route("**/api/interview/improve", lambda r: fulfill(r, IMPROVE))
                seed_and_submit(page)
                page.wait_for_timeout(1800)
                page.click(".is-stack__action-btn--primary:has-text('Improve My Answer')")
                page.wait_for_timeout(2000)
                resolved = IMPROVE["improvement"]["draft"]
                for marker in IMPROVE["improvement"]["confirmations"]:
                    resolved = resolved.replace(marker, "I resolved this detail with a real example from my work.")
                page.fill(".is-stack__improve-draft", resolved)
                page.wait_for_timeout(500)
                page.click(".is-stack__action-btn--primary:has-text('Review Revised Answer')")
                page.wait_for_timeout(2500)
                count = page.evaluate("document.querySelectorAll('.is-stack__coaching').length")
                print("stack coaching sections:", count)
                page.evaluate("""() => {
                    const nodes = document.querySelectorAll('.is-stack__coaching');
                    if (nodes.length) nodes[nodes.length - 1].scrollIntoView({block: 'start'});
                }""")
                page.wait_for_timeout(400)
                shoot(page, "06-interview-me-revised-coaching")
                ctx.close()

            if "10-video-practice-local-playback" in names:
                ctx, page = new_page(DESKTOP, media=True)
                goto(page, "/interview-studio?mode=video")
                page.click("[data-is-camera-enable]")
                page.wait_for_timeout(2000)
                page.click("[data-is-record-start]")
                page.wait_for_timeout(2500)
                page.click("[data-is-record-stop]")
                page.wait_for_timeout(2500)
                shoot(page, "10-video-practice-local-playback")
                ctx.close()

            if "14a-mobile-coaching-detail" in names:
                ctx, page = new_page(MOBILE)
                page.route("**/api/interview/review", lambda r: fulfill(r, REVIEW))
                seed_and_submit(page)
                page.wait_for_timeout(1800)
                scroll_to(page, ".is-stack__table")
                shoot(page, "14a-mobile-coaching-detail")
                ctx.close()

            if "14b-mobile-improvement-confirmation" in names:
                ctx, page = new_page(MOBILE)
                page.route("**/api/interview/review", lambda r: fulfill(r, REVIEW))
                page.route("**/api/interview/improve", lambda r: fulfill(r, IMPROVE))
                seed_and_submit(page)
                page.wait_for_timeout(1800)
                page.click(".is-stack__action-btn--primary:has-text('Improve My Answer')")
                page.wait_for_timeout(2200)
                scroll_to(page, ".is-stack__draft-box")
                shoot(page, "14b-mobile-improvement-confirmation")
                ctx.close()

            if "17-history-storage-unavailable" in names:
                ctx, page = new_page(DESKTOP)
                page.add_init_script("""
                    const deadStorage = {
                        getItem() { throw new DOMException('blocked', 'SecurityError'); },
                        setItem() { throw new DOMException('blocked', 'SecurityError'); },
                        removeItem() { throw new DOMException('blocked', 'SecurityError'); },
                        key() { throw new DOMException('blocked', 'SecurityError'); },
                        clear() { throw new DOMException('blocked', 'SecurityError'); },
                        get length() { throw new DOMException('blocked', 'SecurityError'); },
                    };
                    Object.defineProperty(window, 'localStorage', { get: () => deadStorage });
                """)
                goto(page, "/interview-studio/history")
                shoot(page, "17-history-storage-unavailable")
                ctx.close()

            if "15-video-practice-permission-unavailable" in names:
                ctx, page = new_page(DESKTOP)
                goto(page, "/interview-studio?mode=video")
                if page.query_selector("[data-is-camera-enable]"):
                    page.click("[data-is-camera-enable]")
                page.wait_for_timeout(2500)
                shoot(page, "15-video-practice-permission-unavailable")
                ctx.close()

            if "07-interview-ai-best-practice" in names:
                ctx, page = new_page(DESKTOP)
                page.route("**/api/interview/model-answer", lambda r: fulfill(r, MODEL_GENERIC))
                goto(page, "/interview-studio?mode=ai")
                page.check("[data-is-ai-source-radio][value='best_practice']")
                page.click("[data-is-ai-form] button[type=submit]")
                page.wait_for_timeout(2000)
                shoot(page, "07-interview-ai-best-practice")
                ctx.close()

            if "08-interview-ai-insufficient-evidence" in names:
                ctx, page = new_page(DESKTOP)
                page.route("**/api/interview/model-answer", lambda r: fulfill(r, MODEL_INSUFFICIENT))
                goto(page, "/interview-studio?mode=ai")
                page.check("[data-is-ai-source-radio][value='member_history']")
                page.click("[data-is-ai-form] button[type=submit]")
                page.wait_for_timeout(2000)
                shoot(page, "08-interview-ai-insufficient-evidence")
                ctx.close()

            if "09-video-practice-preview" in names:
                ctx, page = new_page(DESKTOP, media=True)
                goto(page, "/interview-studio?mode=video")
                if page.query_selector("[data-is-camera-enable]"):
                    page.click("[data-is-camera-enable]")
                page.wait_for_timeout(2500)
                shoot(page, "09-video-practice-preview")
                ctx.close()

            if "11-session-complete" in names:
                ctx, page = new_page(DESKTOP)
                page.route("**/api/interview/review", lambda r: fulfill(r, REVIEW))
                seed_and_submit(page)
                page.wait_for_timeout(1500)
                page.click("[data-is-finish-session]")
                page.wait_for_timeout(1200)
                shoot(page, "11-session-complete")
                ctx.close()

            if "12-history-populated" in names:
                ctx, page = new_page(DESKTOP)
                page.route("**/api/interview/review", lambda r: fulfill(r, REVIEW))
                seed_and_submit(page)
                page.wait_for_timeout(1500)
                goto(page, "/interview-studio/history")
                shoot(page, "12-history-populated")
                ctx.close()

            if "16-history-empty-storage-available" in names:
                ctx, page = new_page(DESKTOP)
                goto(page, "/interview-studio/history")
                shoot(page, "16-history-empty-storage-available")
                ctx.close()

            if "13-mobile-interview-me-ready" in names:
                ctx, page = new_page(MOBILE)
                goto(page, "/interview-studio?mode=me")
                page.fill("#is-answer", DRAFT)
                page.wait_for_timeout(600)
                page.evaluate("window.scrollTo(0, 0)")
                shoot(page, "13-mobile-interview-me-ready")
                ctx.close()

            browser.close()
    finally:
        proc.kill()
    if errors:
        print("PAGE ERRORS:", *errors, sep="\n  ")


ALL = ["02-interview-me-review-processing", "03-interview-me-review-failure",
       "04a-interview-me-coaching-appended-top", "04b-interview-me-coaching-detail-actions",
       "05-interview-me-improvement-appended", "07-interview-ai-best-practice",
       "08-interview-ai-insufficient-evidence", "09-video-practice-preview",
       "11-session-complete", "12-history-populated", "16-history-empty-storage-available",
       "13-mobile-interview-me-ready"]

if __name__ == "__main__":
    run(sys.argv[1:] or ALL)
