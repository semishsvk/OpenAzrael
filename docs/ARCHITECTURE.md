# OpenAzrael Architecture

## Core pipeline

```text
Original Azrael assets / databases / executable
                  |
                  v
       Importers / decoders / forensic tools
                  |
                  v
          Clean OpenAzrael IR
                  |
       +----------+-----------+
       |                      |
       v                      v
 evidence/provenance      Godot runtime
                              |
                    +---------+---------+
                    |         |         |
                 Classic   Enhanced  Remastered
```

## Separation of concerns
### Source layer
Original demo/retail bytes, hashes, object names, coordinates, resources, database records and executable structures. Source facts are never rewritten to fit the runtime.

### Evidence layer
Reproducible parsers, forensic reports, cross-correlations, confidence labels, and provenance. This layer may contain hypotheses, but they must be clearly classified.

### OpenAzrael IR
Engine-neutral representation of rooms, objects, triggers, puzzle actions, world coordinates, audio references, and later NPC/dialogue/script data. The IR should preserve original identifiers whenever possible.

### Runtime layer
Godot 4 consumes IR and recovered assets. Runtime convenience values must remain distinguishable from recovered original constants.

## Presentation modes
- **Classic**: aims to reproduce original behavior/appearance as evidence allows.
- **Enhanced**: deterministic cleanup/upscale/reconstruction without changing authored composition or gameplay logic.
- **Remastered**: higher-fidelity presentation generated from the same underlying world/logic and original-conditioned art direction.

Presentation mode must never fork puzzle/world logic.

## Audio architecture target
```text
SoundDatabase / legacy_world_ir
          |
          +--> Classic renderer
          |
          +--> Enhanced spatial renderer
                    |
             AcousticGraph
             Rooms / Portals
             Occlusion / Reverb
             Ambient manager
```

Original sample identity, source XYZ and authored references remain evidence. Attenuation, pan, occlusion and reverb may be reconstructed only when evidence supports them; otherwise they stay implementation defaults or HOLD.

## Generalization rule
Every subsystem proven on the demo should be generalized only after validation. The demo is the reference testbed for the full-game framework.
