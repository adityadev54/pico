import time
import unittest

from server.contract import (
    ContractError,
    validate_approval,
    validate_envelope,
    validate_progress,
    validate_tool_call,
    validate_tool_result,
    check_transition,
)


def base_call(**over):
    msg = {
        "type": "tool_call",
        "contract_version": 1,
        "task_id": "task-1",
        "step_id": "step-1",
        "call_id": "call-1",
        "tool": "search_documents",
        "arguments": {"query": "brief"},
        "idempotency_key": "task-1:step-1",
        "deadline_seconds": 30,
    }
    msg.update(over)
    return msg


class ContractTests(unittest.TestCase):
    def test_envelope_requires_version_task_type(self):
        with self.assertRaises(ContractError):
            validate_envelope({"type": "request", "contract_version": 2, "task_id": "t"})
        with self.assertRaises(ContractError):
            validate_envelope({"type": "request", "contract_version": 1})
        self.assertEqual(
            validate_envelope({"type": "request", "contract_version": 1, "task_id": "t"})["type"],
            "request",
        )

    def test_tool_call_validates_tool_deadline_args(self):
        validate_tool_call(base_call())
        with self.assertRaises(ContractError):
            validate_tool_call(base_call(tool="wipe_disk"))
        with self.assertRaises(ContractError):
            validate_tool_call(base_call(deadline_seconds=500))
        with self.assertRaises(ContractError):
            validate_tool_call(base_call(arguments={}))

    def test_transfer_requires_candidate_and_approval(self):
        validate_tool_call(base_call(
            tool="transfer_selected_file",
            arguments={"candidate_id": "c1", "approval_id": "a1"},
        ))
        with self.assertRaises(ContractError):
            validate_tool_call(base_call(
                tool="transfer_selected_file", arguments={"candidate_id": "c1"},
            ))

    def test_filesystem_and_process_calls_validate(self):
        validate_tool_call(base_call(
            tool="fs_write", arguments={"path": "n.txt", "content": "hi"},
        ))
        validate_tool_call(base_call(
            tool="process_run", arguments={"argv_json": "[\"echo\"]"},
        ))
        with self.assertRaises(ContractError):
            validate_tool_call(base_call(
                tool="fs_write", arguments={"path": "n.txt"},
            ))

    def test_failed_result_needs_stable_code(self):
        validate_tool_result({
            "type": "tool_result", "contract_version": 1, "task_id": "t",
            "step_id": "s", "call_id": "c", "status": "succeeded", "data": {},
        })
        with self.assertRaises(ContractError):
            validate_tool_result({
                "type": "tool_result", "contract_version": 1, "task_id": "t",
                "step_id": "s", "call_id": "c", "status": "failed",
                "error": {"code": "mystery"},
            })

    def test_approval_binds_owner_task_version_expiry(self):
        approval = {
            "owner": "u1", "task_id": "t1", "task_version": 1,
            "approval_id": "a1", "operation": "transfer:c1",
            "candidate_id": "c1", "expires_at": time.time() + 60,
        }
        validate_approval(dict(approval), "u1", "t1", 1)
        with self.assertRaises(ContractError):
            validate_approval(dict(approval), "u2", "t1", 1)
        with self.assertRaises(ContractError):
            validate_approval({**approval, "expires_at": time.time() - 1}, "u1", "t1", 1)

    def test_progress_rejects_secrets_and_paths(self):
        validate_progress({
            "type": "progress", "contract_version": 1, "task_id": "t",
            "state": "needs_approval", "message": "Select a file.",
        })
        with self.assertRaises(ContractError):
            validate_progress({
                "type": "progress", "contract_version": 1, "task_id": "t",
                "state": "executing", "message": "token Bearer abc123",
            })

    def test_terminal_states_never_leave(self):
        check_transition("executing", "verifying")
        with self.assertRaises(ContractError):
            check_transition("cancelled", "executing")
        with self.assertRaises(ContractError):
            check_transition("completed", "failed")


if __name__ == "__main__":
    unittest.main()
