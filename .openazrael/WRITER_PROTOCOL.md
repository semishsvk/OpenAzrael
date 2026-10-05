# OpenAzrael writer lifecycle v2

This protocol supplements the integration branch AGENTS.md. The authoritative lock remains
`.openazrael/ACTIVE_WORK.json` on `coordination/single-writer`. Integration source and the
Candidate 6 target HEAD are unchanged by this coordination repair.

## Identity and scheduling

- A lease belongs to `owner_thread_id` (the Codex/ChatGPT chat ID) and `lease_id` together.
  A resumed turn or heartbeat of the same chat retains this identity. Do not request takeover
  approval merely because the execution turn changed.
- A foreign active lease is a scheduling condition: enqueue once and retry on a later wakeup.
  Do not ask the user to approve taking over a live owner. Never force a CAS update.
- `queue` is ordered. Only the first ready ticket may acquire an idle lease. Waiting tickets
  do not block independent ready work. Requests are deduplicated by chat and lease.
- A dependency wait releases the writer and records a waiting ticket. It does not hold an
  active lease for hours. `ready` requires a receipt for actual dependency completion;
  an idle chat or finished turn alone is not completion evidence.
- On completion, failure, pause, or handoff: stop task-owned processes, record repository
  HEAD, working-tree status, remote HEAD and sync disposition, then release. Unpushed work
  must be identified and preserved; do not push unrelated commits just to clear a lock.
- No expiration steals a lease. `last_seen_at` is diagnostic. An abandoned legacy lease
  or crash with an unresolved run requires reconciliation and the existing takeover policy.

## One guarded writer run

Use `lease.py run` for foreground validation, capture, build, export and other mutating commands.
It verifies both ownership fields and atomically registers `active_run` before spawning the process.
A second run, even from another turn of the same chat, cannot start while that claim exists.
Release and dependency wait refuse a registered active run. Foreground completion removes only
the matching run claim. A supervisor crash leaves the claim closed for reconciliation.

The executable must not detach/background child work. If it creates background processes,
wait for and stop those processes before clearing ownership. This guard coordinates cooperative
agents; it does not intercept arbitrary external tools. Every agent must honor this protocol
and the original AGENTS.md single-writer invariant.

## Installation and use on HomePC

Canonical code and tests live on the coordination branch:
`.openazrael/lease.py` and `.openazrael/test_lease.py`.
Installed copy: `F:\OpenRemaster\OpenAzrael\.runtime\work\coordination\lease.py`.
Python: `F:\OpenRemaster\OpenAzrael\.venv\Scripts\python.exe`.
GitHub authentication comes from `gh`; the script never reads or prints a token.

Use the same `--thread CHAT_ID --lease LEASE_ID` for all lifecycle operations:

```text
python lease.py status
python lease.py acquire --thread CHAT_ID --lease LEASE_ID
python lease.py run --thread CHAT_ID --lease LEASE_ID --cwd CHECKOUT -- EXECUTABLE ARGUMENTS
python lease.py wait --thread CHAT_ID --lease LEASE_ID --dependency DEPENDENCY_CHAT --receipt reconciliation.json
python lease.py ready --thread CHAT_ID --lease LEASE_ID --receipt dependency-completion.json
python lease.py release --thread CHAT_ID --lease LEASE_ID --receipt reconciliation.json
```

Exit 75 means queued/waiting or fail-closed: read the result and reschedule; do not force.
Exit 0 means the lifecycle transition succeeded. A guarded run returns the executable exit code.
`status` is read-only. Reconciliation receipts require `head`, `git_status`, `remote_head`,
`sync_state`, and `task_processes_stopped: true`. Dependency receipts must cite the completed
phase's actual evidence, not a guessed result.

## Verification

Nine isolated lifecycle tests cover competing CAS acquisitions, deduplication/FIFO,
same-chat resume, dependency wait/reacquisition, refusing legacy/foreign/expired leases,
active-run exclusion, release reconciliation, child exit and failed launch cleanup.
Run `python -m unittest discover -s coordination -v` against the installed test directory.
These are coordination tests, not Candidate 6 gameplay or visual evidence.
