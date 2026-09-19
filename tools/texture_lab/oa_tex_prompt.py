#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import ROOT


def build_prompt_pair(profiles: dict, content_class: str) -> dict[str, str]:
    base = str(profiles["base"]).strip()
    class_text = str(profiles.get("classes", {}).get(content_class, "")).strip()
    positive_parts = [base]
    if class_text:
        positive_parts.append(class_text)
    return {
        "positive": " ".join(positive_parts).strip(),
        "negative": str(profiles.get("negative", "")).strip(),
    }


def build_prompt(profiles: dict, content_class: str) -> str:
    pair = build_prompt_pair(profiles, content_class)
    parts = [pair["positive"]]
    if pair["negative"]:
        parts.append("Constraints: " + pair["negative"])
    return " ".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build consistent AI Recreated prompts from RT-POC-01 metadata.")
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
    parser.add_argument(
        "--format",
        choices=["combined", "positive", "negative", "json"],
        default="combined",
    )
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    profiles = json.loads(args.profiles.read_text(encoding="utf-8"))
    entry = next((row for row in selection["textures"] if row["id"] == args.texture_id), None)
    if entry is None:
        raise SystemExit(f"texture id is not in RT-POC-01 selection: {args.texture_id}")

    pair = build_prompt_pair(profiles, str(entry["content_class"]))
    if args.format == "positive":
        text = pair["positive"]
    elif args.format == "negative":
        text = pair["negative"]
    elif args.format == "json":
        text = json.dumps(pair, indent=2, sort_keys=True)
    else:
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
