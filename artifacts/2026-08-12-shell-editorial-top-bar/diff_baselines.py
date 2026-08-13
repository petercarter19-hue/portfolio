"""Compare two shell frame sets, byte for byte and then pixel for pixel.

    python diff_baselines.py <reference_dir> <candidate_dir>

A frame that is byte-identical is reported as identical. A frame whose bytes
differ is opened and compared pixel by pixel, because PNG encoding is not
guaranteed stable — a pixel-identical frame with different bytes is still a
pass, and only a non-zero pixel delta is a real difference.
"""
import sys
from pathlib import Path

from PIL import Image, ImageChops

ref = Path(sys.argv[1])
cand = Path(sys.argv[2])

ref_names = {p.name for p in ref.glob("*.png")}
cand_names = {p.name for p in cand.glob("*.png")}

only_ref = sorted(ref_names - cand_names)
only_cand = sorted(cand_names - ref_names)
shared = sorted(ref_names & cand_names)

byte_identical = []
pixel_identical = []
different = []

for name in shared:
    a, b = ref / name, cand / name
    if a.read_bytes() == b.read_bytes():
        byte_identical.append(name)
        continue
    # RGB, and getextrema() rather than getbbox(). Pillow's getbbox() takes an
    # alpha_only argument that defaults to True, so on an RGBA pair it inspects
    # ONLY the alpha channel — and two fully opaque screenshots always have an
    # identical alpha channel. It returned None, meaning "identical", for
    # frames with 167 differing colour pixels. Comparing channel extrema on RGB
    # has no such trapdoor.
    ia = Image.open(a).convert("RGB")
    ib = Image.open(b).convert("RGB")
    if ia.size != ib.size:
        different.append((name, f"size {ia.size} vs {ib.size}"))
        continue
    diff = ImageChops.difference(ia, ib)
    worst = max(high for _, high in diff.getextrema())
    if worst == 0:
        pixel_identical.append(name)
    else:
        box = diff.getbbox(alpha_only=False)
        changed = sum(1 for p in diff.getdata() if p != (0, 0, 0))
        different.append(
            (name, f"{changed} px differ in {box}, max channel delta {worst}")
        )


def group(name):
    for key in ("switcher-open", "account-open", "sheet-open", "search-results",
                "search-empty", "nav-hover", "nav-focus", "bottombar",
                "200pct", "header"):
        if key in name:
            return key
    return "other"


groups = {}
for name in shared:
    state = "different" if name in dict(different) else "identical"
    g = groups.setdefault(group(name), {"identical": 0, "different": 0})
    g[state] += 1

print(f"reference {ref}  ({len(ref_names)} frames)")
print(f"candidate {cand}  ({len(cand_names)} frames)")
print()
print(f"{'frame group':16} {'identical':>10} {'different':>10}")
for g in sorted(groups):
    print(f"{g:16} {groups[g]['identical']:>10} {groups[g]['different']:>10}")
print()
print(f"byte-identical  {len(byte_identical)}")
print(f"pixel-identical {len(pixel_identical)}  (bytes differ, pixels do not)")
print(f"DIFFERENT       {len(different)}")
if only_ref:
    print(f"only in reference ({len(only_ref)}): {only_ref[:10]}")
if only_cand:
    print(f"only in candidate ({len(only_cand)}): {only_cand[:10]}")
for name, why in different:
    print(f"  DIFF {name}: {why}")
sys.exit(1 if different or only_ref or only_cand else 0)
