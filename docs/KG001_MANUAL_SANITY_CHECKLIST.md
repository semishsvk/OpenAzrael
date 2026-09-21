# KG-001 G10 — manual sanity checklist

Run this only after G00-G09 are recorded PASS for the **exact candidate commit** and the Candidate 3 export receipt is PASS.

Record the Godot version, candidate commit SHA, export receipt SHA/hash, date and tester. G10 is a fixed-order verification, not a free-form playthrough.

## Stop-on-critical-failure rule

If the project cannot launch, the player falls through/support collision fails, either required R8 stair profile is not traversable both up and down, or a reproducible softlock occurs:

1. press **F11 before quitting** when possible;
2. preserve the generated diagnostic ZIP;
3. record G10 as **FAIL**;
4. stop the remaining long-route checks unless additional evidence is needed to characterize the defect.

Do not continue a full playthrough merely to accumulate more PASS items after a critical traversal failure.

## Fixed verification order

### 1. Launch and R1 physical sanity
- project launches without a blocking error;
- mouse/look and movement controls behave normally;
- at the historical R1 fall-through location, the player remains supported by the floor;
- walk forward and backward across the affected R1 floor area without sinking, falling through, teleporting, or becoming stuck.

### 2. R1 presentation and pickup sanity
- R1 keyhole cutout has transparent background with no visible pink/magenta key color;
- R1 keyhole is upright and matches the intended source orientation, not vertically inverted/upside down;
- rusty-tongs cutout has transparent background with no visible pink/magenta key color;
- R1 tongs can be picked up.

### 3. R1 -> R7 and well+tongs event
- Door 1 opens and R1 -> R7 traversal works;
- use the tongs on the well;
- the Well Key is produced/acquired through the intended interaction;
- the tongs are consumed/removed as intended;
- **979TONGS.WAV** is audibly triggered to human perception;
- no interaction softlock or duplicated/incorrect inventory state occurs.

### 4. R7 progression and return
- R7 lever -> wheel -> lever sequence drains the R8 bath;
- expected R7 ambient/gameplay sounds are audible;
- R7 -> R1 return works and persistent state is preserved;
- Door 2 unlocks with the Well Key and R1 -> R8 traversal works.

### 5. R8 critical stair traversal
Test both real Candidate 3 stair profiles with ordinary player controls, without debug movement or teleport assistance:
- `step011__mesh`: traverse **up and down** successfully;
- `stairs__STAIR2`: traverse **up and down** successfully;
- no fall-through, snag/softlock, oscillation, impossible step, or forced jump workaround is accepted.

A failure of either stair profile is a **critical G10 FAIL** and triggers the stop-on-critical-failure rule.

### 6. R8 puzzle route
- lens is obtainable only after bath drain;
- lens can be placed on the Bible;
- optical mechanism activates from the intended zxplate zone;
- secret door opens and the Shield becomes obtainable;
- taking the Shield completes the demo.

### 7. Audio and cutout sweep
- expected ambient and triggered gameplay sounds are present to human perception across the tested R1/R7/R8 route;
- no visible magenta key-color rectangles/halos remain on other `#` cutout textures encountered during the route.

### 8. Persistence
- save/load round-trip preserves the tested demo state without duplicating inventory, reverting puzzle state, or breaking room progression.

### 9. Diagnostics
- press **F11**;
- verify that a source-safe diagnostic ZIP is created;
- verify that F11 does not change the observed gameplay state.

### 10. Final acceptance
- no reproducible critical bug was observed;
- no reproducible softlock was observed;
- every required item above is PASS.

If every item passes, create `data/tests/kg001_manual_sanity.json` with status `PASS`, the exact candidate commit SHA, Godot version and export-receipt identity. Any required-check failure records `FAIL` and blocks `demo-known-good-001`.
