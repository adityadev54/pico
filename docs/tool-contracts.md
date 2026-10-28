# Tool contracts

Version 1 is a proposal for today's integration. See `contract-examples.json` for copyable sample messages. IDs and results there are synthetic.

## Required envelope

All messages carry `contract_version`, `task_id` and message `type`. Tool calls/results also carry `step_id` and `call_id`. Device IDs identify targets but never authorize access. The server derives owner identity from authentication, not a request body.

Request → agent → validated tool call → authorized native execution → structured tool result → verification → final result.

## Initial tools

- `search_documents`: query and optional folder-grant ID; returns candidate IDs and bounded metadata.
- `transfer_selected_file`: candidate ID and approval ID; exact file approved on phone, rechecked on computer.
- Next: `capture_current_tab`, `create_checklist`, `read_back_file`, `open_resource`.

## States

Queued, planning, needs_clarification, needs_approval, executing, verifying, awaiting_receipt; terminal: completed, partial, failed, cancelled.

A failed search must not become completed delivery. Upload is not phone receipt. Cancellation cannot be reversed by a late result. Model/step limits and deadlines stop runaway loops. State-changing retries require idempotency.

## Approval and evidence

Bind each approval to owner, task, exact operation/candidate or content, task version and expiry. Helpers enforce current local grants. Browser/document content cannot authorize tools.

Transfer evidence includes expected size/digest. The authenticated phone separately acknowledges received size/digest; verifier checks both. Never embed secrets, unrestricted paths or document contents in progress logs.

Clarification uses a question ID and task version so responses cannot resolve the wrong task. Errors include a stable code and short message; use `permission_denied`, `device_offline`, `no_match`, `candidate_changed`, `timeout`, or `unsupported_tool` as appropriate.

Finalize schemas together before implementing network endpoints. Sample messages are a shared interface starting point, not authentication or validation code.
