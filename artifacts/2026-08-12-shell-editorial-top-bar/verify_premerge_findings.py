"""PS-SHELL-001 pre-merge review round — the measurements it asked for.

F-A  every sheet row reachable at 390x400, 568x320, 640x360 and 320x256
F-B  a signed-in phone keeps destination navigation while scrolling down
F-D  bottom bar slot height, icon presence, and the current-slot treatment
F-F  active underline overhang and weight against the header rule
F-G  no overflow at 200% text
"""
import json

from playwright.sync_api import sync_playwright

OUT = "http://127.0.0.1:5057"   # signed out
IN = "http://127.0.0.1:5058"    # server-rendered signed in
out = {}

SHEET = """() => {
  const sheet = document.querySelector('[data-platform-menu]');
  const rows = Array.from(sheet.querySelectorAll('a[href], button[type=submit]'));
  const vh = window.innerHeight;
  const r = sheet.getBoundingClientRect();
  const visible = el => {
    const b = el.getBoundingClientRect();
    return b.bottom <= vh + 0.5 && b.top >= -0.5;
  };
  const atRest = rows.filter(el => !visible(el)).map(el => el.textContent.trim());
  // Real reachability: can each row be brought on screen, and does keyboard
  // focus bring it there by itself? A row that only scrolls the PAGE would
  // stay stuck, because the sheet is anchored to a sticky header.
  const unreachableByScroll = [];
  rows.forEach(el => {
    el.scrollIntoView({block: 'nearest'});
    if (!visible(el)) unreachableByScroll.push(el.textContent.trim());
  });
  sheet.scrollTop = 0;
  const unreachableByKeyboard = [];
  rows.forEach(el => {
    el.focus();
    if (!visible(el)) unreachableByKeyboard.push(el.textContent.trim());
  });
  sheet.scrollTop = 0;
  return {
    viewport: `${window.innerWidth}x${vh}`,
    sheetHeight: Math.round(r.height * 10) / 10,
    sheetBottom: Math.round(r.bottom * 10) / 10,
    maxHeight: getComputedStyle(sheet).maxHeight,
    overflowY: getComputedStyle(sheet).overflowY,
    scrollable: sheet.scrollHeight > sheet.clientHeight + 1,
    rows: rows.length,
    offscreenAtRest: atRest,
    UNREACHABLE_by_scrolling: unreachableByScroll,
    UNREACHABLE_by_keyboard: unreachableByKeyboard,
  };
}"""

