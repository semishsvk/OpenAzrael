# KG-001 Proof Capture v152

v152 makes proof-video generation fail closed on the class of failures seen during the human-style demo capture.

## New mandatory gates

1. Single writer: an atomic capture lock is acquired before stale outputs are touched.
2. Process collision check: another Godot Movie Maker process for the same OpenAzrael workspace aborts the run.
3. Output identity monitoring: after the raw AVI appears, its device/inode identity must not change.
4. Monotonic output: AVI size may only grow during capture. Unlink, replacement or shrink aborts the run.
5. Gameplay identity: the captured PPPV run must still evaluate PASS and match the accepted deterministic gameplay state.
6. Audio identity: the same runtime capture must contain decodable, non-silent audio.
7. Temporal visual QA: the final MP4 is decoded at low resolution and checked for p99 frame-difference, p99 luma jumps and isolated one-frame flash signatures.
8. Fail closed: any visual stability failure deletes/rejects the final MP4 instead of publishing it.

The temporal audit stores the worst hotspot timestamps in the receipt so a reviewer can immediately inspect the most suspicious frames.

These gates are generic in tools/remaster_framework/capture_safety.py so future remaster projects can reuse them.

This does not replace manual G10. It prevents a technically successful but visually broken capture from being accepted as proof.
