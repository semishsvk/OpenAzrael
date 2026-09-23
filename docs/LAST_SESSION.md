# OpenAzrael Last Session

## Candidate 4 source hardening — 2026-09-23

Work continued on the authoritative `integration/kg001-candidate3-pppv-v2` branch without creating a new Candidate build.

### Completed source changes

- Introduced `tools/kg001_gate_manifest.py` as the canonical ordered declaration for source/runtime gates. Candidate 3 and Candidate 4 contracts and validators now compare against executable runner declarations rather than relying on a handful of source-string checks.
- Expanded the required runtime contract through trigger v137, localization v139, v122-v130, all-transitions v141, cursor v143, menu v145-v147, deterministic interaction v148, menu toggle v149 and save compatibility v150, plus PPPV v2 evidence.
- Candidate 3 v131 forensic preflight now requires a real PASS for R1/R7/R8 instead of accepting mere report creation.
- InteractionProbe v148 preserves raycast-first behavior and makes the inside-Area3D fallback deterministic. The runtime regression uses two overlapping interactable Area3D volumes, reversed query ordering and 64 repeated selections.
- `LegacySaveSystemV145` now rejects unsupported save versions before state restoration. v150 covers current roundtrip, older version, unknown version, corrupt JSON, wrong schema and incompatible state payload while asserting rejected loads do not mutate live state/room/player position.
- Candidate 4 music receipts now separate canonical event/timing identity, PCM identity and encoded OGG artifact identity. FluidSynth and libsndfile identities are recorded; native FluidSynth library SHA-256 is recorded when a stable resolved file is available. Cross-platform bit identity is explicitly not claimed.
- Added source-safe Candidate 4 frozen handoff: exact commit/tree + preflight receipt SHA + complete runtime-asset identity digest. The exporter requires the matching freeze receipt.
- Updated the source snapshot workflow to support an explicitly requested exact SHA using tracked-source-only `git archive`.
- Added the reusable Verify/Release Orchestrator: diff-targeted FAST selection, fail-safe escalation for unknown critical changes, fingerprint-bound PASS cache reuse, full source VERIFY, and exact-head CI readiness without invoking a Candidate build.

### Evidence status

Exact-head source workflows were observed PASS on `34d5b2077079854c52bac8d8071c98fd40748f3d` for Candidate 3, Candidate 4, Remaster Framework, trigger and localization. That observation proves the earlier zero-step source-CI incident is no longer current.

The source-hardening commits after that SHA still require final exact-head CI observation after documentation sync. Asset-backed Candidate 4 preflight, packaged/export evidence and G10 have **not** been run or inferred in this session.

Candidate 4 and KG-001 therefore remain **NOT Known Good**.

### Next action

Run final source VERIFY on the resulting exact SHA. If all source checks pass, use that exact SHA for the private asset-backed Candidate 4 preflight, freeze the resulting source/runtime identity, then export and perform G10. Do not create a Candidate 4 export merely to validate source-only changes.

Final source VERIFY is required on the exact resulting HEAD; this documentation line deliberately does not promote runtime/export/G10 evidence.

- 2026-09-23: exact-head Candidate 4 validation closure cycle requested; no runtime scope change.


### Candidate 4 proof capture v151

Source-safe proof-capture support is implemented for the frozen Candidate 4 path. It records the real chained PPPV run through Godot Movie Maker, overlays exact source/freeze identity plus room/step status, re-evaluates the captured run, requires replay/final-state identity with the deterministic PPPV baseline, and only then emits MP4 + a SHA-bound receipt. This remains supplemental evidence and does not promote runtime/export/G10 by itself.

No proof MP4 is claimed by source integration alone. A real video still requires the private registered demo corpus, graphical Godot runtime, a PASS Candidate 4 preflight/freeze, and ffmpeg on the exact source SHA.