with sync_playwright() as p:
    b = p.chromium.launch()

    # ---- F-A : the four viewports the review named ----
    for w, h in [(390, 400), (568, 320), (640, 360), (320, 256)]:
        page = b.new_page(viewport={"width": w, "height": h})
        page.goto(IN + "/opportunity-slate", wait_until="domcontentloaded")
        page.wait_for_timeout(500)
        opener = page.query_selector(".mobile-tabbar__item--more") \
            or page.query_selector("[data-platform-menu-toggle]")
        opener.click()
        page.wait_for_timeout(200)
        out[f"F-A {w}x{h}"] = page.evaluate(SHEET)
        page.close()

    # ---- F-B : navigation still present after scrolling down ----
    page = b.new_page(viewport={"width": 390, "height": 844})
    page.goto(IN + "/opportunity-slate", wait_until="domcontentloaded")
    page.wait_for_timeout(500)
    before = page.evaluate("""() => {
      const bar = document.getElementById('mobile-tabbar');
      const mt = document.querySelector('[data-platform-menu-toggle]');
      return {barHidden: bar.classList.contains('is-hidden'),
              menuToggle: getComputedStyle(mt).display};
    }""")
    page.evaluate("() => window.scrollTo(0, 900)")
    page.wait_for_timeout(500)
    after = page.evaluate("""() => {
      const bar = document.getElementById('mobile-tabbar');
      const mt = document.querySelector('[data-platform-menu-toggle]');
      const r = bar.getBoundingClientRect();
      return {barHidden: bar.classList.contains('is-hidden'),
              barOnScreen: r.bottom <= window.innerHeight + 1 && r.top < window.innerHeight,
              menuToggle: getComputedStyle(mt).display,
              scrollY: Math.round(window.scrollY)};
    }""")
    out["F-B 390x844 signed in"] = {"at top": before, "after 900px scroll": after}

    # ---- F-D : slot geometry ----
    out["F-D bar slots"] = page.evaluate("""() => {
      const items = Array.from(document.querySelectorAll('#mobile-tabbar > *'));
      return items.map(i => {
        const r = i.getBoundingClientRect();
        const svg = i.querySelector('svg');
        const label = i.querySelector('.mobile-tabbar__label');
        const cs = svg ? getComputedStyle(svg) : null;
        return {label: label ? label.textContent.trim() : i.textContent.trim(),
                h: Math.round(r.height * 10) / 10,
                w: Math.round(r.width * 10) / 10,
                hasIcon: !!svg,
                iconFill: cs ? cs.fill : null,
                current: i.getAttribute('aria-current') === 'page',
                color: getComputedStyle(i).color};
      });
    }""")
    page.close()

    # current-slot treatment, on a route that is in the bar
    page = b.new_page(viewport={"width": 390, "height": 844})
    page.goto(IN + "/interview-studio", wait_until="domcontentloaded")
    page.wait_for_timeout(500)
    out["F-D current slot"] = page.evaluate("""() => {
      const cur = document.querySelector('#mobile-tabbar [aria-current="page"]');
      if (!cur) return 'none';
      const svg = cur.querySelector('svg');
      return {label: cur.textContent.trim(),
              color: getComputedStyle(cur).color,
              iconFill: getComputedStyle(svg).fill,
              iconStroke: getComputedStyle(svg).stroke,
              indicator: getComputedStyle(cur, '::before').content,
              h: Math.round(cur.getBoundingClientRect().height * 10) / 10};
    }""")
    page.close()

    # ---- F-F : underline geometry ----
    page = b.new_page(viewport={"width": 1440, "height": 900})
    page.goto(OUT + "/interview-studio", wait_until="domcontentloaded")
    page.wait_for_timeout(500)
    out["F-F underline"] = page.evaluate("""() => {
      const header = document.querySelector('.global-header');
      const a = document.querySelector('.platform-nav__links a[aria-current="page"]');
      const label = document.createRange();
      label.selectNodeContents(a);
      const lr = label.getBoundingClientRect();
      const ar = a.getBoundingClientRect();
      const after = getComputedStyle(a, '::after');
      const hb = header.getBoundingClientRect().bottom;
      const ulBottom = ar.bottom - parseFloat(after.bottom);
      const h = parseFloat(after.height);
      return {headerHeight: Math.round(hb * 10) / 10,
              labelSpan: [Math.round(lr.x * 10) / 10, Math.round(lr.right * 10) / 10],
              underlineSpan: [Math.round(ar.x * 10) / 10, Math.round(ar.right * 10) / 10],
              overhangLeft: Math.round((lr.x - ar.x) * 10) / 10,
              overhangRight: Math.round((ar.right - lr.right) * 10) / 10,
              thickness: after.height,
              pctOfHeader: Math.round(h / hb * 1000) / 10,
              clearanceAboveRule: Math.round((hb - ulBottom) * 10) / 10};
    }""")
    page.close()

    # ---- F-G : 200% text ----
    for base, label in [(OUT, "signed out"), (IN, "signed in")]:
        page = b.new_page(viewport={"width": 1440, "height": 900})
        page.goto(base + "/interview-studio", wait_until="domcontentloaded")
        page.add_style_tag(content="html { font-size: 200%; }")
        page.wait_for_timeout(400)
        out[f"F-G 200% text {label}"] = page.evaluate("""() => {
          const links = Array.from(document.querySelectorAll('.platform-nav__links a'));
          const last = links[links.length - 1].getBoundingClientRect();
          const header = document.querySelector('.global-header').getBoundingClientRect();
          return {docScrollWidth: document.documentElement.scrollWidth,
                  innerWidth: window.innerWidth,
                  overflowPx: document.documentElement.scrollWidth - window.innerWidth,
                  lastDestination: [Math.round(last.x), Math.round(last.right)],
                  rowWrapped: links.length > 1 &&
                      links[links.length - 1].getBoundingClientRect().top >
                      links[0].getBoundingClientRect().top + 2,
                  headerHeight: Math.round(header.height)};
        }""")
        page.close()
    b.close()

print(json.dumps(out, indent=1))
