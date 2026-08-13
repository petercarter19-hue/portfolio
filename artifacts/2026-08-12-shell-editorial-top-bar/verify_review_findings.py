"""PS-SHELL-001 fix round — the specific measurements the review asked for.

F1  bottom bar must not overflow 320px, and every slot must be on screen
F2  Sign out must match its neighbours in both menus below 544px
F3  no global bar for a signed-out visitor, and the hamburger stays
F4  active underline clearance above the header rule
F5  focus ring wraps the label and stays inside the header
F6  exactly one visible search field with the More sheet open
F8  released destination type restored
"""
import json
import sys

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5057"        # signed out
BASE_IN = "http://127.0.0.1:5058"     # dev identity, so the SERVER renders signed in
out = {}


def run():
    with sync_playwright() as p:
        b = p.chromium.launch()

        # ---- F3 / F1 : signed out, then signed in, at 320 and 390 ----
        for width in (320, 390):
            page = b.new_page(viewport={"width": width, "height": 720})
            page.goto(BASE + "/opportunity-slate", wait_until="domcontentloaded")
            page.wait_for_timeout(500)
            out[f"F3 signed-out @{width}"] = page.evaluate("""() => {
              const bar = document.getElementById('mobile-tabbar');
              const mt = document.querySelector('[data-platform-menu-toggle]');
              return {
                barVisible: bar ? !bar.hidden && getComputedStyle(bar).display !== 'none' : false,
                globalSourcePresent: !!document.querySelector('[data-global-tabsource]'),
                hasGlobalTabbar: document.body.classList.contains('has-global-tabbar'),
                menuToggle: mt ? getComputedStyle(mt).display : 'absent',
                bodyPadBottom: getComputedStyle(document.body).paddingBottom,
              };
            }""")
            page.close()

        # Signed in requires the server-rendered marker, so drive the dev
        # identity through the real header rather than faking the DOM.
        for width in (320, 390):
            page = b.new_page(viewport={"width": width, "height": 720})
            page.goto(BASE_IN + "/opportunity-slate", wait_until="domcontentloaded")
            page.wait_for_timeout(500)
            out[f"F1 signed-in @{width}"] = page.evaluate("""() => {
              const bar = document.getElementById('mobile-tabbar');
              if (!bar) return {bar: 'absent'};
              const items = Array.from(bar.children);
              return {
                clientWidth: bar.clientWidth,
                scrollWidth: bar.scrollWidth,
                overflows: bar.scrollWidth > bar.clientWidth,
                viewport: window.innerWidth,
                slots: items.map(i => {
                  const r = i.getBoundingClientRect();
                  return {label: i.textContent.trim(),
                          x: Math.round(r.x * 10) / 10,
                          right: Math.round(r.right * 10) / 10,
                          w: Math.round(r.width * 10) / 10,
                          h: Math.round(r.height * 10) / 10,
                          offScreen: r.right > window.innerWidth + 0.5 || r.x < -0.5};
                }),
                menuToggle: (() => { const m = document.querySelector('[data-platform-menu-toggle]');
                                     return m ? getComputedStyle(m).display : 'absent'; })(),
                barBg: getComputedStyle(bar).backgroundColor,
                barFilter: getComputedStyle(bar).backdropFilter,
                barShadow: getComputedStyle(bar).boxShadow,
              };
            }""")

            # ---- F2 : Sign out vs its neighbours, both menus ----
            out[f"F2 @{width}"] = page.evaluate("""() => {
              const m = (sel) => { const e = document.querySelector(sel); if (!e) return null;
                const s = getComputedStyle(e); const r = e.getBoundingClientRect();
                return {text: e.textContent.trim(), fontSize: s.fontSize,
                        boxH: Math.round(r.height * 100) / 100}; };
              document.querySelector('[data-platform-account]').hidden = false;
              document.querySelector('[data-platform-account-menu]').hidden = false;
              document.querySelector('.platform-menu__account').hidden = false;
              document.querySelector('[data-platform-menu]').hidden = false;
              return {
                accountMySlate: m('[data-platform-account-menu] .platform-account__item'),
                accountSignOut: m('[data-platform-account-menu] .nav-sign-out__btn'),
                sheetMySlate: m('.platform-menu__account .platform-menu__account-item'),
                sheetSignOut: m('.platform-menu__account .nav-sign-out__btn'),
              };
            }""")

            # ---- F6 : how many search fields are visible with the sheet open ----
            out[f"F6 @{width}"] = page.evaluate("""() => {
              const vis = e => { const s = getComputedStyle(e);
                return s.display !== 'none' && s.visibility !== 'hidden' && !e.hidden
                       && e.getBoundingClientRect().width > 0; };
              const inputs = Array.from(document.querySelectorAll('.nav-search__input'));
              return {sheetOpen: !document.querySelector('[data-platform-menu]').hidden,
                      totalSearchInputs: inputs.length,
                      visibleSearchInputs: inputs.filter(vis).map(i => i.id)};
            }""")
            page.close()

        # ---- F4 / F5 / F8 : desktop destination row ----
        page = b.new_page(viewport={"width": 1440, "height": 900})
        page.goto(BASE + "/interview-studio", wait_until="domcontentloaded")
        page.wait_for_timeout(500)
        out["F4/F8 desktop"] = page.evaluate("""() => {
          const header = document.querySelector('.global-header');
          const active = document.querySelector('.platform-nav__links a[aria-current="page"]');
          const idle = document.querySelector('.platform-nav__links a:not([aria-current])');
          const hr = header.getBoundingClientRect();
          const ar = active.getBoundingClientRect();
          const after = getComputedStyle(active, '::after');
          const underlineBottom = ar.bottom - parseFloat(after.bottom);
          return {
            headerBottom: Math.round(hr.bottom * 10) / 10,
            linkBox: [Math.round(ar.top * 10) / 10, Math.round(ar.height * 10) / 10],
            underlineHeight: after.height,
            underlineBottomEdge: Math.round(underlineBottom * 10) / 10,
            clearanceAboveRule: Math.round((hr.bottom - underlineBottom) * 10) / 10,
            activeFontSize: getComputedStyle(active).fontSize,
            activeWeight: getComputedStyle(active).fontWeight,
            idleFontSize: getComputedStyle(idle).fontSize,
            idleWeight: getComputedStyle(idle).fontWeight,
            activeColor: getComputedStyle(active).color,
            letterSpacing: getComputedStyle(idle).letterSpacing,
          };
        }""")
        page.keyboard.press("Tab")
        page.keyboard.press("Tab")
        page.keyboard.press("Tab")
        out["F5 focus"] = page.evaluate("""() => {
          const el = document.activeElement;
          const s = getComputedStyle(el);
          const r = el.getBoundingClientRect();
          const hr = document.querySelector('.global-header').getBoundingClientRect();
          const off = parseFloat(s.outlineOffset) || 0;
          const w = parseFloat(s.outlineWidth) || 0;
          return {
            focused: el.textContent.trim(),
            outline: s.outline,
            outlineOffset: s.outlineOffset,
            padding: s.padding,
            boxH: Math.round(r.height * 10) / 10,
            ringTop: Math.round((r.top - off - w) * 10) / 10,
            ringBottom: Math.round((r.bottom + off + w) * 10) / 10,
            ringInsideHeader: (r.top - off - w) >= hr.top - 0.5
                              && (r.bottom + off + w) <= hr.bottom + 0.5,
            ringClearsGlyphsBy: Math.round((parseFloat(s.paddingLeft) + off) * 10) / 10,
          };
        }""")
        page.screenshot(path=str(sys.argv[1] + "/fix_1440_navfocus.png"),
                        clip={"x": 0, "y": 0, "width": 800, "height": 90})
        page.close()
        b.close()


run()
print(json.dumps(out, indent=1))
