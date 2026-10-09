# OpenAzrael C8 v403 — automatic one-shot Niamh activation

**Scope:** SOURCE-BOUND GODOT RUNTIME PASS / ORIGINAL VISUAL-TIMING FIDELITY HOLD.

Authority: the read-only ATDEMO `R.EXE` / `R7.XAF`, `ROOMS.DAT`,
`PUZZLES.DAT`, `NIAMH.ANI` and `NIAMH.DAT` corpus and the native
DOSBox-X animation oracle from the original game, including the private
original visible Niamh clip `visible_v397`.

The original authored transparent activation volume is `R7/zxactghost`.
The event graph `R7_NIAMH_ACTIVATE` is the sole implementation dispatch,
not a synthetic talk-on-click action. First encounter automatically:
* records the internal one-shot latch `R7NiamhActivated`;
* sets the source-derived `R7NiamhAZ` puzzle state;
* plays the NIAMH.XAF/NIAMH.ANI source animation `NOLOOP1` then `REST`;
* opens the canonical ATDEMO NIAMH.DAT `1A` conversation.
Leaving via source record `999` starts `NOLOOP2`.
The activation does **not** require a mouse click, keyboard `M`,
interact key, or explicitly speaking to Niamh.

The source `zxactghost` lies inside R7, not at its distant corridor
portal view. Thus room-identifier loading outside the source trigger does
not start the encounter early. Walking automatically into the authored
volume does. v403 closes a missing case in which the character initially
spawns/loads within the ghost volume: `initial_overlap=true` now turns
that first valid overlap into a real ENTER and reuses the original
one-shot graph. No other activation trigger had initial-overlap behavior
enabled. The existing `RoomManager` processing logic already supported
this scoped property and was not modified.

`kg001_niamh_auto_once_runner_v403.gd` executes real Godot portal
arrival → automatic ghost entry → source animation/conversation →
source `999` exit → room return (no replay) → canonical save/load
(no replay) → initial-inside-volume case (exactly one entry graph).
It uses no source-trigger input events. Godot v137/v209/v256 existing
tests remain mandatory, plus the whole Candidate 8 regression suite.

IMPORTANT HOLDS: exact original callback/trigger tick timing,
original Niamh animation frame-by-frame against Godot, real Miles
PCM audio (DOSBox-X original AVI audio currently silent) and
release safety remain unverified. This is not Candidate 8 acceptance,
not proof Niamh re-appears after exit, and not Retail promotion.
