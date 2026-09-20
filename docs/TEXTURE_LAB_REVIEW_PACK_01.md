# OpenAzrael Texture Lab — Review Pack 01

**Status:** SOURCE PLAN READY / real AI outputs stage-dependent  
**Scope:** the existing 12 canonical RT-POC-01 textures used by R1/R7/R8  
**Decision policy:** manual review only; no automatic ranking, winner, threshold or production promotion

Review Pack 01 is a review-order and evidence-plan layer over the existing Texture Lab pipeline. It does **not** introduce a new AI stage and does not bypass the existing Restored/Recreated smoke, review, approval or production-selection contracts.

## Treatment classes

- **safe_upscale** — deterministic Enhanced is the natural improvement baseline. AI is useful only if it adds visible value without reducing fidelity.
- **ai_recreation_candidate** — a full Classic / Enhanced / AI comparison is useful because learned reconstruction may improve material, organic or artwork detail.
- **conservative** — semantic, puzzle, text, alpha, transparency or geometry risk dominates. Classic/Enhanced remain truth; AI is constrained by the existing policy and may be disabled completely.

## Review order

| # | Texture | Room | Priority | Treatment | Key review focus |
|---:|---|---|---|---|---|
| 1 | CORIROCK | R1 | P1 | safe_upscale | rock material microdetail; avoid plastic surface; gameplay-scale clarity |
| 2 | KEYHOLE# | R1 | P1 | conservative | exact binary hard-edge mask; Enhanced nearest reference; no AI required |
| 3 | WEL_PUZ1 | R7 | P1 | conservative | puzzle readability; holes/levers/plates alignment; no semantic geometry drift |
| 4 | BAPFLOR# | R8 | P1 | conservative | exact alpha lock; U/V repeat seams; no pattern drift |
| 5 | BAPTAP | R8 | P1 | ai_recreation_candidate | four-quarter atlas lock; figures/objects preserved; no cross-panel hallucination |
| 6 | SHIELD1 | R8 | P1 | conservative | exact text characters and line layout; symbol geometry |
| 7 | ECRDOR01 | R1 | P2 | ai_recreation_candidate | doorway opening/trim geometry and proportions |
| 8 | WEL_WWAL | R7 | P2 | safe_upscale | carved detail; U-edge continuity; no false relief |
| 9 | WEL_BDY1 | R7 | P2 | ai_recreation_candidate | anatomy, pose, silhouette, expression and props |
| 10 | WEL_FLOR | R7 | P2 | safe_upscale | circular structure, openings and edge placement |
| 11 | BAPGLASS | R8 | P2 | conservative | translucent style; no invented reflections/environment |
| 12 | VSTPAP01 | R1 | P3 | conservative | paper silhouette, stains and markings; no invented writing |

The order is for **human review efficiency**, not product ranking.

## A / B / C comparison model

For each texture the planner derives the actual eligible set from the existing selection, policy, sampling and smoke-stage contracts:

- **A — Classic:** immutable source reference.
- **B — Enhanced:** deterministic reference; normally Lanczos 4x, except KEYHOLE# where nearest-neighbour is the conservative reference.
- **C — AI candidate evidence:** AI Restored and/or AI Recreated only when that texture is eligible and the normal named stage has produced current evidence.

Examples:

- **KEYHOLE#**: Classic + Enhanced nearest only. Both AI modes remain disabled by policy.
- **SHIELD1**: Classic + Enhanced Lanczos + AI Restored. AI Recreated remains disabled because text can be rewritten.
- **BAPTAP**: Classic + Enhanced Lanczos + AI Restored + AI Recreated; Recreated begins at the dedicated four-segment `recreated_atlas` stage.
- **BAPFLOR#**: all eligible candidates, but exact alpha and U/V seam checks remain mandatory.

Missing AI output is never interpreted as a failed or inferior candidate; it means the corresponding stage has not produced current evidence yet.

## Manual rubric

Score each applicable dimension from **1 to 5**, where 5 is best. `N/A` is allowed where a dimension does not apply.

1. **Fidelity to original** — authored composition, geometry and identity.
2. **Readability / detail** — useful clarity at gameplay scale without false structure.
3. **Material believability** — plausible material detail consistent with the source.
4. **Atmosphere / period feel** — preserves the visual character and mood of *Azrael's Tear*.
5. **Tiling / seam safety** — no new edge discontinuity; required repeat/atlas boundaries remain safe.
6. **Semantic / gameplay safety** — symbols, puzzle cues, openings, text and object meaning remain exact.
7. **Artifact cleanliness** — no material ringing, false edges, hallucinated microdetail, anatomy errors or plastic look.
8. **Alpha / transparency safety** — source mask/transparency policy remains intact where applicable.

There is deliberately **no aggregate score and no automatic threshold**. A reviewer may judge one dimension critical enough to HOLD or reject a candidate regardless of other scores.

## Commands

Validate the source plan:

```bash
python tools/texture_lab/oa_tex_review_pack_01.py validate
```

Render a deterministic source-plan snapshot:

```bash
python tools/texture_lab/oa_tex_review_pack_01.py render \
  --out-json .local/texture_lab/review_pack_01/source_plan.json \
  --out-md .local/texture_lab/review_pack_01/source_plan.md
```

This is separate from real AI stage execution. Actual image comparisons continue to use the existing stage-specific review pack, Godot REVIEW profile and structured manual-review/approval pipeline. Stage-specific review packs now also include a fingerprinted alpha evidence sheet (expected alpha, candidate alpha, absolute delta and expected edge band) for manual transparency/halo inspection.

A passive per-asset lifecycle/readiness dashboard is available with:

```bash
python tools/texture_lab/oa_tex_asset_status.py
```

It reports evidence readiness only; it does not compute a winner or quality score.

## Prioritized visual hub

Once local Classic/Enhanced references exist, Review Pack 01 can materialize a convenience HTML overview in P1 -> P3 order:

```bash
python tools/texture_lab/oa_tex_review_pack_01.py hub \
  --out-dir .local/texture_lab/review_pack_01/current
```

Optional explicit output paths:

```bash
python tools/texture_lab/oa_tex_review_pack_01.py hub \
  --out-dir .local/texture_lab/review_pack_01/current \
  --out-json .local/texture_lab/review_pack_01/current/hub.json \
  --out-html .local/texture_lab/review_pack_01/current/hub.html
```

For each reference-ready texture the hub renders:
- Classic source as the comparison truth;
- the configured deterministic Enhanced reference;
- only AI Restored/Recreated candidates backed by current PASS named-stage evidence;
- a full comparison sheet;
- a detail comparison sheet;
- one alpha evidence sheet for every materialized Enhanced/AI variant;
- the texture-specific Review Pack attention list.

The hub verifies current file size/SHA-256 before using every reference/candidate and refuses stale evidence. Textures without local Classic/Enhanced references are listed as skipped rather than treated as quality failures.

The hub is **not approval evidence**. Stage-specific review packs, repeat/seam previews, structured manual review records and approval receipts remain authoritative.

## Evidence boundary

**SOURCE_PLAN_READY** means the shortlist, treatment classes, review order, eligibility mapping and rubric are internally consistent with current Texture Lab contracts.

It does **not** mean:
- Real-ESRGAN or Qwen has run;
- an AI candidate exists for every texture;
- a candidate has passed manual review;
- any production texture has been selected.
