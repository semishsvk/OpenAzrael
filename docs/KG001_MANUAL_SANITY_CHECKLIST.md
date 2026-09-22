# KG-001 G10 — manual sanity checklist

Run G10 only after the exact Candidate 2 package has a **v118 test-build receipt** with status `READY_FOR_G10_MANUAL_TEST`. That receipt already proves the automated preconditions for the same commit/package: complete restored asset set, fresh-checkout G09, canonical R1/R7/R8 visual capture, Windows export and exported-EXE startup smoke.

G10 remains human/manual. The receipt does **not** make the build known-good and does not close Issues #6, #9 or #11.

## 1. Initialize evidence for the exact test build

From the same checkout/package:

```bash
python tools/record_kg001_g10_v118.py init
```

This creates `.tmp/kg001/kg001_manual_sanity_v118.json` and copies build identity from:

`exports/OpenAzrael-KG001-Candidate2-v116.test-build.json`

The result is bound to the receipt SHA-256, candidate commit, EXE SHA-256, PCK SHA-256 and exact Godot version. Do not edit those identity fields manually.

## 2. Perform the manual checks

If any defect appears, press **F11 before quitting** and preserve the generated source-safe diagnostic ZIP.

Required checks:

- project launches without a blocking error;
- mouse/look and movement controls behave normally;
- R1 floor collision is stable;
- R7 floor collision is stable;
- R8 floor collision is stable;
- R1 keyhole cutout has correct transparency with no visible pink/magenta or black fringe;
- rusty-tongs/MINETON# cutout has correct transparency with no visible pink/magenta or black fringe;
- R1 tongs can be picked up;
- Door 1 opens and R1 -> R7 traversal works;
- Well Key requires/uses the tongs and is acquired;
- R7 lever -> wheel -> lever sequence drains the R8 bath;
- R7 -> R1 return works and persistent state is preserved;
- Door 2 unlocks with the Well Key and R1 -> R8 traversal works;
- lens is obtainable only after bath drain;
- lens can be placed on the Bible;
- optical mechanism activates from the intended zxplate zone;
- secret door opens and the Shield becomes obtainable;
- taking the Shield completes the demo;
- expected ambient/event gameplay sounds are actually audible to human perception;
- no visible magenta key-color rectangles/halos/fringes remain on other `#` cutout textures encountered during the route;
- save/load round-trip preserves the tested demo state;
- F11 creates a source-safe diagnostic ZIP without changing observed gameplay state;
- no reproducible critical bug was observed;
- no reproducible softlock was observed.

Blocker-specific checks must also be recorded separately:

- `issue_6_floor_collision`
- `issue_9_human_audibility`
- `issue_11_colorkey_transparency`

## 3. Record results

Record one or more checks at any time:

```bash
python tools/record_kg001_g10_v118.py record \
  --check floor_r1_stable=PASS \
  --check floor_r7_stable=PASS \
  --check floor_r8_stable=PASS \
  --blocker issue_6_floor_collision=PASS
```

For a found defect, record the failed check plus the defect:

```bash
python tools/record_kg001_g10_v118.py record \
  --check audio_audible=FAIL \
  --blocker issue_9_human_audibility=FAIL \
  --critical-bug "Audio remains inaudible in R1; F11 ZIP captured"
```

For a reproducible softlock use `--softlock "..."`. Notes can be appended with `--note "..."`.

The recorder rejects unknown check names and does not allow a finalized PASS result to be edited.

## 4. Finalize and validate

After every required check and blocker check has been recorded:

```bash
python tools/record_kg001_g10_v118.py finalize \
  --tester "YOUR_NAME"
```

Finalize automatically sets the manual result to:

- `PASS` only if every required check and blocker check is PASS and both defect lists are empty;
- otherwise `FAIL`.

It then validates the result against the exact test-build receipt.

A receipt-bound PASS may be promoted into canonical test evidence:

```bash
python tools/record_kg001_g10_v118.py finalize \
  --tester "YOUR_NAME" \
  --promote
```

Promotion writes:

- `data/tests/kg001_manual_sanity.json`
- `data/tests/kg001_manual_sanity_validation_v118.json`

Promotion is refused unless receipt-bound validation is literal PASS.

## 5. Release boundary

`kg001_status_v112.py` accepts G10 PASS only when:

- the promoted manual result is schema version 2 and status PASS;
- the promoted v118 validation is PASS;
- both manual artifacts are bound to the same commit as the promoted fresh-checkout evidence.

Even then, G10 alone does **not** automatically clear the recorded release-blocker flags or authorize `demo-known-good-001`. The final tag still requires every G00-G10 gate to be literal PASS, zero recorded release blockers, zero critical bugs and zero reproducible softlocks.
