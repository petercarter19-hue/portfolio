"""PS-SHELL-001 — does every shell surface paint the token it says it does?

The owner colour round asks for one semantic role, one value, everywhere the
shell renders. Two things can break that and only one of them is visible in a
screenshot:

  1. the same role written with two different tokens, and
  2. the shell declaring a token that a PAGE rule then outranks, so the shell
     only appears to own the value because the two happen to agree.

(2) is the dangerous one. It hid a real defect: the idle destination ink was
coming from style.css's `body[data-theme="modern-blue"] .platform-nav__links a`
at (0,2,2), not from the shell's own (0,2,1) rule, and the two agreed on every
route except /experience — the one route base.html does not give
body.slate-light.

This script measures BOTH. For every rendered shell surface it compares the
painted value against the --ps-shell-* token that surface's declaration names,
and it reports every cross-route divergence of every painted value.

Two servers, pinned to this worktree, token-checked before measuring:

    python -c "from app import app; app.run(port=5057, use_reloader=False)"
    python -c "from app import app; \
        app.config['PEERSLATE_ALLOW_DEV_IDENTITY']=True; \
        app.config['PEERSLATE_DEV_USER_KEY']='shell-colour'; \
        app.run(port=5058, use_reloader=False)"
    python artifacts/2026-08-12-shell-editorial-top-bar/verify_shell_colour_consistency.py
"""
import collections
import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = {"signedout": "http://127.0.0.1:5057", "signedin": "http://127.0.0.1:5058"}
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent

ROUTES = ["/", "/experience", "/peerslate", "/interview-studio",
          "/opportunity-slate", "/the-slate", "/petec/resume", "/petec/my-story"]
VIEWPORTS = [1440, 1100, 900, 390]

# selector, property, the --ps-shell-* token the declaration names.
#
# Measured in TWO passes on the same page: once with the shell closed and at
# rest, once with every panel open. A surface is scored from the first pass in
# which it renders, so the search field is judged at rest (where it sits on the
# rail) rather than focused (where it deliberately lifts to the surface colour
# and takes an accent border) — that state change is the design, and scoring it
# against the resting token would manufacture 60 false mismatches.
SURFACES = [
    (".global-header", "background-color", "--ps-shell-surface"),
    (".global-header", "border-bottom-color", "--ps-shell-border"),
    (".global-header .platform-room-title", "color", "--ps-shell-text"),
    (".global-header .platform-nav__links a:not([aria-current])", "color", "--ps-shell-text"),
    ('.global-header .platform-nav__links a[aria-current="page"]', "color", "--ps-shell-accent-room"),
    (".global-header .platform-roomswitcher__trigger", "background-color", "--ps-shell-rail"),
    (".global-header .platform-roomswitcher__trigger", "color", "--ps-shell-text"),
    (".global-header .platform-roomswitcher__list", "background-color", "--ps-shell-surface"),
    (".global-header .platform-roomswitcher__list", "border-top-color", "--ps-shell-border"),
    (".global-header .platform-roomswitcher__list a:not([aria-current])", "color", "--ps-shell-text"),
    ('.global-header .platform-roomswitcher__list a[aria-current="page"]', "color", "--ps-shell-accent-room"),
    ('.global-header .platform-roomswitcher__list a[aria-current="page"]', "background-color", "--ps-shell-accent-soft"),
    (".global-header .platform-roomswitcher__sub", "color", "--ps-shell-text-muted"),
    (".global-header .platform-account__trigger", "background-color", "--ps-shell-rail"),
    (".global-header .platform-account__trigger", "color", "--ps-shell-text"),
    (".global-header .platform-account__trigger", "border-top-color", "--ps-shell-border"),
    (".global-header .platform-account__menu", "background-color", "--ps-shell-surface"),
    (".global-header .platform-account__menu", "border-top-color", "--ps-shell-border"),
    (".global-header .platform-account__item", "color", "--ps-shell-text"),
    (".global-header .nav-search__input", "background-color", "--ps-shell-rail"),
    (".global-header .nav-search__input", "color", "--ps-shell-text"),
    (".global-header .nav-search__input", "border-top-color", "--ps-shell-border"),
    (".global-header .nav-search__icon", "stroke", "--ps-shell-text-muted"),
    (".global-header .nav-search__results", "background-color", "--ps-shell-surface"),
    (".global-header .nav-search__results", "border-top-color", "--ps-shell-border"),
    (".platform-menu-toggle", "background-color", "--ps-shell-rail"),
    (".platform-menu-toggle", "color", "--ps-shell-text"),
    (".platform-menu-toggle", "border-top-color", "--ps-shell-border"),
    (".platform-menu", "background-color", "--ps-shell-surface"),
    (".platform-menu", "border-top-color", "--ps-shell-border"),
    (".platform-menu__links a:not([aria-current])", "color", "--ps-shell-text"),
    ('.platform-menu__links a[aria-current="page"]', "color", "--ps-shell-accent-room"),
    ('.platform-menu__links a[aria-current="page"]', "background-color", "--ps-shell-accent-soft"),
    (".platform-menu__account-item", "color", "--ps-shell-text"),
    ("#mobile-tabbar", "background-color", "--ps-shell-surface"),
    ("#mobile-tabbar", "border-top-color", "--ps-shell-border"),
    ('.mobile-tabbar__item:not([aria-current])', "color", "--ps-shell-text-muted"),
    ('.mobile-tabbar__item[aria-current="page"]', "color", "--ps-shell-accent-room"),
]

