# OpenAzrael v111 — consolidated KG-001 gate status

The repository now has one machine-readable status layer for all G00-G10 gates.

Current overall state is **PRE_RUNTIME_READY**. No required gate is recorded as FAIL, but the release tag is **not allowed** because source/model readiness is intentionally distinct from runtime PASS.

## Current gate picture

- G00 context integrity — validator ready, not yet recorded as release PASS.
- G01 data validation — validators ready, not yet recorded as release PASS.
- G02 gameplay logic — source-model PASS, Godot runtime pending.
- G03 exhaustive puzzle state-space — source-model PASS: 63 reachable states, 0 modeled softlocks.
- G04 room transitions — source contract PASS, asset-backed runtime pending.
- G05 triggers — source contract PASS, asset-backed runtime pending.
- G06 logical audio event stream — source contract PASS, runtime pending.
- G07 save/load state hash — source contract PASS, runtime pending.
- G08 full synthetic demo — source contract PASS, runtime pending.
- G09 fresh checkout — pending.
- G10 user manual sanity — pending.

tools/kg001_status_v111.py automatically looks for future runtime result files and upgrades only the corresponding gates. It never treats SOURCE_*, READY_* or PENDING as release PASS.

The tag demo-known-good-001 is allowed only if **every** G00-G10 status is literal PASS.
