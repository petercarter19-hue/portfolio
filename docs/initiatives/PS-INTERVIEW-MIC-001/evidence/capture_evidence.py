"""Render the real /interview-studio page in headless Chrome with a controllable
SpeechRecognition stub, so the shipped state machine paints its real states.

Only the recogniser is stubbed (a real microphone grant is impossible headless).
Template, CSS, JS and state machine are the shipped code.

Chrome enforces a 500 CSS px minimum window width, so narrow viewports are
rendered inside an exactly-390px iframe and cropped, which gives the inner
document a genuine 390px layout viewport for media queries.
"""
import http.server
import functools
import subprocess
import sys
import threading
import urllib.request
from pathlib import Path

from PIL import Image

APP = "http://127.0.0.1:5077"
SERVE_PORT = 5078
OUT = Path(sys.argv[1]).resolve()
WORK = Path(__file__).resolve().parent / "pages"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SCALE = 2

OUT.mkdir(parents=True, exist_ok=True)
WORK.mkdir(parents=True, exist_ok=True)

html = urllib.request.urlopen(APP + "/interview-studio?mode=me").read().decode("utf-8")

STUB = """
<base href="%s/">
<script>
(function () {
  function Fake() { window.__last = this; }
  Fake.prototype.start = function () {};
  Fake.prototype.stop = function () { var s = this; setTimeout(function () { s.onend && s.onend(); }, 0); };
  window.SpeechRecognition = Fake;
  window.webkitSpeechRecognition = Fake;
  window.__emit = function (chunks) {
    var r = chunks.map(function (c) { var x = [{ transcript: c[0] }]; x.isFinal = c[1]; return x; });
    window.__last.onresult({ resultIndex: 0, results: r });
  };
  window.__err = function (code) { window.__last.onerror({ error: code }); };
})();
</script>
""" % APP

LISTENING = """
  answer.value = 'I disagreed with my manager about the ship date for a compliance release.';
  answer.dispatchEvent(new Event('input', { bubbles: true }));
  mic.click();
  window.__emit([['I raised the risk in our planning review and proposed', false]]);
  setInterval(function () { window.__emit([['I raised the risk in our planning review and proposed', false]]); }, 1000);
"""

DENIED = """
  answer.value = 'My typed answer stays exactly where it was.';
  answer.dispatchEvent(new Event('input', { bubbles: true }));
  mic.click();
  window.__err('not-allowed');
"""


def build_page(name, theme, driver):
    body = """
<script>
window.addEventListener('load', function () {
  setTimeout(function () {
    document.body.setAttribute('data-theme', '%s');
    var answer = document.querySelector('[data-is-answer]');
    var mic = document.querySelector('[data-is-mic="answer"]');
    %s
  }, 60);
});
</script>
""" % (theme, driver)
    page = html.replace("<head>", "<head>" + STUB, 1)
    page = page.replace("</body>", body + "</body>", 1)
    path = WORK / ("page_%s.html" % name)
    path.write_text(page, encoding="utf-8")
    return path.name


def build_frame(name, inner, width, height):
    frame = (
        '<body style="margin:0;background:#fff">'
        '<iframe src="%s" width="%d" height="%d" '
        'style="border:0;display:block"></iframe></body>' % (inner, width, height)
    )
    path = WORK / ("frame_%s.html" % name)
    path.write_text(frame, encoding="utf-8")
    return path.name


def chrome_shot(url, png, win_w, win_h):
    subprocess.run([
        CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
        "--force-device-scale-factor=%d" % SCALE,
        "--virtual-time-budget=7000",
        "--window-size=%d,%d" % (win_w, win_h),
        "--screenshot=%s" % png, url,
    ], check=True, capture_output=True)


def shoot(name, theme, driver, width, height):
    inner = build_page(name, theme, driver)
    png = OUT / (name + ".png")
    if width >= 520:
        chrome_shot("http://127.0.0.1:%d/%s" % (SERVE_PORT, inner), png, width, height)
    else:
        frame = build_frame(name, inner, width, height)
        chrome_shot("http://127.0.0.1:%d/%s" % (SERVE_PORT, frame), png, 540, height)
        im = Image.open(png).crop((0, 0, width * SCALE, height * SCALE))
        im.save(png)
    im = Image.open(png)
    print("%-42s %s  %d bytes" % (name, im.size, png.stat().st_size))


handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(WORK))
server = http.server.ThreadingHTTPServer(("127.0.0.1", SERVE_PORT), handler)
threading.Thread(target=server.serve_forever, daemon=True).start()

shoot("01_listening_desktop_5A_light", "modern-blue", LISTENING, 1280, 1500)
shoot("02_listening_desktop_5C_dark", "dark", LISTENING, 1280, 1500)
shoot("03_listening_mobile390_5A_light", "modern-blue", LISTENING, 390, 1800)
shoot("04_listening_mobile390_5C_dark", "dark", LISTENING, 390, 1800)
shoot("05_permission_denied_desktop_5A_light", "modern-blue", DENIED, 1280, 1500)

# D-2 close-up: the relocated control beside Submit answer, cropped from the
# desktop light capture above so it is the same real render, not a new one.
src = Image.open(OUT / "01_listening_desktop_5A_light.png")
src.crop((90, 1590, 1790, 2140)).save(OUT / "06_composer_row_D2_desktop_5A_light.png")
print("06_composer_row_D2_desktop_5A_light", Image.open(OUT / "06_composer_row_D2_desktop_5A_light.png").size)

server.shutdown()
