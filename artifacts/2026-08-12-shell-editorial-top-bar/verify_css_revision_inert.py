"""Account for every computed-style delta a public-navigation.css revision makes.

Originally written for the guard split, where the answer had to be zero. The
owner colour round of 2026-08-13 is not inert — it is meant to change things —
so the question changed from "did anything move?" to "did anything move that I
did not intend and cannot name?". Every delta is therefore classified against a
named intent, and the pass condition is that nothing is left unexplained.

    python verify_css_revision_inert.py <git-rev>

It snapshots every CSS property of every node under the shell with the CURRENT
stylesheet, swaps in the stylesheet as of <git-rev> IN THE SAME LIVE DOM,
snapshots again, and buckets every property whose computed value moved. Custom
properties are included, unlike the tokenization proof.

Scope note: the comparison is LIGHT-THEME ONLY, deliberately. The dark half of
the split cannot render — PEERSLATE_DARK_THEME_ENABLED is off, so no page
carries body[data-theme="dark"] — and the point of the split was to stop
guarding geometry that dark never redefines. What must be proven is that the
light render, which is what ships, did not move.
"""
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = "http://127.0.0.1:5057"
IN = "http://127.0.0.1:5058"
REV = sys.argv[1] if len(sys.argv) > 1 else "HEAD~1"
ROOT = Path(__file__).resolve().parents[2]

PREVIOUS = subprocess.run(
    ["git", "show", f"{REV}:static/css/public-navigation.css"],
    capture_output=True, cwd=ROOT, check=True,
).stdout.decode("utf-8")

VIEWPORTS = [(1440, 900), (1100, 800), (768, 900), (390, 844), (320, 700)]
ROUTES = ["/", "/experience", "/peerslate", "/interview-studio",
          "/opportunity-slate", "/petec/resume"]

# The properties the review named, on the elements the split touched. The
# parent .mobile-tabbar rule joined them in the 2026-08-13 round (finding F1),
# so its own layout and colour declarations are watched the same way.
WATCHED = {
    ".mobile-tabbar": ["display", "gap", "padding-top", "padding-right",
                       "padding-bottom", "padding-left", "overflow-x",
                       "background-color", "border-top-width", "border-top-color",
                       "box-shadow", "backdrop-filter", "position", "z-index"],
    ".mobile-tabbar__item": ["display", "min-height", "padding-top", "padding-right",
                             "padding-bottom", "padding-left", "font-size", "font-weight",
                             "flex-direction", "align-items", "justify-content", "gap",
                             "flex-grow", "flex-shrink", "flex-basis", "line-height",
                             "text-align", "color", "background-color"],
    ".mobile-tabbar__label": ["display", "max-width", "overflow-x", "overflow-y",
                              "text-overflow", "white-space", "color", "font-size"],
    ".mobile-tabbar__mark": ["width", "height", "fill", "stroke", "stroke-width",
                             "flex-shrink"],
}

# The six values the cross-route correction pins on a route without
# body.slate-light, as the engine serialises them.
PINNED = [
    ("rgb(6, 26, 58)", "rgb(22, 33, 58)"),
    ("rgb(217, 226, 236)", "rgb(229, 231, 236)"),
    ("rgb(73, 97, 122)", "rgb(92, 101, 117)"),
    ("rgb(244, 248, 253)", "rgb(246, 247, 249)"),
    ("rgba(11, 99, 229, 0.08)", "rgba(47, 111, 224, 0.09)"),
    ("rgba(6, 26, 58, 0.08) 0px 12px 30px 0px",
     "rgba(23, 33, 58, 0.07) 0px 10px 26px 0px"),
]


def pins_to(before, after):
    out = before
    for tokenized, detokenized in PINNED:
        out = out.replace(tokenized, detokenized)
    return out == after


def classify(route, markers, prop, before, after):
    """Name the intent behind a delta, or return None if nothing claims it.

    Order is deliberate: structural intents first, then the specific colour
    roles, then the cross-route palette pin, which would otherwise swallow
    everything on /experience.
    """
    if prop == "--ps-shell-shadow":
        return ("a. the new --ps-shell-shadow token exists in one variant only "
                "(the four shell panels' one elevation role)")
    # Checked before the structural intents because it is the most specific
    # test — an exact value-pair match — and because every descendant of the
    # brand row and the sheet inherits the pinned custom properties, which
    # would otherwise be attributed to whichever component they sit inside.
    if route == "/experience" and (
            pins_to(before, after) or prop.startswith("--ps-shell-")):
        return ("h. the cross-route palette pin — /experience is the one route "
                "without body.slate-light")
    if "platform-room-title" in markers:
        return ("c. the room title: a 1px divider and its padding, and it "
                "stands down below 34rem so the mark never has to")
    if "platform-brand" in markers:
        return ("b. THE PRIORITY — the logo is revealed at every width in "
                "every auth state")
    if "platform-roomswitcher__list" in markers and prop.endswith("background-color"):
        return "d. F2 — the switcher's current row takes the board's soft persistent fill"
    if "platform-menu-toggle" in markers and prop.endswith("background-color"):
        return "e. the Menu button joins the shell's one control ground (rail)"
    if "platform-menu__account" in markers and (
            prop.endswith("color") or prop == "-webkit-text-fill-color"):
        return "f. the More sheet's account rows take the same ink as every other menu row"
    if "platform-menu" in markers and prop == "box-shadow":
        return "g. the More sheet joins the panels' one elevation"
    return None

