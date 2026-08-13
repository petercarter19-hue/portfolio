"""Prove the --ps-shell-* layer is inert by COMPUTED STYLE, not by pixels.

Screenshot comparison has a noise floor: font rasterisation and interaction
timing move pixels between runs, so a frame diff cannot separate a real
regression from capture jitter. This does.

For each route, auth state, viewport and open state it snapshots every CSS
property of every node under the shell, swaps the stylesheet for its
de-tokenized twin IN THE SAME LIVE DOM, snapshots again, and reports any
property whose computed value moved. Custom properties are excluded on
purpose: --ps-shell-* exists in one variant and not the other, which is the
point of the change rather than an effect of it.

    python verify_tokenization_computed.py
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from detokenize import detokenize  # noqa: E402

OUT = "http://127.0.0.1:5057"
IN = "http://127.0.0.1:5058"
ROOT = Path(__file__).resolve().parents[2]
DETOKENIZED = detokenize((ROOT / "static/css/public-navigation.css").read_text(encoding="utf-8"))

VIEWPORTS = [(1440, 900), (1280, 800), (1100, 800), (1024, 800),
             (768, 900), (390, 844), (320, 700)]
# /experience is in this list on purpose from 2026-08-13: it is the one route
# base.html does not give body.slate-light, so it is the only route where the
# family is no longer a pure alias, and a proof that never visits it would be
# proving the wrong thing.
ROUTES = ["/", "/experience", "/peerslate", "/interview-studio",
          "/opportunity-slate", "/petec/resume"]

# The owner colour round's six pinned values, written as the exact pair the
# engine serialises: (what the token layer paints, what no token layer would).
# A delta is EXPECTED only if substituting these pairs into the tokenized value
# reproduces the de-tokenized one — which also covers compound values such as
# box-shadow and any property that inherits from color.
PINNED = [
    ("rgb(6, 26, 58)", "rgb(22, 33, 58)"),            # --ps-shell-text
    ("rgb(217, 226, 236)", "rgb(229, 231, 236)"),     # --ps-shell-border
    ("rgb(73, 97, 122)", "rgb(92, 101, 117)"),        # --ps-shell-text-muted
    ("rgb(244, 248, 253)", "rgb(246, 247, 249)"),     # --ps-shell-rail
    ("rgba(11, 99, 229, 0.08)", "rgba(47, 111, 224, 0.09)"),  # accent-soft
    ("rgba(6, 26, 58, 0.08) 0px 12px 30px 0px",
     "rgba(23, 33, 58, 0.07) 0px 10px 26px 0px"),     # --ps-shell-shadow
]
PINNED_ROUTE = "/experience"


def is_pinned_delta(route, before, after):
    """True when this delta is exactly the cross-route correction."""
    if route != PINNED_ROUTE:
        return False
    rewritten = before
    for tokenized, detokenized in PINNED:
        rewritten = rewritten.replace(tokenized, detokenized)
    return rewritten == after

SNAPSHOT = """() => {
  const roots = ['.global-header', '#mobile-tabbar'];
  const snap = [];
  roots.forEach(sel => {
    const root = document.querySelector(sel);
    if (!root) return;
    const nodes = [root, ...root.querySelectorAll('*')];
    nodes.forEach((n, i) => {
      const cs = getComputedStyle(n);
      const props = {};
      for (let k = 0; k < cs.length; k += 1) {
        const name = cs[k];
        if (name.startsWith('--')) continue;   // the point of the change
        props[name] = cs.getPropertyValue(name);
      }
      // Pseudo-elements carry the underline and the current-slot marks.
      ['::before', '::after'].forEach(pe => {
        const p = getComputedStyle(n, pe);
        ['content', 'background-color', 'height', 'width', 'bottom', 'left',
         'right', 'top', 'border-radius', 'color', 'fill', 'stroke'].forEach(name => {
          props[pe + ' ' + name] = p.getPropertyValue(name);
        });
      });
      snap.push({key: sel + '[' + i + ']:' + n.tagName + '.' + (n.className.baseVal || n.className || ''), props});
    });
  });
  return snap;
}"""

SWAP = """(css) => {
  const link = document.querySelector('link[href*="public-navigation.css"]');
  if (!link) return 'no link';
  const style = document.createElement('style');
  style.id = 'detokenized-twin';
  style.textContent = css;
  link.after(style);
  link.disabled = true;
  return 'swapped';
}"""


def open_states(page):
    """Yield a label after putting the shell into each state that shows colour."""
    yield "closed"
    for label, trigger, panel in (
        ("switcher-open", "[data-platform-roomswitcher-trigger]", "[data-platform-roomswitcher-list]"),
        ("account-open", "[data-platform-account-trigger]", "[data-platform-account-menu]"),
    ):
        el = page.query_selector(trigger)
        if el and el.is_visible():
            el.click()
            page.wait_for_timeout(120)
            yield label
            page.keyboard.press("Escape")
            page.wait_for_timeout(80)
    opener = page.query_selector(".mobile-tabbar__item--more") or page.query_selector("[data-platform-menu-toggle]")
    if opener and opener.is_visible():
        opener.click()
        page.wait_for_timeout(150)
        yield "sheet-open"
        page.keyboard.press("Escape")
        page.wait_for_timeout(80)
    field = page.query_selector("#nav-search-input")
    if field and field.is_visible():
        page.fill("#nav-search-input", "resume")
        page.wait_for_timeout(180)
        yield "search-results"
        page.fill("#nav-search-input", "")


checked = 0
nodes_checked = 0
deltas = []
pinned_deltas = []
pinned_props = {}

with sync_playwright() as p:
    b = p.chromium.launch()
    for route in ROUTES:
        for base, auth in ((OUT, "signed-out"), (IN, "signed-in")):
            for w, h in VIEWPORTS:
                page = b.new_page(viewport={"width": w, "height": h})
                page.goto(base + route, wait_until="domcontentloaded", timeout=20000)
                # Swapping a stylesheet in a live DOM restarts transitions, so
                # a snapshot taken mid-transition reports the interpolated
                # value rather than the styled one. That is an artifact of the
                # method, not of the change: neutralise it so any remaining
                # delta is real.
                page.add_style_tag(content="*, *::before, *::after "
                                           "{ transition: none !important; "
                                           "animation: none !important; }")
                page.wait_for_timeout(400)
                for state in open_states(page):
                    before = page.evaluate(SNAPSHOT)
                    assert page.evaluate(SWAP, DETOKENIZED) == "swapped"
                    page.wait_for_timeout(60)
                    after = page.evaluate(SNAPSHOT)
                    # restore for the next state in this page
                    page.evaluate("""() => {
                      const s = document.getElementById('detokenized-twin');
                      if (s) s.remove();
                      const link = document.querySelector('link[href*="public-navigation.css"]');
                      if (link) link.disabled = false;
                    }""")
                    page.wait_for_timeout(60)
                    checked += 1
                    nodes_checked += len(before)
                    if len(before) != len(after):
                        deltas.append(f"{route} {auth} {w}x{h} {state}: node count "
                                      f"{len(before)} vs {len(after)}")
                        continue
                    for nb, na in zip(before, after):
                        for prop, value in nb["props"].items():
                            other = na["props"].get(prop)
                            if other == value:
                                continue
                            line = (f"{route} {auth} {w}x{h} {state} {nb['key']} "
                                    f"{prop}: {value!r} -> {other!r}")
                            if is_pinned_delta(route, value, other or ""):
                                pinned_deltas.append(line)
                                pinned_props[prop] = pinned_props.get(prop, 0) + 1
                            else:
                                deltas.append(line)
                page.close()
    b.close()

print(f"states compared      : {checked}")
print(f"node snapshots taken : {nodes_checked}")
print()
print("EXPECTED — the owner colour round's cross-route correction, which is")
print("the only place the family is not a pure alias:")
print(f"  deltas on {PINNED_ROUTE}, every one of them one of the six pinned")
print(f"  values                                     : {len(pinned_deltas)}")
for prop, count in sorted(pinned_props.items(), key=lambda kv: -kv[1]):
    print(f"      {prop:34} x{count}")
print()
print(f"UNEXPECTED — anything else                     : {len(deltas)}")
for d in deltas[:40]:
    print("  " + d)
sys.exit(1 if deltas else 0)
