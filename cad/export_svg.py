"""Generate docs/2d/*.svg from sketch profiles."""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from cad.profiles import all_profiles
from cad.svg_util import write_svg


def main(out_dir: str | None = None):
    out_dir = out_dir or os.path.join(ROOT, "docs", "2d")
    os.makedirs(out_dir, exist_ok=True)
    profiles = all_profiles()
    for name, pts in profiles.items():
        path = os.path.join(out_dir, f"{name}.svg")
        write_svg(path, f"2D sketch: {name}", [(name, pts)], width=480, height=360, scale=2.2)
    # joint layout overview
    overview = [
        ("upper", profiles["upper_ibeam"]),
        ("fore", [(x + 90, y) for x, y in profiles["fore_ibeam"]]),
    ]
    write_svg(
        os.path.join(out_dir, "00_link_layout.svg"),
        "Link layout (upper + forearm) — split lines at mid",
        overview,
        width=640,
        height=280,
        scale=1.6,
    )
    return sorted(os.listdir(out_dir))


if __name__ == "__main__":
    print(main())
