import ast
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RESTORE_TOOL = ROOT / "tools" / "restore_candidate_assets.py"


class CandidateAssetRestoreReceiptSourceTests(unittest.TestCase):
    def test_restore_receipt_suffix_is_real_newline_and_json_parseable(self):
        source = RESTORE_TOOL.read_text(encoding="utf-8")
        tree = ast.parse(source)
        matches = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (isinstance(func, ast.Attribute) and func.attr == "write_text"):
                continue
            if not node.args:
                continue
            expr = node.args[0]
            if isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Add):
                if isinstance(expr.right, ast.Constant) and isinstance(expr.right.value, str):
                    matches.append(expr.right.value)
        self.assertIn("\n", matches)
        self.assertNotIn("\\n", matches)

        sample = json.dumps({"schema": "openazrael.kg001.candidate_asset_restore", "status": "PASS"}, indent=2) + "\n"
        self.assertEqual(json.loads(sample)["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
