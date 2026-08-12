"""Fable's capture + measure harness for the Interview Studio visual rebuild.

Usage:
  python capture_measure.py capture <state> [...]   -> capture named states to OUT
  python capture_measure.py measure <capture.png>   -> region-measure a capture vs its lock

Starts the app from the implementation worktree with the flag ON and a dev
identity (owner-mapped), captures locked-visual states at the lock's native
size, and measures fills/inks with the same region method used on the locks.
"""
import os
import subprocess
import sys
import time
import urllib.request

WT = r"C:\Users\peter\Documents\portfolio-interview-studio-auth-20260811"
VENV_PY = r"C:\Users\peter\Documents\portfolio\venv\Scripts\python.exe"
OUT = os.path.join(WT, "artifacts", "2026-08-11-interview-studio-authenticated", "fable-rebuild")
LOCKS = r"C:\Users\peter\iCloudDrive\PeerSlate Architect Handoffs\2026-08-11\Interview Studio Claude Architecture Handoff 2026-08-11\02_VISUAL_AUTHORITY\FINAL"
PORT = 5011
BASE = f"http://127.0.0.1:{PORT}"

ENV = {
    **os.environ,
    "ANTHROPIC_API_KEY": "test-placeholder-key",
    "PEERSLATE_INTERVIEW_STUDIO_AUTHENTICATED": "true",
    "PEERSLATE_ALLOW_DEV_IDENTITY": "true",
    "PEERSLATE_DEV_USER_KEY": "fable-rebuild-owner",
    "PEERSLATE_OWNER_USER_KEYS": "fable-rebuild-owner",
    "PORT": str(PORT),
    "FLASK_DEBUG": "0",
}

DESKTOP = (1672, 941)
MOBILE = (864, 1821)

# state name -> (url path, viewport, setup callable name)
STATES = {
    "01-interview-me-ready-authenticated": ("/interview-studio?mode=me", DESKTOP, "seed_draft"),
    "07-interview-ai-best-practice": ("/interview-studio?mode=ai", DESKTOP, None),
    "09-video-practice-preview": ("/interview-studio?mode=video", DESKTOP, None),
    "12-history-populated": ("/interview-studio/history", DESKTOP, "seed_history"),
    "16-history-empty-storage-available": ("/interview-studio/history", DESKTOP, None),
    "13-mobile-interview-me-ready": ("/interview-studio?mode=me", MOBILE, "seed_draft"),
}

DRAFT_TEXT = (
    "When priorities conflict, I start by clarifying the goal, the constraint, "
    "and who is most affected. Then I weigh the trade-offs and focus on the "
    "option that creates the most value now without hurting the long-term "
    "outcome.\n\nI align with stakeholders on what matters most, make the "
    "call, and communicate it clearly. If new information changes the "
    "picture, I adjust quickly."
)


def start_server():
    proc = subprocess.Popen(
        [VENV_PY, "app.py"], cwd=WT, env=ENV,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    for _ in range(60):
        try:
            urllib.request.urlopen(BASE + "/healthz", timeout=1)
            return proc
        except Exception:
            time.sleep(0.5)
    proc.kill()
    raise RuntimeError("server did not start")


def capture(names):
    from playwright.sync_api import sync_playwright
    os.makedirs(OUT, exist_ok=True)
    proc = start_server()
    errors = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            for name in names:
                path, viewport, setup = STATES[name]
                ctx = browser.new_context(viewport={"width": viewport[0], "height": viewport[1]},
                                          device_scale_factor=1)
                page = ctx.new_page()
                page.on("pageerror", lambda e: errors.append(str(e)))
                page.goto(BASE + path, wait_until="load")
                page.wait_for_timeout(1800)
                if setup == "seed_draft":
                    page.fill("#is-answer", DRAFT_TEXT)
                    page.wait_for_timeout(900)
                page.evaluate("document.activeElement && document.activeElement.blur()")
                probe = page.evaluate("""() => {
                    const pick = (sel) => {
                        const el = document.querySelector(sel);
                        if (!el) return null;
                        const r = el.getBoundingClientRect();
                        return {x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height)};
                    };
                    return {badge: pick('[data-is-draft-badge]'), composer: pick('.is__composer'),
                            btn: pick('[data-is-review]')};
                }""")
                print("probe:", probe)
                page.wait_for_timeout(500)
                dest = os.path.join(OUT, name + ".png")
                page.screenshot(path=dest, full_page=False)
                print("captured", dest)
                ctx.close()
            browser.close()
    finally:
        proc.kill()
    if errors:
        print("PAGE ERRORS:", *errors, sep="\n  ")


def measure(capture_path):
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "pylibs"))
    from PIL import Image
    from collections import Counter
    import statistics

    name = os.path.basename(capture_path)
    lock_path = os.path.join(LOCKS, name)
    for tag, pth in (("BUILD", capture_path), ("LOCK ", lock_path)):
        img = Image.open(pth).convert("RGB")
        w, h = img.size

        def mode_color(box):
            c = Counter(img.crop(box).getdata()).most_common(1)[0][0]
            return "#%02x%02x%02x" % c

        def dark(box, pct=0.10):
            pix = list(img.crop(box).getdata())
            pix.sort(key=lambda p: sum(p))
            sel = pix[:max(1, int(len(pix) * pct))]
            return "#%02x%02x%02x" % tuple(int(statistics.median(p[i] for p in sel)) for i in range(3))

        # proportional regions so both images use their own geometry
        print(f"{tag} {name} ({w}x{h})")
        print("   canvas         ", mode_color((int(w*0.20), int(h*0.50), int(w*0.26), int(h*0.62))))
        print("   rail bg        ", mode_color((int(w*0.02), int(h*0.42), int(w*0.17), int(h*0.60))))
        print("   question ink   ", dark((int(w*0.27), int(h*0.18), int(w*0.78), int(h*0.31))))
        print("   primary greens :", end=" ")
        pix = [p for p in img.crop((0, int(h*0.70), w, h)).getdata()
               if p[1] > p[0] + 15 and p[1] > p[2] + 10]
        if pix:
            c = Counter(pix).most_common(1)[0][0]
            print("#%02x%02x%02x" % c, f"({len(pix)} px)")
        else:
            print("none found")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "capture":
        capture(sys.argv[2:] or list(STATES))
    elif cmd == "measure":
        measure(sys.argv[2])
