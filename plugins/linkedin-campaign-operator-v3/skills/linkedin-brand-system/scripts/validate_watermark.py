#!/usr/bin/env python3
"""Validate a transparent PNG watermark export."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from PIL import Image


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("--expected-width", type=int)
    parser.add_argument("--expected-height", type=int)
    args = parser.parse_args()

    errors: list[str] = []
    try:
        raw = args.image.read_bytes()
        with Image.open(args.image) as image:
            image.load()
            width, height = image.size
            if image.format != "PNG":
                errors.append("watermark must be PNG")
            if "A" not in image.getbands():
                errors.append("watermark must contain an alpha channel")
            else:
                alpha = image.getchannel("A")
                minimum, maximum = alpha.getextrema()
                if minimum == maximum == 255:
                    errors.append("watermark alpha channel contains no transparency")
                if maximum == 0:
                    errors.append("watermark is fully transparent")
            if args.expected_width and width != args.expected_width:
                errors.append(f"width must equal {args.expected_width}")
            if args.expected_height and height != args.expected_height:
                errors.append(f"height must equal {args.expected_height}")
    except (OSError, ValueError) as exc:
        errors.append(str(exc))
        raw = b""
        width = height = None

    result = {
        "valid": not errors,
        "path": str(args.image),
        "width": width,
        "height": height,
        "sha256": hashlib.sha256(raw).hexdigest() if raw else None,
        "errors": errors,
    }
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
