#!/usr/bin/env python3
"""Reject empty, all-black, or effectively flat D600 screenshots."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageStat


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument("--minimum-nonblack-ratio", type=float, default=0.01)
    parser.add_argument("--minimum-luminance-span", type=int, default=12)
    args = parser.parse_args()

    with Image.open(args.image) as image:
        luminance = image.convert("L")
        histogram = luminance.histogram()
        total = sum(histogram)
        nonblack = sum(histogram[4:])
        extrema = luminance.getextrema()
        mean = ImageStat.Stat(luminance).mean[0]

    ratio = nonblack / total if total else 0.0
    span = extrema[1] - extrema[0] if extrema else 0
    print(
        f"width={image.width} height={image.height} "
        f"mean_luminance={mean:.3f} nonblack_ratio={ratio:.6f} "
        f"luminance_span={span}"
    )

    if total == 0:
        return 1
    if ratio < args.minimum_nonblack_ratio:
        return 1
    if span < args.minimum_luminance_span:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
