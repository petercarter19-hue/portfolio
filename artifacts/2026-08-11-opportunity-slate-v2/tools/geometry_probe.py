"""Locate structural rules and borders in a raster reference or capture.

Usage: geometry_probe.py <image> <probes.json>

Each JSON probe names an axis (row/col), an inclusive coordinate search
range, a perpendicular pixel span, a target hex color, and a per-channel
tolerance.  The best-scoring coordinate is emitted with its match count.
"""

import json
import sys

from PIL import Image


image = Image.open(sys.argv[1]).convert("RGB")
probes = json.load(open(sys.argv[2], encoding="utf-8"))


def rgb(hex_value):
    value = hex_value.lstrip("#")
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))


def matches(pixel, target, tolerance):
    return all(abs(pixel[index] - target[index]) <= tolerance for index in range(3))


results = {}
for name, probe in probes.items():
    target = rgb(probe["target"])
    tolerance = int(probe.get("tolerance", 6))
    search_start, search_end = probe["search"]
    span_start, span_end = probe["span"]
    scored = []
    for coordinate in range(search_start, search_end + 1):
        if probe["axis"] == "row":
            pixels = (image.getpixel((offset, coordinate)) for offset in range(span_start, span_end + 1))
        elif probe["axis"] == "col":
            pixels = (image.getpixel((coordinate, offset)) for offset in range(span_start, span_end + 1))
        else:
            raise ValueError(f"unknown axis for {name}: {probe['axis']}")
        score = sum(1 for pixel in pixels if matches(pixel, target, tolerance))
        scored.append((score, coordinate))
    score, coordinate = max(scored)
    results[name] = {
        "axis": probe["axis"],
        "coordinate": coordinate,
        "matches": score,
        "span_pixels": span_end - span_start + 1,
        "target": probe["target"],
        "tolerance": tolerance,
    }

print(json.dumps(results, indent=2))
