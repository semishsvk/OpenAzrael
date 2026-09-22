# KG-001 Candidate 4 release criteria

Candidate 4 is the first OpenAzrael demo candidate intended to be fully playable
end to end rather than a partial diagnostic build.

It MUST NOT be exported as Candidate 4 unless the exact Git HEAD passes the
asset-backed runtime preflight and every required evidence artifact is bound to
that same source and runtime asset set.

## Geometry

R1, R7 and R8 must use the complete restored demo geometry. The importer must
match the canonical source counts, and the v122-v131 fidelity stack must pass:
geometry/render parity, object visibility, materials/textures, transforms,
graphical census, reachable visibility, portal geometry, interaction
reachability and the fail-closed room forensic report. No visible authored
object may be silently omitted. Any required walkable surface without working
collision is critical.

## Gameplay

The synthetic player must traverse the demo through production player input and
production interactions. All four required room transitions, both R8 stair
profiles, the R1 former Object02 failure point, every required puzzle effect,
save/load and the successful end-of-demo state are release gates. PPPV v2 must
produce at least two identical guarded end-to-end runs. Required transition
failure or a reproducible softlock is critical.

## Audio

Candidate 4 requires the canonical 30/30 WAV demo corpus. Restore validates each
source file against the canonical SHA-256 in `data/audio/legacy_world_ir.json`
and binds the resulting runtime file hashes in a local receipt. Ambient and
triggered-event runtime tests remain mandatory, followed by human audibility in
G10.

The demo package also contains 24 XMI music assets. Candidate 4 is fail-closed
until forensic route evidence proves one of two states: the required XMI music
is supported and runtime-tested, or XMI music is proven not to be used on the
accepted Candidate 4 demo route. Merely having the XMI files in the package is
not sufficient evidence either way.

## Release rule

Candidate 4 requires zero known critical bugs, zero reproducible softlocks,
zero failed mandatory gates, clean-checkout reproducibility, exact-head asset
binding, guarded export/startup smoke, and a complete manual G10 run on the
exact exported EXE/PCK pair.
