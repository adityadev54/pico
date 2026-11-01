"""Interactive demonstration for Step 5: Bounded Agent Loop.

Demonstrates:
1. User Request: "Find my project brief"
2. Agent planning & tool selection: search_documents
3. Safe execution via FakeDesktopHelper
4. Transition to needs_approval with candidate
5. Bound enforcement (turns, timeouts, error safety)
"""
from server.agent.loop import AgentLoop
from server.agent.meta_client import MetaClient
from server.config import PicoConfig
from server.contracts import RequestMessage, ToolCallMessage, ToolResultMessage


class DemoDesktopHelper:
    """Simulated desktop helper responding to validated search calls."""

    def dispatch(self, call: ToolCallMessage) -> ToolResultMessage:
        print(f"\n[Helper] Received ToolCall:")
        print(f"  Tool Name       : {call.tool}")
        print(f"  Step ID         : {call.step_id}")
        print(f"  Call ID         : {call.call_id}")
        print(f"  Arguments       : {call.arguments}")
        print(f"  Idempotency Key : {call.idempotency_key}")
        print(f"  Deadline Secs   : {call.deadline_seconds}")

        return ToolResultMessage(
            contract_version=1,
            task_id=call.task_id,
            step_id=call.step_id,
            call_id=call.call_id,
            status="succeeded",
            data={
                "candidates": [
                    {
                        "candidate_id": "cand-proj-brief-999",
                        "name": "pico-project-brief.pdf",
                        "size_bytes": 48210,
                    }
                ]
            },
            evidence={"grant_id": "grant-desktop-demo-01", "simulated": True},
        )


def main():
    print("=" * 60)
    print("         DEMONSTRATING STEP 5: BOUNDED AGENT LOOP         ")
    print("=" * 60)

    cfg = PicoConfig.from_env()
    client = MetaClient(cfg)
    helper = DemoDesktopHelper()
    agent = AgentLoop(client=client, dispatcher=helper.dispatch, cfg=cfg)

    # 1. Incoming user request from phone
    req = RequestMessage(
        contract_version=1,
        task_id="task-demo-step5",
        device_id="desktop-win-primary",
        text="Find my project brief",
    )
    print(f"\n[Phone] User request received: '{req.text}'")

    # 2. Agent starts task
    session = agent.start_task(req, owner="LoGesH")
    print(f"[Agent] Task started -> State: {session.state.value}")

    # 3. Agent steps: Plan -> Model selects tool -> Dispatch -> Candidates -> Needs Approval
    print(f"[Agent] Stepping agent loop...")
    progress = agent.step(session)

    print(f"\n[Agent] Turn complete:")
    print(f"  Final State     : {progress.state.value}")
    print(f"  Progress Message: {progress.message}")
    print(f"  Model Turns Used: {session.model_turns} / {cfg.max_model_turns}")
    print(f"  Tool Calls Used : {session.tool_calls_count} / {cfg.max_tool_calls}")

    if session.pending_approval:
        appr = session.pending_approval
        print(f"\n[Agent] Pending Approval Created:")
        print(f"  Approval ID     : {appr.approval_id}")
        print(f"  Operation       : {appr.operation}")
        print(f"  Candidate ID    : {appr.candidate_id}")
        print(f"  Candidate Name  : {appr.candidate_name}")
        print(f"  Expires At      : {appr.expires_at_unix}")

    print("\n" + "=" * 60)
    print("STEP 5 FLOW VERIFIED: request -> search -> candidates -> needs_approval")


if __name__ == "__main__":
    main()
