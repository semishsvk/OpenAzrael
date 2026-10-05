#!/usr/bin/env python3
"""CAS-backed OpenAzrael writer lifecycle; no time-based lock stealing."""
import argparse
import base64
import copy
import datetime
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import uuid

REPO = "semishsvk/OpenAzrael"
BRANCH = "coordination/single-writer"
LOCK = ".openazrael/ACTIVE_WORK.json"


class Conflict(RuntimeError):
    pass


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def gh(args, payload=None):
    result = subprocess.run(["gh", "api", *args], input=json.dumps(payload) if payload is not None else None,
                            text=True, capture_output=True)
    if result.returncode:
        # Do not print credentials or API input. CAS failures never force-retry.
        raise Conflict("GitHub read/write failed; re-read state on the next scheduled attempt")
    return json.loads(result.stdout)


class Store:
    def read(self):
        blob = gh([f"repos/{REPO}/contents/{LOCK}?ref={BRANCH}"])
        return json.loads(base64.b64decode(blob["content"])), blob["sha"]

    def write(self, state, sha):
        return gh(["--method", "PUT", f"repos/{REPO}/contents/{LOCK}", "--input", "-"], {
            "branch": BRANCH, "sha": sha,
            "message": "coordination: writer lifecycle transition",
            "content": base64.b64encode((json.dumps(state, indent=2) + "\n").encode()).decode(),
        })


def transition(state, action, thread, lease, dependency=None, receipt=None):
    """Pure transition; callers must use the exact blob SHA from the read."""
    out = copy.deepcopy(state)
    out.setdefault("queue", [])
    out.setdefault("active_run", None)
    out["schema_version"] = 2
    own = out.get("status") == "active" and out.get("owner_thread_id") == thread and out.get("lease_id") == lease
    ticket = next((t for t in out["queue"] if t["thread_id"] == thread and t["lease_id"] == lease), None)
    if action in ("acquire", "ready", "wait"):
        if ticket is None and not own:
            ticket = {"thread_id": thread, "lease_id": lease, "enqueued_at": now(), "state": "ready"}
            out["queue"].append(ticket)
        if action == "wait":
            if not dependency:
                raise Conflict("wait requires a dependency or reason")
            if own:
                _release(out, receipt)
                ticket = {"thread_id": thread, "lease_id": lease, "enqueued_at": now(), "state": "waiting"}
                out["queue"].append(ticket)
            ticket["state"] = "waiting"
            ticket["dependency"] = dependency
            return out, "WAITING_DEPENDENCY"
        if action == "ready":
            if not receipt:
                raise Conflict("ready requires evidence that the dependency completed")
            if own:
                return out, "OWNED"
            ticket["state"] = "ready"
            ticket["dependency_receipt"] = receipt
        elif ticket and ticket.get("state") == "waiting":
            return out, "WAITING_DEPENDENCY"
        if own:
            out["last_seen_at"] = now()
            return out, "OWNED"
        if out.get("status") not in ("idle", "active"):
            raise Conflict("Unknown lock state")
        if out.get("status") == "active":
            return out, "QUEUED"
        first = next((t for t in out["queue"] if t["state"] == "ready"), None)
        if first is not ticket:
            return out, "QUEUED"
        out.update(status="active", lease_id=lease, owner_thread_id=thread,
                   owner=thread, acquired_at=now(), last_seen_at=now(), active_run=None)
        out["queue"].remove(ticket)
        return out, "ACQUIRED"
    if action == "cancel":
        if own:
            raise Conflict("Release an owned lease with a reconciliation receipt before cancelling")
        out["queue"] = [t for t in out["queue"] if t is not ticket]
        return out, "CANCELLED"
    if not own:
        raise Conflict("Owner thread AND lease must match; a foreign or legacy lease is never stolen")
    if action == "renew":
        out["last_seen_at"] = now()
        return out, "OWNED"
    if action == "release":
        _release(out, receipt)
        return out, "RELEASED"
    raise Conflict("Unknown transition")


def _release(state, receipt):
    if state.get("active_run"):
        raise Conflict("A registered run is active; finish or reconcile it before release")
    if not receipt:
        raise Conflict("Release requires a reconciliation receipt")
    required = ("head", "git_status", "remote_head", "sync_state", "task_processes_stopped")
    if any(key not in receipt for key in required) or receipt["task_processes_stopped"] is not True:
        raise Conflict("Receipt must record HEAD, working tree, remote HEAD, sync state and stopped task processes")
    state.update(status="idle", released_at=now(), reconciliation=receipt)


def apply(store, action, thread, lease, dependency=None, receipt=None):
    state, sha = store.read()
    updated, status = transition(state, action, thread, lease, dependency, receipt)
    store.write(updated, sha)  # One CAS attempt. Never overwrite a winner.
    return status, updated


def owned(state, thread, lease):
    return state.get("status") == "active" and state.get("owner_thread_id") == thread and state.get("lease_id") == lease


def run(store, thread, lease, command, cwd):
    """Run a foreground process while holding a server-side active_run claim."""
    if not command:
        raise Conflict("run requires an executable and arguments after --")
    state, sha = store.read()
    if not owned(state, thread, lease) or state.get("active_run"):
        raise Conflict("Writer is foreign or another registered run is active")
    run_id = str(uuid.uuid4())
    state["active_run"] = {"run_id": run_id, "host": socket.gethostname(), "supervisor_pid": os.getpid(),
                           "started_at": now(), "cwd": str(Path(cwd).resolve()), "command": command}
    store.write(state, sha)
    try:
        child = subprocess.Popen(command, cwd=cwd)
        try:
            code = child.wait()
        except BaseException:
            # Do not free a lock while the process continues in the background.
            child.terminate()
            try:
                child.wait(timeout=15)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
            raise
    finally:
        current, current_sha = store.read()
        if not owned(current, thread, lease) or (current.get("active_run") or {}).get("run_id") != run_id:
            raise Conflict("Run ownership changed; preserve lock and reconcile manually")
        current["active_run"] = None
        current["last_seen_at"] = now()
        store.write(current, current_sha)
    return code


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=["status", "acquire", "ready", "wait", "renew", "release", "cancel", "run"])
    ap.add_argument("--thread")
    ap.add_argument("--lease")
    ap.add_argument("--dependency")
    ap.add_argument("--receipt", type=Path)
    ap.add_argument("--cwd", default=".")
    # Split executable arguments explicitly so lifecycle options remain parseable.
    argv = sys.argv[1:]
    extra = []
    if "--" in argv:
        boundary = argv.index("--")
        argv, extra = argv[:boundary], argv[boundary + 1:]
    args = ap.parse_args(argv)
    try:
        store = Store()
        if args.action == "status":
            state, sha = store.read()
            print(json.dumps({"blob_sha": sha, "state": state}, indent=2))
            return 0
        if not args.thread or not args.lease:
            raise Conflict("thread and lease are required")
        if args.action == "run":
            return run(store, args.thread, args.lease, extra, args.cwd)
        receipt = json.loads(args.receipt.read_text(encoding="utf-8")) if args.receipt else None
        status, state = apply(store, args.action, args.thread, args.lease, args.dependency, receipt)
        print(json.dumps({"status": status, "owner_thread_id": state.get("owner_thread_id"), "lease_id": state.get("lease_id")}))
        return 75 if status in ("QUEUED", "WAITING_DEPENDENCY") else 0
    except (Conflict, OSError, ValueError) as error:
        print(json.dumps({"status": "BLOCKED", "reason": str(error)}))
        return 75


if __name__ == "__main__":
    sys.exit(main())
