#!/usr/bin/env python3
"""Inspect deterministic dimensions, timing, and format metrics for a GIF."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

from PIL import Image, ImageSequence


MAX_BYTES = 100 * 1024 * 1024
MAX_FRAMES = 500
MAX_PIXELS = 36_152_320


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("gif", type=Path)
    args = parser.parse_args()

    errors: list[str] = []
    try:
        byte_size = args.gif.stat().st_size
        with Image.open(args.gif) as image:
            if image.format != "GIF":
                errors.append("file must be GIF")
            width, height = image.size
            durations = [int(frame.info.get("duration", image.info.get("duration", 0))) for frame in ImageSequence.Iterator(image)]
            frame_count = len(durations)
            total_duration = sum(durations)
            loop = image.info.get("loop")
            transparency = "transparency" in image.info or any("A" in frame.getbands() for frame in ImageSequence.Iterator(image))
            palette_colors = len(image.getcolors(maxcolors=256) or [])
        if byte_size > MAX_BYTES:
            errors.append("GIF exceeds 100 MB")
        if frame_count > MAX_FRAMES:
            errors.append("GIF exceeds 500 frames")
        if width * height > MAX_PIXELS:
            errors.append("GIF exceeds 36,152,320 pixels")
    except (OSError, ValueError) as exc:
        errors.append(str(exc))
        byte_size = width = height = frame_count = total_duration = loop = palette_colors = None
        durations = []
        transparency = None

    result = {
        "valid": not errors,
        "path": str(args.gif),
        "byte_size": byte_size,
        "width": width,
        "height": height,
        "pixel_count": width * height if width and height else None,
        "frame_count": frame_count,
        "total_duration_ms": total_duration,
        "frame_duration_ms": {
            "minimum": min(durations) if durations else None,
            "median": statistics.median(durations) if durations else None,
            "maximum": max(durations) if durations else None,
        },
        "loop": loop,
        "transparency": transparency,
        "palette_colors": palette_colors,
        "errors": errors,
    }
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
