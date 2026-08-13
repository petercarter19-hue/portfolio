"""PS-SHELL-001 headless verification of the Editorial Top Bar."""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5057"
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
OUT.mkdir(parents=True, exist_ok=True)

VIEWPORTS = [
    ("1440x900", 1440, 900),
    ("1280x800", 1280, 800),
    ("1100x800", 1100, 800),
    ("1024x800", 1024, 800),
    ("768x900", 768, 900),
    ("743x900", 743, 900),
    ("390x844", 390, 844),
    ("320x700", 320, 700),
    ("720x450", 720, 450),
]

ROUTES = ["/", "/experience", "/peerslate", "/interview-studio", "/opportunity-slate", "/petec/resume"]

PROBE = """
() => {
  const header = document.querySelector('.global-header');
  const inner = document.querySelector('.platform-nav__inner');
  const links = document.querySelector('.platform-nav__links');
  const sw = document.querySelector('.platform-roomswitcher');
  const search = document.querySelector('.platform-actions .nav-search');
  const input = document.querySelector('.platform-actions .nav-search__input');
  const account = document.querySelector('.platform-account');
  const signin = document.querySelector('[data-ps-auth-control="signed_out"]');
  const menuToggle = document.querySelector('[data-platform-menu-toggle]');
  const bar = document.getElementById('mobile-tabbar');
  const logo = document.querySelector('.platform-brand__logo');
  const title = document.querySelector('.platform-room-title');
  const active = document.querySelector('.platform-nav__links a[aria-current="page"]');
  const cs = e => e ? getComputedStyle(e) : null;
  const vis = e => { if (!e) return 'absent'; const s = getComputedStyle(e);
    return (s.display === 'none' || s.visibility === 'hidden' || e.hidden) ? 'hidden' : 'shown'; };
  const box = e => { if (!e) return null; const r = e.getBoundingClientRect();
    return [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)]; };
  let underline = null;
  if (active) {
    const a = getComputedStyle(active, '::after');
    underline = { height: a.height, background: a.backgroundColor, bottom: a.bottom };
  }
  return {
    docScrollW: document.documentElement.scrollWidth,
    innerW: window.innerWidth,
    overflow: document.documentElement.scrollWidth > window.innerWidth + 1,
    headerH: header ? Math.round(header.getBoundingClientRect().height) : null,
    headerBg: cs(header) ? cs(header).backgroundColor : null,
    headerBorder: cs(header) ? cs(header).borderBottomWidth + ' ' + cs(header).borderBottomColor : null,
    headerShadow: cs(header) ? cs(header).boxShadow : null,
    innerGrid: cs(inner) ? cs(inner).gridTemplateAreas : null,
    links: vis(links),
    switcher: vis(sw),
    search: vis(search),
    inputW: input ? Math.round(input.getBoundingClientRect().width) : null,
    account: vis(account),
    signin: vis(signin),
    menuToggle: vis(menuToggle),
    tabbar: vis(bar),
    tabbarSlots: bar ? Array.from(bar.children).map(c => c.textContent.trim()) : [],
    hasGlobalTabbar: document.body.classList.contains('has-global-tabbar'),
    hasMobileTabbar: document.body.classList.contains('has-mobile-tabbar'),
    bodyPadBottom: getComputedStyle(document.body).paddingBottom,
    logo: vis(logo),
    roomTitle: vis(title),
    activeLabel: active ? active.textContent.trim() : null,
    activeColor: active ? getComputedStyle(active).color : null,
    activeWeight: active ? getComputedStyle(active).fontWeight : null,
    underline: underline,
    logoBox: box(logo),
    accountBox: box(account),
  };
}
"""

SIGN_IN = """
() => {
  document.querySelectorAll('[data-ps-auth-control]').forEach(el => {
    el.hidden = el.getAttribute('data-ps-auth-control') !== 'authenticated';
  });
  const c = document.querySelector('[data-ps-auth-controls]');
  if (c) c.setAttribute('data-ps-auth-state', 'authenticated');
}
"""

results = {}
with sync_playwright() as p:
    browser = p.chromium.launch()
    for route in ROUTES:
        for name, w, h in VIEWPORTS:
            page = browser.new_page(viewport={"width": w, "height": h})
            page.goto(BASE + route, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(500)
            key = f"{route} @ {name}"
            results[key] = {"out": page.evaluate(PROBE)}
            page.evaluate(SIGN_IN)
            page.wait_for_timeout(120)
            results[key]["in"] = page.evaluate(PROBE)
            page.close()
    browser.close()

(OUT / "probe.json").write_text(json.dumps(results, indent=1), encoding="utf-8")

print(f"{'state':<44} {'ovf':<4} {'hdr':<4} {'lnk':<7} {'sw':<7} {'srch':<7} {'acct':<7} {'menu':<7} {'bar':<7} {'logo':<7} {'title'}")
for key, both in results.items():
    for mode in ("out", "in"):
        r = both[mode]
        print(f"{key + ' [' + mode + ']':<44} {str(r['overflow']):<4} {str(r['headerH']):<4} "
              f"{r['links']:<7} {r['switcher']:<7} {r['search']:<7} {r['account']:<7} "
              f"{r['menuToggle']:<7} {r['tabbar']:<7} {r['logo']:<7} {r['roomTitle']}")