# Page treatments that are LOCKED by their own package and are meant to win.
KNOWN_PAGE_OVERRIDES = {
    # Interview Studio's accepted authenticated warm shell.
    ("/interview-studio", ".global-header", "background-color"),
    ("/interview-studio", ".global-header", "border-bottom-color"),
    ("/interview-studio", ".global-header .platform-nav__links a:not([aria-current])", "color"),
    ("/interview-studio", '.global-header .platform-nav__links a[aria-current="page"]', "color"),
    ("/interview-studio", ".global-header .nav-search__input", "background-color"),
    ("/interview-studio", ".global-header .nav-search__input", "border-top-color"),
}

PROBE = """([surfaces, tokens]) => {
  const header = document.querySelector('.global-header');
  if (!header) return null;
  const hs = getComputedStyle(header);
  const tokenValues = {};
  tokens.forEach(t => { tokenValues[t] = hs.getPropertyValue(t).trim(); });

  // Normalise a token's declared value into the same serialisation the
  // painted value uses, by letting the engine parse it.
  const probe = document.createElement('span');
  probe.style.display = 'none';
  document.body.appendChild(probe);
  const normalise = raw => {
    if (!raw) return null;
    probe.style.color = '';
    probe.style.color = raw;
    const v = getComputedStyle(probe).color;
    return (v === 'rgb(0, 0, 0)' && !/^(#000|black|rgb\\(0, ?0, ?0\\))$/i.test(raw.trim())) ? null : v;
  };
  const normalised = {};
  tokens.forEach(t => { normalised[t] = normalise(tokenValues[t]); });

  const rendered = e => {
    if (!e) return false;
    const s = getComputedStyle(e);
    if (s.display === 'none' || s.visibility === 'hidden') return false;
    const r = e.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };

  // The one bottom bar is page-owned wherever a route supplies section tabs,
  // and this package deliberately leaves that render exactly as released. Only
  // score it where it is carrying the SHELL's global structure.
  const globalBar = document.body.classList.contains('has-global-tabbar');

  const rows = [];
  surfaces.forEach(([sel, prop, token]) => {
    if (!globalBar && (sel === '#mobile-tabbar' || sel.startsWith('.mobile-tabbar__'))) {
      rows.push({sel, prop, token, state: 'page-owned-bar'});
      return;
    }
    const el = document.querySelector(sel);
    if (!rendered(el)) { rows.push({sel, prop, token, state: 'not-rendered'}); return; }
    const painted = getComputedStyle(el).getPropertyValue(prop).trim();
    const expected = normalised[token];
    rows.push({sel, prop, token, painted, expected,
               state: expected === null ? 'token-unparsed'
                    : (painted === expected ? 'match' : 'MISMATCH')});
  });
  probe.remove();
  return {rows, tokenValues, bodyClass: document.body.className.trim()};
}"""


def check_served_token():
    disk = hashlib.sha256(
        (ROOT / "static/css/public-navigation.css").read_bytes()).hexdigest()[:12]
    for name, base in BASE.items():
        html = urllib.request.urlopen(base + "/interview-studio", timeout=15).read().decode("utf-8")
        served = re.search(r"public-navigation\.css\?v=([0-9a-f]+)", html)
        served = served.group(1) if served else None
        if served != disk:
            sys.exit(f"{name} at {base} serves {served}, disk is {disk} — "
                     "a mispointed server would invalidate every number below")
    print(f"both servers pinned to this worktree; public-navigation.css = {disk}\n")


def open_everything(page):
    for trig in ("[data-platform-roomswitcher-trigger]",
                 "[data-platform-account-trigger]",
                 "[data-platform-menu-toggle]"):
        try:
            el = page.query_selector(trig)
            if el and el.is_visible():
                el.click()
                page.wait_for_timeout(110)
        except Exception:
            pass
    try:
        box = page.query_selector(".global-header .nav-search__input")
        if box and box.is_visible():
            box.click()
            box.type("s")
            page.wait_for_timeout(180)
    except Exception:
        pass


