# Pico capability progress

Updated: October 28, 2026. Owner: Santosh (verification/fixtures), LoGesH (agent/planner), Aditya (native tools/helper).

---

## Evidence rules

A task is checked only when:
- The changed files are named.
- Actual test output is quoted or referenced.
- Limitations and what is still missing are explicit.
- No step is marked done because the model says it works.

---

## A-series: repair the execution backbone

### A01 — Inventory the actual Pico implementation ✅ (this document)

**Files inspected:** agents/, relay/, lib/, server/, docs/

**Execution path mapped:**

```
Phone (Flutter) → relay/app.py (Fly.io) → agent/poll → companion.py (macOS/Windows)
                                        ↓
                           server/app.py (localhost:8000)
                                        ↓
                           server/agent/loop.py (AgentLoop)
                                        ↓
                           agents/agent_server.py (localhost:8001)  ← NEW
                                        ↓
                           agents/handlers.py → native_search / workspace / runner
```

**Supported (code exists + tested):**
- Place capture and delivery (phone ↔ desktop)
- Relay mailbox (place, companion, idle, head_start, parked)
- Pairing (6-digit code, DPAPI on Windows, token file on macOS)
- Character mood sync
- Idle detection + optional screenshot (macOS)
- AgentLoop state machine (queued → executing → needs_approval → verifying → completed/failed)
- Contract validation (all message types, all tool shapes)
- Tool registry with argument validation (13 tools)
- Native handlers: search_documents, transfer_selected_file, read_back_file, fs_list, fs_read, fs_write, process_run, open_website, open_app, open_document, organize_photos, fetch_upload, manage_permissions
- Workspace (atomic writes, revision guards, path containment)
- Runner (bounded subprocess, cancel, timeout)
- Verifier checks (search, exact-file, transfer receipt, fs manifest, process result, organize, open_document)
- Doctor + deps probes

**Unavailable (planned, not built):**
- capture_current_tab, create_checklist, open_resource
- Email/calendar/cloud-drive connectors (F-series)
- Browser control (E03+)
- Native desktop app control (E07)
- Scheduled tasks (G04)
- Notifications to phone (F06)

**Untested (no physical device run yet):**
- Phone → agent_server → relay → phone receipt end-to-end
- Windows companion execute_tool path
- Head Start with a live Muse endpoint

---

### A02 — Reproduce one request that currently fails ⬜

**Status:** Not yet executed on a paired physical phone + laptop.

**Known missing boundary:** The server/app.py `/request` endpoint did not
call the model or dispatch tool calls before this session.  It accepted
`POST /request` and returned a task_id, but left the task in `queued` with
no further progress.

**Fixed in this session:** See A04, A05, A06, A07 below.

---

### A03 — Add a truthful doctor and capability screen ✅

**Files:** `agents/doctor.py`, `agents/deps.py`

**Evidence:** `python3 -m pytest agents/tests/test_doctor.py agents/tests/test_deps.py` — 14/14 pass.

**CLI:**
```sh
python3 agents/doctor.py --relay https://pico-companion.fly.dev --json
python3 agents/deps.py check
```

**Limitation:** screen permission probe skips without the compiled `macos_context` binary.

---

### A04 — Register typed tools and validate their arguments ✅

**Files:** `agents/tools.py`, `server/contract.py`

**Evidence:** `python3 -m pytest agents/tests/test_tools.py server/tests/test_contract.py` — 11/11 pass.

**Tools registered:** search_documents, transfer_selected_file, read_back_file, open_website, open_app, manage_permissions, fs_list, fs_read, fs_write, open_document, organize_photos, fetch_upload, process_run (+ 3 declared-unavailable).

**Validation:** Unknown tools → `unsupported_tool`. Malformed args → `invalid_args` with field name. Unavailable tools → typed rejection before dispatch.

---

### A05 — Finish the plan, act, observe and revise loop ✅ (loop) + NEW (auto-plan wiring)

**Files:** `server/agent/loop.py`, `server/agent/planner.py` (NEW), `server/app.py` (updated)

**Evidence:** `python3 -m pytest server/tests/test_agent_loop.py server/tests/test_planner.py` — 17/17 pass.

**What's now wired:**
- `POST /request` calls `model_plan()` immediately when `MUSE_API_URL`/`MUSE_API_KEY` are set.
- Planner returns a shaped `tool_call` dict or a `question` string; AgentLoop consumes it.
- If the model is not configured the task stays `queued`; caller can still POST `/plan` manually.
- Background thread dispatches the tool_call to the agent tool server.

**Step/model limits:** max_steps=6, max_model_calls=4. Deadline per step: 30 s (configurable).

**Limitation:** Multi-turn plans (search → wait for approval → transfer) require `/approve` + another `/plan` call from the client. The loop does not auto-continue after `needs_approval`.

---

### A06 — Implement a bounded local process runner ✅

**Files:** `agents/runner.py`

**Evidence:** `python3 -m pytest agents/tests/test_runner.py` — 9/9 pass.

**Verified:** spaces in paths, shell metacharacters as data, process-group kill on timeout, cancel via ProcHandle, stdout/stderr cap, real exit codes.

---

### A07 — Make local reads and writes work end to end ✅

**Files:** `agents/workspace.py`, `agents/native_search.py`

**Evidence:** `python3 -m pytest agents/tests/test_workspace.py agents/tests/test_native_search.py` — 17/17 pass.

**Verified:** atomic create, revision guard, stale-revision preservation, path escape rejection, binary detection, symlink skip, bounded listing.

---

### A08 — Return real files through an artifact pipeline ⬜

