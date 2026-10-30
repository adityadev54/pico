import unittest

from server.agent.loop import AgentLoop
from server.contract import ContractError


def search_call(task_id="task-1"):
    return {
        "type": "tool_call", "contract_version": 1, "task_id": task_id,
        "step_id": "step-search", "call_id": "call-search",
        "tool": "search_documents", "arguments": {"query": "brief"},
        "idempotency_key": f"{task_id}:step-search", "deadline_seconds": 30,
    }


def transfer_call(task_id="task-1"):
    return {
        "type": "tool_call", "contract_version": 1, "task_id": task_id,
        "step_id": "step-transfer", "call_id": "call-transfer",
        "tool": "transfer_selected_file",
        "arguments": {"candidate_id": "c1", "approval_id": "a1"},
        "idempotency_key": f"{task_id}:step-transfer", "deadline_seconds": 30,
    }


class AgentLoopTests(unittest.TestCase):
    def test_first_integration_search_then_approval(self):
        loop = AgentLoop()
        task = loop.start("task-1", "Find my project brief")
        task["owner"] = "u1"
        loop.plan(task, search_call())
        self.assertEqual(task["status"], "executing")
        loop.on_tool_result(task, {
            "type": "tool_result", "contract_version": 1, "task_id": "task-1",
            "step_id": "step-search", "call_id": "call-search",
            "status": "succeeded",
            "data": {"candidates": [{"candidate_id": "c1", "name": "brief.txt"}]},
        })
        self.assertEqual(task["status"], "needs_approval")
        self.assertEqual(len(task["candidates"]), 1)

    def test_failed_search_never_completes(self):
        loop = AgentLoop()
        task = loop.start("task-1", "Find it")
        task["owner"] = "u1"
        loop.plan(task, search_call())
        loop.on_tool_result(task, {
            "type": "tool_result", "contract_version": 1, "task_id": "task-1",
            "step_id": "step-search", "call_id": "call-search",
            "status": "failed", "error": {"code": "no_match", "message": "none"},
        })
        self.assertEqual(task["status"], "failed")

    def test_transfer_requires_approval(self):
        loop = AgentLoop()
        task = loop.start("task-1", "Send it")
        task["owner"] = "u1"
        with self.assertRaises(ContractError):
            loop.plan(task, transfer_call())

    def test_cancellation_wins_over_late_result(self):
        loop = AgentLoop()
        task = loop.start("task-1", "Find it")
        task["owner"] = "u1"
        loop.plan(task, search_call())
        loop.cancel(task)
        self.assertEqual(task["status"], "cancelled")
        with self.assertRaises(ContractError):
            loop.on_tool_result(task, {
                "type": "tool_result", "contract_version": 1, "task_id": "task-1",
                "step_id": "step-search", "call_id": "call-search",
                "status": "succeeded", "data": {"candidates": []},
            })

    def test_step_limits_stop_runaway(self):
        loop = AgentLoop(max_steps=1, max_model_calls=1)
        task = loop.start("task-1", "Find it")
        task["owner"] = "u1"
        loop.plan(task, search_call())
        # Second planner turn exceeds model budget and fails closed.
        task.pop("pending_call", None)
        task["status"] = "executing"
        out = loop.plan(task, search_call())
        self.assertEqual(out["status"], "failed")

    def test_clarification_carries_question_id_and_version(self):
        loop = AgentLoop()
        task = loop.start("task-1", "???")
        task["owner"] = "u1"
        loop.plan(task, None, question="Which folder?")
        self.assertEqual(task["status"], "needs_clarification")
        self.assertIn("question_id", task["question"])
        self.assertEqual(task["question"]["task_version"], 1)


if __name__ == "__main__":
    unittest.main()
