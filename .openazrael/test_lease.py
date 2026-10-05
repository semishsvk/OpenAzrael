import copy
import unittest
from unittest.mock import patch

import lease


RECEIPT = {"head": "bcc196103ddf137d05cc6f2d6724d9fe5bd0b8bc", "git_status": "clean",
           "remote_head": "55207b3b666a91970c7c5008892e00ae91ce9447",
           "sync_state": "local ahead 11; no push during coordination repair", "task_processes_stopped": True}


class MemoryStore:
    def __init__(self, state=None):
        self.state = state or {"status": "idle", "queue": []}
        self.sha = 0

    def read(self):
        return copy.deepcopy(self.state), self.sha

    def write(self, state, sha):
        if sha != self.sha:
            raise lease.Conflict("CAS conflict")
        self.state = copy.deepcopy(state)
        self.sha += 1


class LifecycleTests(unittest.TestCase):
    def test_competing_acquire_has_one_winner(self):
        store = MemoryStore()
        state, sha = store.read()
        first, _ = lease.transition(state, "acquire", "chat-a", "lease-a")
        second, _ = lease.transition(state, "acquire", "chat-b", "lease-b")
        store.write(first, sha)
        with self.assertRaises(lease.Conflict):
            store.write(second, sha)
        status, state = lease.apply(store, "acquire", "chat-b", "lease-b")
        self.assertEqual(status, "QUEUED")
        self.assertEqual(state["owner_thread_id"], "chat-a")
        self.assertEqual(len(state["queue"]), 1)

    def test_wait_releases_and_requires_dependency_completion(self):
        store = MemoryStore()
        lease.apply(store, "acquire", "a", "a")
        status, state = lease.apply(store, "wait", "a", "a", "framework-phase2", RECEIPT)
        self.assertEqual(status, "WAITING_DEPENDENCY")
        self.assertEqual(state["status"], "idle")
        self.assertEqual(lease.apply(store, "acquire", "a", "a")[0], "WAITING_DEPENDENCY")
        self.assertEqual(lease.apply(store, "acquire", "b", "b")[0], "ACQUIRED")
        lease.apply(store, "release", "b", "b", receipt=RECEIPT)
        with self.assertRaises(lease.Conflict):
            lease.apply(store, "ready", "a", "a")
        self.assertEqual(lease.apply(store, "ready", "a", "a", receipt={"phase2": "PASS", "evidence": "receipt.json"})[0], "ACQUIRED")

    def test_resume_uses_stable_chat_identity(self):
        store = MemoryStore()
        lease.apply(store, "acquire", "a", "a")
        self.assertEqual(lease.apply(store, "acquire", "a", "a")[0], "OWNED")
        with self.assertRaises(lease.Conflict):
            lease.apply(store, "release", "b", "a", receipt=RECEIPT)

    def test_ready_queue_is_fifo_and_repeated_request_is_deduplicated(self):
        store = MemoryStore()
        lease.apply(store, "acquire", "a", "a")
        lease.apply(store, "acquire", "b", "b")
        lease.apply(store, "acquire", "c", "c")
        lease.apply(store, "acquire", "b", "b")
        self.assertEqual(len(store.state["queue"]), 2)
        lease.apply(store, "release", "a", "a", receipt=RECEIPT)
        self.assertEqual(lease.apply(store, "acquire", "c", "c")[0], "QUEUED")
        self.assertEqual(lease.apply(store, "acquire", "b", "b")[0], "ACQUIRED")

    def test_release_requires_stopped_processes_and_reconciled_state(self):
        store = MemoryStore()
        lease.apply(store, "acquire", "a", "a")
        for receipt in (None, {}, {**RECEIPT, "task_processes_stopped": False}):
            with self.assertRaises(lease.Conflict):
                lease.apply(store, "release", "a", "a", receipt=receipt)
        store.state["active_run"] = {"run_id": "still-running"}
        with self.assertRaises(lease.Conflict):
            lease.apply(store, "release", "a", "a", receipt=RECEIPT)

    def test_legacy_and_expired_foreign_lease_are_never_stolen(self):
        store = MemoryStore({"status": "active", "lease_id": "legacy", "expires": "2000-01-01"})
        self.assertEqual(lease.apply(store, "acquire", "a", "a")[0], "QUEUED")
        self.assertEqual(store.state["lease_id"], "legacy")

    def test_guard_rejects_foreign_and_overlapping_run(self):
        store = MemoryStore()
        lease.apply(store, "acquire", "a", "a")
        with patch("lease.subprocess.Popen") as process:
            with self.assertRaises(lease.Conflict):
                lease.run(store, "b", "b", ["bad-command"], ".")
            store.state["active_run"] = {"run_id": "occupied"}
            with self.assertRaises(lease.Conflict):
                lease.run(store, "a", "a", ["bad-command"], ".")
            process.assert_not_called()

    def test_guard_registers_run_and_clears_only_after_exit(self):
        store = MemoryStore()
        lease.apply(store, "acquire", "a", "a")
        def start(*args, **kwargs):
            self.assertIsNotNone(store.state["active_run"])
            child = unittest.mock.Mock()
            child.wait.return_value = 7
            return child
        with patch("lease.subprocess.Popen", side_effect=start):
            self.assertEqual(lease.run(store, "a", "a", ["test"], "."), 7)
        self.assertIsNone(store.state["active_run"])

    def test_failed_launch_clears_claim(self):
        store = MemoryStore()
        lease.apply(store, "acquire", "a", "a")
        with patch("lease.subprocess.Popen", side_effect=OSError("missing executable")):
            with self.assertRaises(OSError):
                lease.run(store, "a", "a", ["test"], ".")
        self.assertIsNone(store.state["active_run"])


if __name__ == "__main__":
    unittest.main()
