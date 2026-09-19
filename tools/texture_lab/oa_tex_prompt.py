#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import ROOT


def build_prompt(profiles: dict, content_class: str) -> str:
    base = str(profiles["base"]).strip()
    class_text = str(profiles.get("classes", {}).get(content_class, "")).strip()
    negative = str(profiles.get("negative", "")).strip()
    parts = [base]
    if class_text:
        parts.append(class_text)
    if negative:
        parts.append("Constraints: " + negative)
    return " ".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a consistent AI Recreated prompt from RT-POC-01 metadata.")
    parser.add_argument("texture_id")
    parser.add_argument(
        "--selection",
        type=Path,
        default=ROOT / "tools/texture_lab/config/rt_poc_01_selection.json",
    )
    parser.add_argument(
        "--profiles",
        type=Path,
        default=ROOT / "tools/texture_lab/profiles/recreate_profiles.json",
    )
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    profiles = json.loads(args.profiles.read_text(encoding="utf-8"))
    entry = next((row for row in selection["textures"] if row["id"] == args.texture_id), None)
    if entry is None:
        raise SystemExit(f"texture id is not in RT-POC-01 selection: {args.texture_id}")

    text = build_prompt(profiles, str(entry["content_class"]))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
        print(f"PASS prompt={args.output}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
