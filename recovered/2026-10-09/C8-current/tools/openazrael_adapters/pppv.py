from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from tools.openazrael_adapters.physical_pppv import (
    adapt_physical_traversal_contract,
)
from tools.openazrael_adapters.well_pppv import adapt_well_tongs_contract
from tools.remaster_framework.validation import ValidationScenario


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _scenario_filename(scenario_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", scenario_id)
    safe = safe.replace(".", "_").strip("_")
    if not safe:
        raise ValueError("scenario_id cannot produce an empty filename")
    return safe + ".json"


def write_scenarios(
    scenarios: list[ValidationScenario],
    output: Path,
    *,
    split_dir: Path | None = None,
) -> dict[str, Any]:
    payload = {
        "schema": "openazrael.pppv_scenario_bundle",
        "version": 1,
        "scenario_count": len(scenarios),
        "scenarios": [scenario.to_dict() for scenario in scenarios],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    if split_dir is not None:
        split_dir.mkdir(parents=True, exist_ok=True)
        for scenario in scenarios:
            path = split_dir / _scenario_filename(scenario.scenario_id)
            path.write_text(
                json.dumps(
                    scenario.to_dict(),
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Adapt OpenAzrael KG contracts to reusable PPPV scenarios."
    )
    parser.add_argument("--physical-contract", type=Path)
    parser.add_argument("--well-contract", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--split-dir",
        type=Path,
        help="Also materialize one deterministic JSON file per scenario.",
    )
    args = parser.parse_args()

    scenarios: list[ValidationScenario] = []
    if args.physical_contract is not None:
        scenarios.extend(
            adapt_physical_traversal_contract(_load(args.physical_contract))
        )
    if args.well_contract is not None:
        scenarios.extend(adapt_well_tongs_contract(_load(args.well_contract)))
    if not scenarios:
        parser.error("at least one contract input is required")

    write_scenarios(
        scenarios,
        args.output,
        split_dir=args.split_dir,
    )
    print(f"PPPV scenarios OK: {len(scenarios)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
