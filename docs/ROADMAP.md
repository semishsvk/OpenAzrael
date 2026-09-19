# OpenAzrael Roadmap

## Now
1. Reverse the 27-byte WORLD section-6 sound-action record and reader chain.
2. Map WORLD runtime fields against PUZZLES opcode-`0x28` operands/state tokens.
3. Extend action-by-action PUZZLES -> WORLD compilation evidence beyond token identity.
4. Preserve/extend evidence-aware Event IR.
5. Obtain a genuine original-runtime Classic audio parity capture.

## Next
- investigate indirect/computed WORLD-writer reachability only when new evidence justifies it;
- close remaining demo gameplay timing/motion semantics;
- widen demo validations into retail rooms/data;
- generalize import/runtime interfaces for full-game loading;
- keep Classic/Enhanced/Remastered renderers on shared gameplay/world IR.


## Localization / language packs
**Architecture approved; runtime implementation deferred until after the first KG-001 Candidate 1 runtime/manual cycle.**

1. Define String IR and immutable semantic-ID naming/migration rules.
2. Generate English fallback catalog plus `openazrael.pot`.
3. Add POT/PO tooling, glossary workflow and validators.
4. Implement `LocalizationManager` with manifest validation and non-overriding external PCK mounting.
5. Add pseudolocalization, overflow and Unicode/font coverage tests.
6. Build a small Slovak smoke-test pack.
7. Migrate demo strings away from hard-coded user-facing text.
8. Expand the separately prepared Slovak localization into the runtime pack format.
