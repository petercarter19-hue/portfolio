"""PS-SHELL-001 interaction + keyboard verification.

Two servers: 5057 renders signed out, 5058 runs with the development
identity so the SERVER renders signed in. The shell's signed-in markup is
server-derived, so faking it in the DOM would not exercise the real render.
"""
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5057"        # signed out
BASE_IN = "http://127.0.0.1:5058"     # development identity, server-rendered signed in
ok = []
fail = []


def check(label, cond, detail=""):
    (ok if cond else fail).append(f"{label} {detail}".strip())


with sync_playwright() as p:
    b = p.chromium.launch()

    # --- medium width: the room switcher ---
    page = b.new_page(viewport={"width": 1100, "height": 800})
    page.goto(BASE_IN + "/interview-studio", wait_until="domcontentloaded")
    page.wait_for_timeout(400)
    trig = page.locator("[data-platform-roomswitcher-trigger]")
    lst = page.locator("[data-platform-roomswitcher-list]")
    switcher_name = page.evaluate(
        "() => document.querySelector('[data-platform-roomswitcher-trigger]')"
        ".textContent.replace(/\\s+/g,' ').trim()")
    check("switcher accessible name states the action and the current room",
          switcher_name == "Browse destinations, current: Interview Studio",
          switcher_name)
    check("switcher list starts hidden", lst.is_hidden())
    trig.click()
    page.wait_for_timeout(120)
    check("switcher opens", lst.is_visible())
    check("switcher aria-expanded true", trig.get_attribute("aria-expanded") == "true")
    check("switcher focus moves into list",
          page.evaluate("() => document.activeElement.closest('[data-platform-roomswitcher-list]') !== null"))
    check("switcher list has 4 destinations",
          page.locator("[data-platform-roomswitcher-list] a").count() == 4,
          str(page.locator("[data-platform-roomswitcher-list] a").count()))
    page.keyboard.press("Escape")
    page.wait_for_timeout(120)
    check("switcher closes on Escape", lst.is_hidden())
    check("switcher aria-expanded false", trig.get_attribute("aria-expanded") == "false")
    check("switcher focus returns to trigger",
          page.evaluate("() => document.activeElement === document.querySelector('[data-platform-roomswitcher-trigger]')"))
    trig.click()
    page.wait_for_timeout(100)
    page.mouse.click(600, 400)
    page.wait_for_timeout(120)
    check("switcher closes on outside click", lst.is_hidden())

    # --- account menu ---
    atrig = page.locator("[data-platform-account-trigger]")
    amenu = page.locator("[data-platform-account-menu]")
    check("account menu starts hidden", amenu.is_hidden())
    atrig.click()
    page.wait_for_timeout(120)
    check("account menu opens", amenu.is_visible())
    items = page.evaluate("() => Array.from(document.querySelectorAll('[data-platform-account-menu] a, [data-platform-account-menu] button')).map(e => e.textContent.trim())")
    check("account menu holds only My Slate + Sign out", items == ["My Slate", "Sign out"], str(items))
    check("account menu has no photo",
          page.locator("[data-platform-account] img").count() == 0)
    check("account initial is the display-name initial",
          page.locator(".platform-account__initial").inner_text().strip() == "L",
          page.locator(".platform-account__initial").inner_text().strip())
    page.keyboard.press("Escape")
    page.wait_for_timeout(120)
    check("account menu closes on Escape", amenu.is_hidden())
    check("account focus returns to trigger",
          page.evaluate("() => document.activeElement === document.querySelector('[data-platform-account-trigger]')"))

    # --- search still works (destination index unchanged) ---
    page.locator("#nav-search-input").fill("resume")
    page.wait_for_timeout(200)
    hits = page.evaluate("() => Array.from(document.querySelectorAll('#nav-search-results a')).map(a => a.textContent.trim())")
    check("search returns destinations", len(hits) > 0, str(hits[:3]))
    check("public search has no Ask-AI fallthrough",
          not any("Ask Pete" in h for h in hits))
    page.close()

    # --- phone: bottom bar + More sheet ---
    page = b.new_page(viewport={"width": 390, "height": 844})
    page.goto(BASE_IN + "/interview-studio", wait_until="domcontentloaded")
    page.wait_for_timeout(400)
    bar = page.locator("#mobile-tabbar")
    check("bottom bar visible on a route with no section tabs", bar.is_visible())
    slots = page.evaluate("() => Array.from(document.querySelectorAll('#mobile-tabbar > *')).map(e => e.textContent.trim())")
    check("four slots", slots == ["Pete's Slate", "Community", "Interview", "More"], str(slots))
    check("only one fixed bottom bar exists",
          page.evaluate("""() => Array.from(document.querySelectorAll('body *')).filter(e => {
              const s = getComputedStyle(e);
              return s.position === 'fixed' && s.bottom === '0px' && s.display !== 'none'
                     && e.getBoundingClientRect().width > window.innerWidth * 0.8
                     && (e.tagName === 'NAV');
          }).length === 1"""))
    check("Interview slot keeps the full name for assistive tech",
          page.evaluate("""() => { const a = Array.from(document.querySelectorAll('#mobile-tabbar a'))
              .find(x => x.textContent.trim() === 'Interview');
              return a && a.getAttribute('aria-label') === 'Interview Studio'; }"""))
    check("header Menu stands down where the global bar renders",
          page.locator("[data-platform-menu-toggle]").is_hidden())
    more = page.locator(".mobile-tabbar__item--more")
    sheet = page.locator("[data-platform-menu]")
    check("More sheet starts hidden", sheet.is_hidden())
    more.click()
    page.wait_for_timeout(150)
    check("More opens the sheet", sheet.is_visible())
    check("More aria-expanded true", more.get_attribute("aria-expanded") == "true")
    sheet_links = page.evaluate("() => Array.from(document.querySelectorAll('[data-platform-menu] a, [data-platform-menu] button[type=submit]')).map(e => e.textContent.trim())")
    check("sheet holds the overflow destinations", "Opportunity Slate" in sheet_links, str(sheet_links))
    page.keyboard.press("Escape")
    page.wait_for_timeout(150)
    check("More sheet closes on Escape", sheet.is_hidden())
    check("More focus returns to the More slot",
          page.evaluate("() => document.activeElement === document.querySelector('.mobile-tabbar__item--more')"))
    more.click()
    page.wait_for_timeout(150)
    signed_in_sheet = page.evaluate("() => Array.from(document.querySelectorAll('[data-platform-menu] a, [data-platform-menu] button[type=submit]')).map(e => e.textContent.trim())")
    check("signed-in sheet adds Settings and Sign out",
          "Settings" in signed_in_sheet and "Sign out" in signed_in_sheet, str(signed_in_sheet))
    check("no Help entry is offered", "Help" not in signed_in_sheet)
    page.close()

    # --- a route that owns its section tabs keeps its own bar ---
    page = b.new_page(viewport={"width": 390, "height": 844})
    page.goto(BASE + "/petec/my-story", wait_until="domcontentloaded")
    page.wait_for_timeout(400)
    slots = page.evaluate("() => Array.from(document.querySelectorAll('#mobile-tabbar > *')).map(e => e.textContent.trim())")
    check("page-owned bar keeps its section tabs",
          "More" not in slots and len(slots) > 0, str(slots))
    check("page-owned bar route keeps its header Menu",
          page.locator("[data-platform-menu-toggle]").is_visible())
    check("page-owned route did not gain has-global-tabbar",
          not page.evaluate("() => document.body.classList.contains('has-global-tabbar')"))
    page.close()

    # --- keyboard order + skip link ---
    page = b.new_page(viewport={"width": 1440, "height": 900})
    page.goto(BASE + "/interview-studio", wait_until="domcontentloaded")
    page.wait_for_timeout(400)
    page.keyboard.press("Tab")
    first = page.evaluate("() => document.activeElement.className + '|' + document.activeElement.textContent.trim().slice(0,30)")
    check("skip link is the first tab stop", "skip-link" in first, first)
    order = []
    for _ in range(9):
        page.keyboard.press("Tab")
        order.append(page.evaluate("() => (document.activeElement.getAttribute('aria-label') || document.activeElement.textContent.trim().slice(0,22))"))
    check("header tab order runs logo -> destinations -> search -> account",
          order[:7] == ["PeerSlate home", "Pete's Slate", "Community",
                        "Interview Studio", "Opportunity Slate",
                        "Search PeerSlate", "Sign In"],
          str(order))
    page.close()

    # --- console errors ---
    page = b.new_page(viewport={"width": 390, "height": 844})
    errs = []
    page.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.goto(BASE + "/", wait_until="domcontentloaded")
    page.wait_for_timeout(900)
    real = [e for e in errs if "favicon" not in e.lower() and "fonts.g" not in e.lower()
            and "net::ERR" not in e]
    check("no shell console errors", len(real) == 0, str(real[:3]))
    page.close()
    b.close()

print(f"PASS {len(ok)}  FAIL {len(fail)}")
for line in ok:
    print("  ok   " + line)
for line in fail:
    print("  FAIL " + line)