SNAPSHOT = """() => {
  const snap = [];
  ['.global-header', '#mobile-tabbar'].forEach(sel => {
    const root = document.querySelector(sel);
    if (!root) return;
    [root, ...root.querySelectorAll('*')].forEach((n, i) => {
      const cs = getComputedStyle(n);
      const props = {};
      for (let k = 0; k < cs.length; k += 1) {
        const name = cs[k];
        props[name] = cs.getPropertyValue(name);
      }
      ['::before', '::after'].forEach(pe => {
        const p = getComputedStyle(n, pe);
        ['content', 'background-color', 'height', 'width', 'bottom', 'left',
         'right', 'top', 'color', 'fill', 'stroke'].forEach(name => {
          props[pe + ' ' + name] = p.getPropertyValue(name);
        });
      });
      const cls = (n.className && n.className.baseVal !== undefined)
        ? n.className.baseVal : (n.className || '');
      // Every class on the node AND on its ancestors up to the shell root, so
      // a delta on an unclassed <img> or <span> can still be attributed to
      // the component it belongs to.
      const markers = [];
      for (let e = n; e && e !== document.body; e = e.parentElement) {
        const c = (e.className && e.className.baseVal !== undefined)
          ? e.className.baseVal : (e.className || '');
        String(c).split(/\\s+/).filter(Boolean).forEach(x => markers.push(x));
        if (e.id) markers.push('#' + e.id);
      }
      snap.push({key: sel + '[' + i + ']:' + n.tagName + '.' + cls, cls: String(cls),
                 markers, props});
    });
  });
  return snap;
}"""

SWAP = """(css) => {
  const link = document.querySelector('link[href*="public-navigation.css"]');
  if (!link) return 'no link';
  const style = document.createElement('style');
  style.id = 'previous-revision';
  style.textContent = css;
  link.after(style);
  link.disabled = true;
  return 'swapped';
}"""

RESTORE = """() => {
  const s = document.getElementById('previous-revision');
  if (s) s.remove();
  const link = document.querySelector('link[href*="public-navigation.css"]');
  if (link) link.disabled = false;
}"""

states = 0
nodes = 0
deltas = []
explained = {}
watched_seen = {k: 0 for k in WATCHED}
watched_confirmed = 0

with sync_playwright() as p:
    b = p.chromium.launch()
    for route in ROUTES:
        for base, auth in ((OUT, "signed-out"), (IN, "signed-in")):
            for w, h in VIEWPORTS:
                page = b.new_page(viewport={"width": w, "height": h})
                page.goto(base + route, wait_until="domcontentloaded", timeout=20000)
                page.add_style_tag(content="*, *::before, *::after "
                                           "{ transition: none !important; "
                                           "animation: none !important; }")
                page.wait_for_timeout(400)
                # The More sheet's ground, rule and elevation only apply to
                # .platform-menu:not([hidden]), so a closed-shell snapshot is
                # blind to them. Open it wherever it exists.
                for opener in (".mobile-tabbar__item--more",
                               "[data-platform-menu-toggle]"):
                    el = page.query_selector(opener)
                    if el and el.is_visible():
                        el.click()
                        page.wait_for_timeout(160)
                        break
                is_dark = page.evaluate(
                    "() => document.body.getAttribute('data-theme') === 'dark'")
                assert not is_dark, 'a page rendered dark; this proof is light only'
                before = page.evaluate(SNAPSHOT)
                assert page.evaluate(SWAP, PREVIOUS) == "swapped"
                page.wait_for_timeout(80)
                after = page.evaluate(SNAPSHOT)
                page.evaluate(RESTORE)
                states += 1
                nodes += len(before)
                if len(before) != len(after):
                    deltas.append(f"{route} {auth} {w}x{h}: node count "
                                  f"{len(before)} vs {len(after)}")
                    page.close()
                    continue
                for nb, na in zip(before, after):
                    props = set(nb["props"]) | set(na["props"])
                    for prop in props:
                        value = nb["props"].get(prop, "")
                        other = na["props"].get(prop, "")
                        if other == value:
                            continue
                        intent = classify(route, nb.get("markers", []), prop,
                                          value, other)
                        line = (f"{route} {auth} {w}x{h} {nb['key']} "
                                f"{prop}: {value!r} -> {other!r}")
                        if intent is None:
                            deltas.append(line)
                        else:
                            explained.setdefault(intent, []).append(line)
                    for cls, watch in WATCHED.items():
                        if cls.lstrip(".") in nb["cls"].split():
                            watched_seen[cls] += 1
                            for prop in watch:
                                if nb["props"].get(prop) == na["props"].get(prop):
                                    watched_confirmed += 1
                page.close()
    b.close()

print(f"comparing CURRENT stylesheet against {REV}")
print(f"states compared      : {states}   (light theme only, dark is flag-gated off)")
print(f"node snapshots taken : {nodes}")
print()
print("watched elements observed (the guard splits' own rules — these must not "
      "move):")
for cls, count in watched_seen.items():
    print(f"  {cls:26} {count} instances")
print(f"watched property comparisons confirmed identical: {watched_confirmed}")
print()
total = sum(len(v) for v in explained.values()) + len(deltas)
print(f"TOTAL DELTAS (custom properties INCLUDED): {total}")
print()
print("EXPLAINED — every one attributed to a named intent of this round:")
for intent in sorted(explained):
    rows = explained[intent]
    routes = sorted({r.split()[0] for r in rows})
    print(f"  {len(rows):>7}  {intent}")
    print(f"           routes: {', '.join(routes)}")
    print(f"           e.g. {rows[0]}")
print()
print(f"UNEXPLAINED — no intent claims these: {len(deltas)}")
for d in deltas[:40]:
    print("  " + d)
sys.exit(1 if deltas else 0)
