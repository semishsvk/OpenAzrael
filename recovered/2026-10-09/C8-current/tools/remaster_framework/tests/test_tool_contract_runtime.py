from __future__ import annotations

import unittest
from pathlib import Path

from tools.remaster_framework.contracts import (
    ToolContract,
    ToolFamily,
    ToolMaturity,
)


class ToolContractRuntimeTests(unittest.TestCase):
    def test_source_safe_tool_may_mutate_ephemeral_runtime(self) -> None:
        root = Path(__file__).resolve().parents[3]
        contract = ToolContract(
            tool_id="pppv_driver",
            family=ToolFamily.VALIDATION_LAB,
            description="Physical runtime driver",
            entrypoint="scripts/validation/pppv_player_driver.gd",
            source_safe=True,
            deterministic=False,
            mutates_runtime=True,
            maturity=ToolMaturity.POC,
        )
        self.assertEqual(contract.validate(root), [])


if __name__ == "__main__":
    unittest.main()
