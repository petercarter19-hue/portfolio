"""Headless screenshots of the v2 room for visual-parity review."""
import sys

from playwright.sync_api import sync_playwright

name = sys.argv[1]
out_dir = sys.argv[2]
port = sys.argv[3] if len(sys.argv) > 3 else "5000"
url = f"http://127.0.0.1:{port}/opportunity-slate"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1372, "height": 1146})
    page.goto(url, wait_until="networkidle")
    page.screenshot(path=f"{out_dir}/{name}-desktop-1372.png", full_page=True)
    narrow = browser.new_page(viewport={"width": 320, "height": 800})
    narrow.goto(url, wait_until="networkidle")
    narrow.screenshot(path=f"{out_dir}/{name}-narrow-320.png", full_page=True)
    browser.close()
print(f"captured {name}", flush=True)
