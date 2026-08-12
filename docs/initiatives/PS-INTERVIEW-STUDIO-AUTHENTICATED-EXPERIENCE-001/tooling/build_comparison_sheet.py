"""Builds the lock-vs-build comparison sheet as one self-contained HTML file
(images inlined as data URIs, scaled) for Pete's review."""
import base64
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "pylibs"))
from PIL import Image

LOCKS = r"C:\Users\peter\iCloudDrive\PeerSlate Architect Handoffs\2026-08-11\Interview Studio Claude Architecture Handoff 2026-08-11\02_VISUAL_AUTHORITY\FINAL"
BUILD = r"C:\Users\peter\Documents\portfolio-interview-studio-auth-20260811\artifacts\2026-08-11-interview-studio-authenticated\fable-rebuild"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "comparison_sheet.html")

MAX_W = 820  # per-image width in the sheet


def data_uri(path):
    img = Image.open(path).convert("RGB")
    if img.width > MAX_W:
        img = img.resize((MAX_W, int(img.height * MAX_W / img.width)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=72)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def main():
    names = sorted(n for n in os.listdir(BUILD) if n.endswith(".png"))
    rows = []
    for name in names:
        lock_path = os.path.join(LOCKS, name)
        build_path = os.path.join(BUILD, name)
        if not os.path.exists(lock_path):
            continue
        rows.append(
            f'<section><h2>{name[:-4]}</h2><div class="pair">'
            f'<figure><figcaption>Mockup (locked)</figcaption><img src="{data_uri(lock_path)}"></figure>'
            f'<figure><figcaption>Build</figcaption><img src="{data_uri(build_path)}"></figure>'
            f"</div></section>"
        )
    html = (
        "<!doctype html><meta charset='utf-8'><title>Interview Studio — mockup vs build</title>"
        "<style>body{font-family:Inter,system-ui,sans-serif;background:#f5f2ec;margin:2rem;color:#10263c}"
        "h1{font-size:1.3rem}h2{font-size:1rem;margin:2.2rem 0 .6rem}"
        ".pair{display:grid;grid-template-columns:1fr 1fr;gap:1rem}"
        "figure{margin:0}figcaption{font-size:.8rem;color:#4b5c67;margin-bottom:.3rem;font-weight:600}"
        "img{width:100%;border:1px solid #d9cfc2;border-radius:8px}</style>"
        "<h1>Interview Studio authenticated rebuild — locked mockup (left) vs build (right)</h1>"
        + "".join(rows)
    )
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print("wrote", OUT, f"({len(rows)} pairs, {os.path.getsize(OUT)//1024} KB)")


if __name__ == "__main__":
    main()
