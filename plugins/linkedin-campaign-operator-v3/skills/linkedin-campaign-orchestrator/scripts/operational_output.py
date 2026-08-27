#!/usr/bin/env python3
"""Compatibility entry point for the v6 rolling-output controller."""

from __future__ import annotations

import runpy
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "linkedin-engagement-execution"
    / "scripts"
    / "rolling_output.py"
)


if __name__ == "__main__":
    runpy.run_path(str(SCRIPT), run_name="__main__")