def merge(closed, opened):
    """Prefer the resting reading; fall back to the opened one."""
    if closed is None:
        return opened
    if opened is None:
        return closed
    by_key = {(r["sel"], r["prop"]): r for r in opened["rows"]}
    rows = []
    for row in closed["rows"]:
        if row["state"] in ("not-rendered",):
            alt = by_key.get((row["sel"], row["prop"]))
            if alt is not None:
                rows.append(dict(alt, pass_="opened"))
                continue
        rows.append(dict(row, pass_="closed"))
    closed["rows"] = rows
    return closed


def main():
    check_served_token()
    tokens = sorted({t for _, _, t in SURFACES})
    results = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for auth, base in BASE.items():
            for route in ROUTES:
                for width in VIEWPORTS:
                    page = browser.new_page(viewport={"width": width, "height": 900})
                    page.goto(base + route, wait_until="domcontentloaded", timeout=20000)
                    page.wait_for_timeout(240)
                    closed = page.evaluate(PROBE, [SURFACES, tokens])
                    open_everything(page)
                    opened = page.evaluate(PROBE, [SURFACES, tokens])
                    results[f"{auth}|{route}|{width}"] = merge(closed, opened)
                    page.close()
        browser.close()

    # A compact record rather than half a megabyte of repeated rows: the token
    # values each route resolved, every value each surface painted and where,
    # and any mismatch in full.
    record = {"states": sorted(results), "tokens_by_route": {},
              "surface_values": {}, "mismatches": []}
    for key, data in results.items():
        if not data:
            continue
        route = key.split("|")[1]
        record["tokens_by_route"].setdefault(route, data["tokenValues"])
        for row in data["rows"]:
            if row["state"] in ("not-rendered", "page-owned-bar"):
                continue
            slot = record["surface_values"].setdefault(
                f'{row["sel"]} {{{row["prop"]}}}', {})
            slot.setdefault(row["painted"], []).append(key)
            if row["state"] != "match":
                record["mismatches"].append(dict(row, state_key=key))
    for slot in record["surface_values"].values():
        for value, keys in slot.items():
            slot[value] = sorted({k.split("|")[1] for k in keys})
    (OUT / "shell_colour_consistency.json").write_text(
        json.dumps(record, indent=1), encoding="utf-8")

    checked = matched = 0
    mismatches = collections.defaultdict(list)
    for key, data in results.items():
        if not data:
            continue
        route = key.split("|")[1]
        for row in data["rows"]:
            if row["state"] in ("not-rendered", "page-owned-bar"):
                continue
            checked += 1
            if row["state"] == "match":
                matched += 1
            else:
                mismatches[(route, row["sel"], row["prop"])].append(
                    (key, row.get("painted"), row.get("expected")))

    print("=== 1. DOES EACH SURFACE PAINT THE TOKEN IT DECLARES? ===")
    print(f"rendered surface checks: {checked}    matching: {matched}    "
          f"mismatching: {checked - matched}")
    expected_over = unexpected = 0
    for (route, sel, prop), rows in sorted(mismatches.items()):
        known = (route, sel, prop) in KNOWN_PAGE_OVERRIDES
        tag = "known locked page override" if known else "UNEXPECTED"
        if known:
            expected_over += len(rows)
        else:
            unexpected += len(rows)
        print(f"\n  [{tag}] {route}  {sel} {{{prop}}}")
        for key, painted, expected in rows[:2]:
            print(f"      painted {painted}   token says {expected}   ({key})")
    print(f"\n  mismatches attributable to a locked page treatment: {expected_over}")
    print(f"  mismatches NOT attributable to one:                  {unexpected}")

    print("\n=== 2. DOES EVERY SURFACE PAINT ONE VALUE ON EVERY ROUTE? ===")
    per_surface = collections.defaultdict(lambda: collections.defaultdict(set))
    for key, data in results.items():
        if not data:
            continue
        auth, route, width = key.split("|")
        for row in data["rows"]:
            if row["state"] in ("not-rendered", "page-owned-bar"):
                continue
            per_surface[(row["sel"], row["prop"], width)][row["painted"]].add(route)
    stable = drifting = 0
    for (sel, prop, width), vals in sorted(per_surface.items()):
        if len(vals) == 1:
            stable += 1
            continue
        drifting += 1
        print(f"\n  {sel} {{{prop}}} at {width}px: {len(vals)} values")
        for val, routes in vals.items():
            print(f"      {val:34} {sorted(routes)}")
    print(f"\n  surface x width combinations with ONE value on every route: {stable}")
    print(f"  combinations that still differ by route:                    {drifting}")

    print(f"\nwrote {OUT / 'shell_colour_consistency.json'}")


if __name__ == "__main__":
    main()
