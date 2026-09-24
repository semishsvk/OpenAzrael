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
