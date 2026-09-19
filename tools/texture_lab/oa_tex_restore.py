#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import shlex
import subprocess

from common import ROOT, sha256_file, write_json


def main() -> int:
    parser = argparse.ArgumentParser(
        description="AI Restored adapter. Executes a local Real-ESRGAN command template; generated pixels stay outside Git."
    )
    parser.add_argument("--input", type=Path, default=ROOT / "assets/textures/classic")
    parser.add_argument("--output", type=Path, default=ROOT / "assets/textures/ai_restored")
    parser.add_argument("--report", type=Path, default=ROOT / "data/texture_lab/ai_restore_run.json")
    parser.add_argument("--factor", type=int, default=4)
    parser.add_argument("--model", default="realesrgan-x4plus")
    parser.add_argument("--only", nargs="*", default=None)
    parser.add_argument(
        "--command",
        required=True,
        help="Command template containing {input}, {output}, {factor}, {model}. Example syntax is local-install dependent.",
    )
    args = parser.parse_args()

    wanted = set(args.only or [])
    sources = [p for p in sorted(args.input.glob("*.png")) if not wanted or p.stem in wanted]
    if not sources:
        raise SystemExit("no input PNGs selected")

    rows = []
    for src in sources:
        out_dir = args.output / src.stem
        out_dir.mkdir(parents=True, exist_ok=True)
        dest = out_dir / f"realesrgan_x{args.factor}.png"
        rendered = args.command.format(
            input=str(src),
            output=str(dest),
            factor=args.factor,
            model=args.model,
        )
        subprocess.run(shlex.split(rendered), check=True)
        if not dest.is_file():
            raise RuntimeError(f"restore command did not create: {dest}")
        rows.append(
            {
                "id": src.stem,
                "source_sha256": sha256_file(src),
                "output_sha256": sha256_file(dest),
                "model": args.model,
                "factor": args.factor,
            }
        )

    write_json(
        args.report,
        {
            "schema": "openazrael.texture_lab.ai_restore_run.v1",
            "mode": "ai_restored",
            "command_template": args.command,
            "textures": rows,
        },
    )
    print(f"PASS ai_restored textures={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
