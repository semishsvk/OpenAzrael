# C5 pre-execution freeze

Status: PREPARATION_COMPLETE_EXECUTION_PENDING

This document freezes the preparation boundary for the next KG-001 candidate without claiming runtime, package, pacing, or manual acceptance.

## Immutable game-source baseline
- Repository: semishsvk/OpenAzrael
- Branch under validation: integration/kg001-candidate3-pppv-v2
- Exact commit: eb4ccc15e19a388980c483318465b6dbb0c448e1
- Any tracked source change starts a new evidence cycle.

## Toolchain handoff
Toolchain/bootstrap development is isolated on branch toolchain/c5-release-bootstrap and is not part of the frozen game-source identity.
Required identities are declared in toolchain/toolchain_registry_v1.json.
Discovery after registration is forbidden; cache/hash verification is fail-closed.

## Execution order
1. Materialize and verify the declared toolchain; emit .tmp/kg001/c5_toolchain_receipt.json.
2. Register/verify the canonical demo source; restore ignored runtime assets.
3. Run Candidate 4 preflight with explicit Godot, demo source, SoundFont and FluidSynth library.
4. Require inherited Candidate 3 runtimes, visual v126, room forensic v131 and PPPV v2 evidence, including repeated determinism.
5. Produce current-head C4 closure evidence required by v200/v201. Historical Candidate 4 evidence is forbidden.
6. Capture original R.EXE pacing under the v199 DOSBox reference profile. This is reproducibility reference evidence, not source authority.
7. Freeze the PASS preflight with tools/freeze_candidate4_release.py.
8. Export exact Windows EXE/PCK from the frozen identity.
9. Run packaged parity against the exported pair.
10. Run manual G10 on that exact exported pair.
11. Capture final runtime evidence and attest Candidate acceptance.

## Fail-closed blockers
- toolchain hash/version mismatch
- source corpus missing/fingerprint drift
- dirty or changed Git HEAD/tree
- missing/mutated runtime assets or receipts
- any required runtime/PPPV/visual/forensic/audio/music failure
- missing current-head identity
- transition failure, crash or softlock
- package parity failure
- G10 failure

## Explicitly not claimed before execution
- FAST/VERIFY runtime PASS
- current-head PPPV PASS
- original pacing PASS
- package/export PASS
- manual G10 PASS
- Candidate acceptance

Preparation is complete when this handoff and the toolchain registry are present. No additional game-content development is authorized unless execution produces a concrete regression.
