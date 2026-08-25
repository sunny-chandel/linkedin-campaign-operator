#!/usr/bin/env python3
"""Promote a GIF pattern and permanently delete a dominated contradictory pattern."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


DOMINANT_SCORE = 85.0
DOMINANT_MARGIN = 15.0


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain an object")
    return value


def atomic_write(path: Path, value: dict[str, Any]) -> None:
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def safe_capture_paths(pattern: dict[str, Any], capture_root: Path) -> list[Path]:
    resolved_root = capture_root.resolve()
    paths: list[Path] = []
    for raw in pattern.get("capture_paths", []):
        candidate = Path(raw)
        if not candidate.is_absolute():
            candidate = resolved_root / candidate
        resolved = candidate.resolve()
        if resolved != resolved_root and resolved_root not in resolved.parents:
            raise ValueError(f"capture path escapes capture root: {raw}")
        paths.append(resolved)
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("library", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--capture-root", type=Path, required=True)
    args = parser.parse_args()

    try:
        library = load_object(args.library)
        candidate = load_object(args.candidate)
        pattern_id = candidate.get("pattern_id")
        score = candidate.get("reference_score")
        if not isinstance(pattern_id, str) or not pattern_id:
            raise ValueError("candidate.pattern_id must be set")
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 100:
            raise ValueError("candidate.reference_score must be from 0 to 100")
        patterns = library.get("patterns", [])
        if not isinstance(patterns, list) or not all(isinstance(item, dict) for item in patterns):
            raise ValueError("library.patterns must be an array of objects")

        deleted_pattern_id = None
        deleted_capture_paths: list[str] = []
        conflict_id = candidate.get("contradicts_pattern_id")
        existing = next((item for item in patterns if item.get("pattern_id") == conflict_id), None)
        if existing is not None:
            existing_score = existing.get("reference_score")
            if isinstance(existing_score, bool) or not isinstance(existing_score, (int, float)):
                raise ValueError("contradictory pattern requires a numeric reference_score")
            if score >= DOMINANT_SCORE and score - float(existing_score) >= DOMINANT_MARGIN:
                for capture in safe_capture_paths(existing, args.capture_root):
                    if capture.is_file():
                        capture.unlink()
                        deleted_capture_paths.append(str(capture))
                patterns = [item for item in patterns if item.get("pattern_id") != conflict_id]
                deleted_pattern_id = conflict_id

        patterns = [item for item in patterns if item.get("pattern_id") != pattern_id]
        patterns.append(candidate)
        patterns.sort(key=lambda item: item.get("pattern_id", ""))
        library["patterns"] = patterns
        atomic_write(args.library, library)
        print(
            json.dumps(
                {
                    "promoted": pattern_id,
                    "deleted_pattern_id": deleted_pattern_id,
                    "deleted_capture_paths": deleted_capture_paths,
                }
            )
        )
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
