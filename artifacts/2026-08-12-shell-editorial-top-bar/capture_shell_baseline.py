"""PS-SHELL-001 — pre-tokenization shell screenshot baseline.

The package sequence captures this baseline against the COMPLETED shell,
immediately before tokenization, and diffs it again afterwards. Any non-zero
diff at that point is a defect or the single authorized focus correction.
The new shell legitimately changes navigation geometry, so this baseline is
deliberately NOT comparable to production before this change.

Review finding F14: a baseline made only of CLOSED-shell crops is blind
exactly where the colour lives. The account menu, the More sheet, the room
switcher list, the search results, hover and focus all carry shell colour and
none of them appears in a closed header. Every one of those states is captured
here, so the token step's "any non-zero diff is a defect" gate can actually
see what it is gating.

Two servers, because the shell's signed-in markup is server-derived and
faking it in the DOM would not exercise the real render:

    python -c "from app import app; app.run(port=5057, use_reloader=False)"
    python -c "from app import app; \
        app.config['PEERSLATE_ALLOW_DEV_IDENTITY']=True; \
        app.config['PEERSLATE_DEV_USER_KEY']='shell-baseline'; \
        app.run(port=5058, use_reloader=False)"
    python artifacts/2026-08-12-shell-editorial-top-bar/capture_shell_baseline.py \
        artifacts/2026-08-12-shell-editorial-top-bar/baseline
"""
import hashlib
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = {"signed-out": "http://127.0.0.1:5057", "signed-in": "http://127.0.0.1:5058"}
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "baseline")
OUT.mkdir(parents=True, exist_ok=True)

VIEWPORTS = [
    ("1440x900", 1440, 900),
    ("1280x800", 1280, 800),
    ("1100x800", 1100, 800),
    ("1024x800", 1024, 800),
    ("768x900", 768, 900),
    ("390x844", 390, 844),
    ("320x700", 320, 700),
    ("720x450", 720, 450),
]
ROUTES = ["/", "/interview-studio", "/opportunity-slate", "/petec/resume"]

digests = {}


def shot(page, name, width, height, top=0):
    path = OUT / (name + ".png")
    page.screenshot(path=str(path),
                    clip={"x": 0, "y": top, "width": width, "height": height})
    digests[name] = hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def open_states(page, browser_name, width, height):
    """Every state that puts shell colour on screen."""
    # Room switcher list (medium width only).
    trigger = page.query_selector("[data-platform-roomswitcher-trigger]")
    if trigger and trigger.is_visible():
        trigger.click()
        page.wait_for_timeout(150)
        shot(page, browser_name + "_switcher-open", width, min(height, 420))
        page.keyboard.press("Escape")
        page.wait_for_timeout(120)

    # Account menu.
    account = page.query_selector("[data-platform-account-trigger]")
    if account and account.is_visible():
        account.click()
        page.wait_for_timeout(150)
        shot(page, browser_name + "_account-open", width, min(height, 260))
        page.keyboard.press("Escape")
        page.wait_for_timeout(120)

    # More sheet / header Menu sheet.
    opener = page.query_selector(".mobile-tabbar__item--more")
    if not (opener and opener.is_visible()):
        opener = page.query_selector("[data-platform-menu-toggle]")
    if opener and opener.is_visible():
        opener.click()
        page.wait_for_timeout(180)
        shot(page, browser_name + "_sheet-open", width, min(height, 520))
        page.keyboard.press("Escape")
        page.wait_for_timeout(120)

    # Search: results, and the honest empty state.
    field = page.query_selector("#nav-search-input")
    if field and field.is_visible():
        field.click()
        page.fill("#nav-search-input", "resume")
        page.wait_for_timeout(200)
        shot(page, browser_name + "_search-results", width, min(height, 380))
        page.fill("#nav-search-input", "zzzznothing")
        page.wait_for_timeout(200)
        shot(page, browser_name + "_search-empty", width, min(height, 260))
        page.fill("#nav-search-input", "")
        page.keyboard.press("Escape")
        page.wait_for_timeout(120)

    # Hover and keyboard focus on a destination.
    link = page.query_selector(".platform-nav__links a:not([aria-current])")
    if link and link.is_visible():
        link.hover()
        page.wait_for_timeout(120)
        shot(page, browser_name + "_nav-hover", width, 90)
        page.keyboard.press("Tab")
        page.keyboard.press("Tab")
        page.keyboard.press("Tab")
        page.wait_for_timeout(120)
        shot(page, browser_name + "_nav-focus", width, 90)


with sync_playwright() as p:
    browser = p.chromium.launch()
    for route in ROUTES:
        slug = route.strip("/").replace("/", "-") or "home"
        for viewport, w, h in VIEWPORTS:
            for auth, base in BASE.items():
                page = browser.new_page(viewport={"width": w, "height": h})
                page.goto(base + route, wait_until="domcontentloaded", timeout=20000)
                page.wait_for_timeout(500)
                name = f"{slug}_{viewport}_{auth}"
                band = 130 if route != "/petec/resume" else 190
                shot(page, name + "_header", w, band)
                if w <= 743:
                    shot(page, name + "_bottombar", w, 70, top=h - 70)
                # The open states are shell-owned and render identically on
                # every route, so they are captured on one room that has an
                # active destination and one page that has none, at the four
                # widths where the shell's structure differs. Capturing them
                # on all 4 routes x 8 viewports adds 28MB of duplicates and
                # no additional colour surface.
                if route in ("/", "/interview-studio") and viewport in (
                    "1440x900", "1100x800", "390x844", "320x700"
                ):
                    open_states(page, name, w, h)
                page.close()

    # 200% text: the same header at a doubled root font size, which is what a
    # browser zoom of 200% does to a rem-based shell.
    for auth, base in BASE.items():
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(base + "/interview-studio", wait_until="domcontentloaded")
        page.add_style_tag(content="html { font-size: 200%; }")
        page.wait_for_timeout(300)
        shot(page, f"interview-studio_200pct_{auth}_header", 1440, 220)
        page.close()
    browser.close()

(OUT / "DIGESTS.json").write_text(
    json.dumps(digests, indent=1, sort_keys=True), encoding="utf-8")
print(f"captured {len(digests)} shell frames into {OUT}")
