"""Computed-style and geometry forensics for the v2 room.

Usage: measure_v2.py <selectors.json> [url]
  selectors.json: {"name": "css selector", ...}
Prints, per element: computed font (family/size/weight/line-height), colors
(color/background/border), and bounding rect (x, y, w, h) at a 1372px viewport.
Server must already be running (default url http://127.0.0.1:5000/opportunity-slate).
"""
import json
import sys

from playwright.sync_api import sync_playwright

selectors = json.load(open(sys.argv[1], encoding="utf-8"))
url = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:5000/opportunity-slate"

JS = """(sel) => {
  const el = document.querySelector(sel);
  if (!el) return null;
  const cs = getComputedStyle(el);
  const r = el.getBoundingClientRect();
  return {
    font: `${cs.fontFamily} | ${cs.fontSize} / ${cs.lineHeight} | w${cs.fontWeight}`,
    color: cs.color, background: cs.backgroundColor,
    border: `${cs.borderTopWidth} ${cs.borderTopColor} / r ${cs.borderRightWidth} ${cs.borderRightColor}`,
    padding: `${cs.paddingTop} ${cs.paddingRight} ${cs.paddingBottom} ${cs.paddingLeft}`,
    rect: {x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height)},
  };
}"""

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1372, "height": 1146})
    page.goto(url, wait_until="networkidle")
    out = {}
    for name, sel in selectors.items():
        out[name] = page.evaluate(JS, sel)
    browser.close()

print(json.dumps(out, indent=1))
