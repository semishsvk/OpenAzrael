# KG-001 G10 — manual sanity checklist

Run this only after G00-G09 are recorded PASS for the exact candidate commit.

Record the Godot version, candidate commit SHA, date and tester. Then perform a normal human launch and verify:

- project launches without a blocking error;
- mouse/look and movement controls behave normally;
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
- expected gameplay sounds are present to human perception;
- save/load round-trip preserves the tested demo state;
- no reproducible critical bug or softlock was observed.

If every item passes, create data/tests/kg001_manual_sanity.json with status PASS, the exact commit SHA and Godot version. Any reproducible critical bug or softlock records FAIL and blocks the tag.
