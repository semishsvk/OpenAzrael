# OpenAzrael repository agent policy

## Global single-writer invariant — mandatory

OpenAzrael uses one global writer lease for all mutating project work.

Before **any** repository mutation, build, validation run, workflow dispatch, merge, release operation, generated artifact commit, or integration-branch write:

1. Read `.openazrael/ACTIVE_WORK.json` from branch `coordination/single-writer`.
2. If `status` is `active` and the `lease_id` is not the lease assigned to your current task, **STOP before doing any work that can change or execute project state**.
3. Do not create a competing branch, commit, build, validation run, workflow run, merge, or artifact. Read-only inspection is allowed only to report the current owner/status.
4. Never auto-expire or steal a lease. A stale lease may be taken over only after explicit user authorization and repository-state reconciliation.
5. To acquire an idle lease, re-read the lock file and update it using its current blob SHA. A SHA/conflict failure means another task won the lease; stop rather than retrying with force.
6. Every commit to the authoritative integration branch must contain the trailer:
   `OpenAzrael-Writer-Lease: <lease_id>`
7. Never force-update the authoritative integration branch.
8. Release the lease only after all work/processes are stopped, the tested tree is known, and repository state is synchronized. Release by updating the same lock file to `status: idle`; do not delete the coordination branch.

The authoritative lock location is:

- branch: `coordination/single-writer`
- file: `.openazrael/ACTIVE_WORK.json`

This policy is intentionally global, not per-subsystem: Audio Lab, Texture Lab, PPPV, video, localization, tooling, build, validation, and release work all share the same writer lease.

## Fly-through video movement and framing — mandatory

Every future OpenAzrael fly-through/proof video must follow these movement and camera rules unless the user explicitly overrides them for that video:

1. Use the shortest practical **valid physical route** between required checkpoints. Do not introduce sightseeing detours or unnecessary lateral movement.
2. Preserve production collision and traversal semantics. No teleporting, noclip, fake transitions, or scripted shortcuts may be used to make the route look shorter.
3. When an obstacle such as a boulder, column, wall projection, furniture, or other blocking geometry must be avoided, steer around it with one smooth natural arc and rejoin the shortest route. Do not zig-zag, oscillate, or make abrupt correction turns.
4. Movement and camera rotation must be visually continuous: no jerky side-to-side steering, rapid yaw sign flipping, snap rotations, or repeated micro-corrections. Prefer anticipatory turns and smoothly blended arcs.
5. For every gameplay action or pickup (for example rusty tongs, scrolls, key, lens, shield, switches, doors, well interactions, or equivalent retail objects), center the relevant interaction target in the view before executing the action.
6. Hold a stable, readable centered framing for the action itself so the resulting animation/state change is clearly visible in the proof footage.
7. After the action completes, smoothly return pitch to the normal horizontal viewing position before resuming traversal. Do not continue walking with the camera left tilted markedly up or down.
8. After interaction framing, smoothly reacquire the next travel heading; do not snap directly from the object view to the next waypoint.
9. Cinematic smoothing may improve presentation only. It must never hide traversal failures, collision contacts, missed interaction probes, invalid states, or softlocks.
10. The proof route must remain compatible with the same production movement/collision/interaction logic used by PPPV validation. A prettier capture must not use a different gameplay path model than the validated one.

Priority for fly-through path selection:
**physical correctness -> required action coverage -> shortest valid route -> natural obstacle avoidance -> smooth camera presentation.**