**Status:** `transfer_selected_file` handler exists and posts bytes + evidence. Phone-side download UI and SHA-256 receipt not yet connected. No `artifact.publish` endpoint.

**Blocker:** Needs Flutter-side artifact display + `/phone/artifact` relay endpoint.

---

### A09 — Use outcome checks instead of success prose ✅ (checks) ⬜ (wired into live path)

**Files:** `server/verification/checks.py`

**Evidence:** `python3 -m pytest server/tests/test_verification.py` — 10/10 pass.

**Gap:** Checks are not yet called automatically from `on_tool_result()` in the live server path. LoGesH needs to call `check_*` before transitioning to `verifying`/`completed`.

---

### A10 — Make permissions explicit and usable ✅

**Files:** `agents/grants.py`, `agents/native_search.py` (granted_roots with access levels)

**Evidence:** `python3 -m pytest agents/tests/test_grants.py` — 5/5 pass.

**CLI:**
```sh
python3 agents/grants.py grant ~/Documents --access read
python3 agents/grants.py grant ~/Projects --access write
python3 agents/grants.py list
python3 agents/grants.py revoke <id>
```

**Limitation:** UI for grant approval is the existing Permissions panel in companion. No web-based grant flow yet.

---

### A11 — Bind the remote session to correct laptop and owner ✅ (relay) ⬜ (agent_server auth)

**Files:** `relay/service.py`, `agents/client.py`, `agents/agent_server.py` (NEW)

**Relay:** Owner derived from Supabase auth token, never from request body. Devices must match `user_id`. Revocation clears mailbox.

**Agent server:** Shared-secret bearer token (`PICO_AGENT_TOKEN`) enforced. Dev mode (no token) for local testing.

**Gap:** The `server/app.py` ↔ `agents/agent_server.py` shared token is not yet automatically provisioned.

---

### A12 — Persist jobs, events and idempotency keys ⬜

**Status:** Tasks live in an in-memory dict in `server/app.py`. Restart loses all task state. Relay uses idempotency on mail IDs. Agent server has none.

**Next:** SQLite task store in `server/` with attempt IDs and event sequence numbers.

---

### A13 — Support cancel, bounded retry and user steering ✅ (cancel) ⬜ (retry, steering)

**Files:** `server/agent/loop.py` (cancel), `agents/agent_server.py` (register_cancel), `agents/handlers.py` (process_run cancel hook)

**Evidence:** `AgentLoopTests::test_cancellation_wins_over_late_result` passes.

**Gap:** No retry logic for retryable failures. No follow-up instruction handling.

---

### A14 — Detect and repair missing runtime dependencies ✅

**Files:** `agents/deps.py`

**Evidence:** `python3 -m pytest agents/tests/test_deps.py` — 8/8 pass.

**Verified:** Removing a dep changes its row to `missing` with the exact install command. Install refuses without `--allow-install`. Non-pip deps (binaries, decisions) report correctly.

---

### A15 — Measure and cap model and worker usage ✅ (step/call caps) ⬜ (credit tracking)

**Files:** `server/agent/loop.py` (max_steps=6, max_model_calls=4), `agents/runner.py` (timeout, output cap)

**Gap:** No token/cost counters from the model provider. No per-account budget enforcement.

---

### A16 — Prove the first useful vertical slice ⬜

**Status:** All component tests pass (114/114). End-to-end physical test pending.

**What now works in isolation:**
1. `execute_tool()` runs `fs_write`, `fs_read`, `fs_list`, `search_documents`, `process_run` with real files.
2. `model_plan()` produces valid tool_call dicts from fake model responses.
3. `AgentLoop` state machine handles the full search → approval → transfer flow.
4. Verifier checks catch wrong-content, changed-file, and unauthenticated-receipt failures.

**What still needs a physical run:**
- Pair phone → relay → companion → agent_server listening → POST /request from phone → task runs → result appears on phone.
- Requires `MUSE_API_URL`/`MUSE_API_KEY` for the planner, or manual `/plan` POST for dev.

---

## New files added this session

| File | Purpose |
|---|---|
| `server/agent/planner.py` | Model call → structured tool_call or clarification |
| `server/agent/tools_proxy.py` | HTTP bridge: server → agent tool server |
| `agents/agent_server.py` | Native tool execution server (localhost:8001) |
| `agents/tests/test_agent_server.py` | 13 tests for execute_tool() |
| `server/tests/test_planner.py` | 10 tests for planner (no real model calls) |
| `docs/pico-capability-progress.md` | This file |

**Test count before:** 92  **After:** 114  **All passing.**

---

## How to run the full vertical slice today

```sh
# Terminal 1 — native tool server (grant your workspace)
PICO_SEARCH_ROOTS=~/Documents:~/Projects python3 -m agents.agent_server

# Terminal 2 — agent backend
PICO_ALLOW_LOCAL_AUTH=1 MUSE_API_URL=https://... MUSE_API_KEY=... \
  python3 -m server.app --port 8000

# Terminal 3 — send a task (replace TOKEN with your Supabase access token)
curl -s -X POST http://127.0.0.1:8000/request \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "find my project brief", "device_id": "your-device-uuid"}'
# Returns: {"task_id": "...", "status": "executing"}

# Poll until done:
curl -s "http://127.0.0.1:8000/task?id=TASK_ID" \
  -H "Authorization: Bearer TOKEN"
```

Without Muse keys, leave out `MUSE_API_URL`/`MUSE_API_KEY`. The task stays `queued`; drive it manually:

```sh
curl -s -X POST http://127.0.0.1:8000/plan \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"task_id": "...", "tool_call": { ... }}'
```
