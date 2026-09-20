from __future__ import annotations

import argparse
import json
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Adapt OpenAzrael KG contracts to reusable PPPV scenarios."
    )
    parser.add_argument("--physical-contract", type=Path)
    parser.add_argument("--well-contract", type=Path)
    parser.add_argument("--output", type=Path, required=True)
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

    payload = {
        "schema": "openazrael.pppv_scenario_bundle",
        "version": 1,
        "scenario_count": len(scenarios),
        "scenarios": [scenario.to_dict() for scenario in scenarios],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"PPPV scenarios OK: {len(scenarios)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
