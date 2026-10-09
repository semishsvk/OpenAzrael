#!/usr/bin/env python3
from pathlib import Path
import json, sys

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "data/kg001_acceptance_contract.json"
EXPECTED = [f"G{i:02d}" for i in range(11)]
errors = []

try:
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))
except Exception as exc:
    print("KG-001 contract validation: FAIL")
    print(" - contract:", exc)
    sys.exit(1)

if data.get("schema") != "openazrael.kg001_acceptance_contract":
    errors.append("schema mismatch")
if data.get("status") != "ACCEPTED":
    errors.append("contract is not ACCEPTED")
if data.get("target_tag") != "demo-known-good-001":
    errors.append("target tag drift")

gates = data.get("gates", [])
ids = [g.get("id") for g in gates]
if ids != EXPECTED:
    errors.append(f"gate ids/order mismatch: {ids}")
if not all(g.get("required") is True for g in gates):
    errors.append("every KG-001 gate must be required")

policy = data.get("release_policy", {})
for key in [
    "zero_known_critical_bugs",
    "zero_reproducible_softlocks",
    "zero_failed_required_gates",
    "fresh_checkout_required",
    "manual_sanity_required",
    "immutable_tag",
]:
    if policy.get(key) is not True:
        errors.append(f"release policy disabled: {key}")

boundary = data.get("forensic_boundary", {})
if boundary.get("known_good_does_not_promote_holds") is not True:
    errors.append("forensic HOLD separation missing")

if errors:
    print("KG-001 contract validation: FAIL")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("KG-001 contract validation: PASS")
print(" target tag: demo-known-good-001")
print(" required gates:", len(gates))
