"""Unit tests for server/agent/loop.py (Step 5)."""
import unittest

from server.agent.loop import AgentLoop, TaskSession
from server.agent.meta_client import MetaClient
from server.config import PicoConfig
from server.contracts import (
    ErrorCode,
    RequestMessage,
    TaskState,
    ToolCallMessage,
    ToolResultMessage,
)


class FakeDesktopHelper:
    """Deterministic simulated helper providing synthetic files."""

    def __init__(self, should_fail: bool = False, no_candidates: bool = False):
        self.should_fail = should_fail
        self.no_candidates = no_candidates
        self.invocations = []

    def dispatch(self, call: ToolCallMessage) -> ToolResultMessage:
        self.invocations.append(call)
        if self.should_fail:
            return ToolResultMessage(
                contract_version=1,
                task_id=call.task_id,
                step_id=call.step_id,
                call_id=call.call_id,
                status="failed",
                error_code="permission_denied",
                error_message="Desktop helper denied access to requested path.",
            )

        if self.no_candidates:
            return ToolResultMessage(
                contract_version=1,
                task_id=call.task_id,
                step_id=call.step_id,
                call_id=call.call_id,
                status="succeeded",
                data={"candidates": []},
            )

        # Standard simulated candidate response
        return ToolResultMessage(
            contract_version=1,
            task_id=call.task_id,
            step_id=call.step_id,
            call_id=call.call_id,
            status="succeeded",
            data={
                "candidates": [
                    {
                        "candidate_id": "cand-proj-brief-001",
                        "name": "project-brief.txt",
                        "size_bytes": 1024,
                    }
                ]
            },
            evidence={"grant_id": "grant-mock-desktop-01", "simulated": True},
        )


class TestAgentLoop(unittest.TestCase):
    def setUp(self):
        self.cfg = PicoConfig(
            meta_api_key="",
            meta_model="muse-spark-1.3",
            meta_base_url="https://api.meta.ai/v1",
            max_model_turns=5,
            max_tool_calls=6,
            request_timeout_seconds=5.0,
            tool_timeout_seconds=5.0,
            task_deadline_seconds=30.0,
            spending_limit_dollars=5.0,
            mock_model=True,
        )
        self.client = MetaClient(self.cfg)

    def test_full_search_flow_to_needs_approval(self):
        """End-to-end: request -> search_documents -> candidate found -> needs_approval."""
        helper = FakeDesktopHelper()
        agent = AgentLoop(client=self.client, dispatcher=helper.dispatch, cfg=self.cfg)

        req = RequestMessage(
            contract_version=1,
            task_id="task-test-01",
            device_id="desktop-win-01",
            text="Find my project brief",
        )

        session = agent.start_task(req)
        self.assertEqual(session.state, TaskState.PLANNING)

        progress = agent.step(session)

        # Confirm step executed
        self.assertEqual(len(helper.invocations), 1)
        dispatched_call = helper.invocations[0]
        self.assertEqual(dispatched_call.tool, "search_documents")
        self.assertEqual(dispatched_call.task_id, "task-test-01")

        # Confirm transition to needs_approval
        self.assertEqual(session.state, TaskState.NEEDS_APPROVAL)
        self.assertEqual(progress.state, TaskState.NEEDS_APPROVAL)
        self.assertIsNotNone(session.pending_approval)
        self.assertEqual(session.pending_approval.candidate_id, "cand-proj-brief-001")
        self.assertEqual(session.pending_approval.candidate_name, "project-brief.txt")

    def test_failed_search_never_completes(self):
        """Hard rule: A failed search must never become a completed delivery."""
        helper = FakeDesktopHelper(should_fail=True)
        agent = AgentLoop(client=self.client, dispatcher=helper.dispatch, cfg=self.cfg)

        req = RequestMessage(
            contract_version=1,
            task_id="task-fail-01",
            device_id="desktop-win-01",
            text="Find brief",
        )

        session = agent.start_task(req)
        progress = agent.step(session)

        self.assertEqual(session.state, TaskState.FAILED)
        self.assertEqual(progress.state, TaskState.FAILED)
        self.assertEqual(session.error_code, ErrorCode.PERMISSION_DENIED.value)

    def test_empty_candidates_fails_with_no_match(self):
        helper = FakeDesktopHelper(no_candidates=True)
        agent = AgentLoop(client=self.client, dispatcher=helper.dispatch, cfg=self.cfg)

        req = RequestMessage(
            contract_version=1,
            task_id="task-empty-01",
            device_id="desktop-win-01",
            text="Find nonexistent file",
        )

        session = agent.start_task(req)
        progress = agent.step(session)

        self.assertEqual(session.state, TaskState.FAILED)
        self.assertEqual(progress.state, TaskState.FAILED)
        self.assertEqual(session.error_code, ErrorCode.NO_MATCH.value)

    def test_max_model_turns_bound_enforced(self):
        # Configure max 1 turn
        cfg_1_turn = PicoConfig(
            meta_api_key="",
            meta_model="muse-spark-1.3",
            meta_base_url="https://api.meta.ai/v1",
            max_model_turns=1,
            max_tool_calls=6,
            request_timeout_seconds=5.0,
            tool_timeout_seconds=5.0,
            task_deadline_seconds=30.0,
            spending_limit_dollars=5.0,
            mock_model=True,
        )
        agent = AgentLoop(client=MetaClient(cfg_1_turn), cfg=cfg_1_turn)
        req = RequestMessage(
            contract_version=1,
            task_id="task-bound-01",
            device_id="desktop-01",
            text="Find file",
        )
        session = agent.start_task(req)
        # Turn 1
        agent.step(session)
        # Turn 2 must trip limit
        progress = agent.step(session)
        self.assertEqual(session.state, TaskState.FAILED)
        self.assertEqual(session.error_code, ErrorCode.TIMEOUT.value)
        self.assertIn("Exceeded MAX_MODEL_TURNS", session.error_message)


if __name__ == "__main__":
    unittest.main()
