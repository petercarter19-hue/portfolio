"""Pixel forensics for parity review.

Usage:
  sample_colors.py <image> point x,y [x,y ...]        -> hex at each pixel
  sample_colors.py <image> region x,y,w,h [...]       -> average hex per region
  sample_colors.py <image> dominant x,y,w,h [...]     -> five most common colors per region
  sample_colors.py <image> size                       -> image WxH

Coordinates are raw pixels of the given image. Compare mockup vs build by
sampling the equivalent region in each and diffing the numbers.
"""
import sys

from PIL import Image


def hexval(rgb):
    return "#{:02X}{:02X}{:02X}".format(*rgb[:3])


img = Image.open(sys.argv[1]).convert("RGB")
mode = sys.argv[2]

if mode == "size":
    print(f"{img.width}x{img.height}")
elif mode == "point":
    for spec in sys.argv[3:]:
        x, y = (int(v) for v in spec.split(","))
        print(f"{spec} -> {hexval(img.getpixel((x, y)))}")
elif mode == "region":
    for spec in sys.argv[3:]:
        x, y, w, h = (int(v) for v in spec.split(","))
        box = img.crop((x, y, x + w, y + h))
        pixels = list(box.getdata())
        n = len(pixels)
        avg = tuple(sum(p[i] for p in pixels) // n for i in range(3))
        print(f"{spec} -> avg {hexval(avg)}")
elif mode == "dominant":
    for spec in sys.argv[3:]:
        x, y, w, h = (int(v) for v in spec.split(","))
        box = img.crop((x, y, x + w, y + h))
        colors = box.getcolors(maxcolors=max(1, w * h)) or []
        ranked = sorted(colors, key=lambda item: item[0], reverse=True)[:5]
        result = ", ".join(f"{hexval(rgb)}={count}" for count, rgb in ranked)
        print(f"{spec} -> {result}")
else:
    raise SystemExit(f"unknown mode {mode}")
