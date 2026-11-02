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

## Batch 16 — missed-approval guidance for the one-time grant (Nov 2, 2026)

### Denied/timeout grant says to approve on the computer; phone points there
Status: VERIFIED
Commit / branch: uncommitted working tree on feature/verification (after 885f22c)
Execution OS and location: macOS laptop, fixtures + widget tests
Changed files: `agents/task_execution.py`, `lib/components/computer_actions.dart`, `test/desktop_dispatch_test.py`, `test/request_routing_test.dart`, `docs/pico-features.md`
Observed failure and fix: the Mac popup appeared but the grant didn't stick (missed 45s timeout or deny), and the error still read "choose a folder" — indistinguishable from no-popup-at-all. Deny/timeout after a shown prompt now reports "Approve the folder request on your computer, then ask again."; only the truly unpromptable case keeps "Choose a folder...". The phone also shows "Check your computer too — approve the folder request there." right after queuing a first find/open with zero folders.
Commands actually run: `test/desktop_dispatch_test` (8 OK), `flutter test --no-pub test/request_routing_test.dart` (11 OK), agents 97 / relay 50 / server 34 (OK), full `flutter test --no-pub` (105 OK), `dart analyze` (clean), `compileall` (clean)
Expected result / observed result: deny answers with the approve-on-computer message and writes no grant; approve-None keeps the choose-a-folder message; find with empty workspaces queues plus the heads-up snackbar.
Evidence and artifact IDs/paths: extended `test_denied_grant_keeps_permission_error`, extended "find goes through so the computer can ask once"
Positive cases / negative cases: asked=True vs asked=False message split; heads-up only for find/open with explicit empty workspaces
Physical device or fixture run: fixture + widget only; owner retries open-file and approves the Mac popup
Known limitations / untested claims: the 45s approval timeout is unchanged; file outside Documents still needs its own folder grant afterward
Measured or estimated cost, account owner and basis: $0 observed, no model calls
Next dependency-ready task: owner retries open-file on the paired Mac and approves the one-time prompt

---

## Batch 15 — one-time folder grant for find/open (Nov 2, 2026)

### Opening a file asks once instead of dead-ending on folders
Status: VERIFIED
Commit / branch: uncommitted working tree on feature/verification (after 885f22c)
Execution OS and location: macOS laptop, fixtures + widget tests
Changed files: `agents/task_execution.py`, `agents/grants.py`, `agents/companion.py`, `lib/components/computer_actions.dart`, `test/desktop_dispatch_test.py`, `agents/tests/test_grants.py`, `test/request_routing_test.dart`, `docs/pico-features.md`
Observed failure and fix: with no folder grants, "open a pdf" died with "choose an approved folder" and no way forward from the phone. Find/open are read-only, so the helper now asks once on the computer ("grant_folder" for ~/Documents, read-only): approving stores the grant (persisted via `grant_added` + save) and runs the request; later opens need only the phone review. The phone lets find/open through with zero folders; write-level commands keep the up-front guidance. Deny, missing approval UI, or missing Documents fails honestly as before.
Commands actually run: agents 97 / relay 50 / server 34 (OK), `flutter test --no-pub` (105 OK), `dart analyze` (clean), `compileall` (clean), system-python integration pytest (33 passed)
Expected result / observed result: search with no grants prompts once, stores a read grant, and succeeds; open works on the stored grant; deny/None keeps permission_denied with no grant written; find with empty workspaces queues, convert still guides.
Evidence and artifact IDs/paths: `test_open_asks_one_time_folder_grant`, `test_denied_grant_keeps_permission_error`, `test_record_builds_a_grant_without_io`, "find goes through so the computer can ask once", "convert with no granted folders guides instead of queuing"
Positive cases / negative cases: grant prompt content (tool/folder/access), persistence flag, second call reuses the grant; deny/None/missing-dir refuse without side effects
Physical device or fixture run: fixture + widget only; live overlay prompt on the paired Mac pending owner hands
Known limitations / untested claims: the one-line companion save on `grant_added` has no autotest (needs tkinter); overlay shows the raw review JSON in the tk fallback; Documents is the only offered folder (CLI/GUI for others)
Measured or estimated cost, account owner and basis: $0 observed, no model calls
Next dependency-ready task: owner retries open-file on the paired Mac and approves the one-time prompt

---

## Batch 14 — per-file delete popups (Nov 2, 2026)

### Every deleted file asks its own popup
Status: VERIFIED
Commit / branch: uncommitted working tree on feature/verification (after 885f22c)
Execution OS and location: macOS laptop, widget tests
Changed files: `lib/components/computer_actions.dart`, `test/request_routing_test.dart`, `docs/pico-features.md`
Observed failure and fix: one review sheet approved up to 5 files at once ("File: a.txt, b.txt"). The delete flow now shows one popup per file naming exactly that file; approving deletes it and asks the next, cancelling stops the batch with the rest unasked and undeleted.
Commands actually run: `flutter test --no-pub test/request_routing_test.dart` (10 OK), full `flutter test --no-pub` (104 OK), `dart analyze` (clean)
Expected result / observed result: "delete a.txt and b.txt" shows two popups in order; approve+approve sends 2 confirmed tasks; approve+cancel sends 1.
Evidence and artifact IDs/paths: "each deleted file asks its own popup", "cancel stops the delete batch"
Positive cases / negative cases: per-file popup order and confirmed flags; mid-batch cancel keeps file 2 unasked; single-file delete unchanged (1 popup)
Physical device or fixture run: widget only
Known limitations / untested claims: none new; trash-only + delete-grant rules unchanged
Measured or estimated cost, account owner and basis: $0 observed, no model calls
Next dependency-ready task: owner grants folder + retries open-file on the paired Mac

---

## Batch 13 — permission-denied diagnosis: kept messages, kept grants (Nov 2, 2026)

### Approved the action but open-file still says permission denied
Status: VERIFIED
Commit / branch: uncommitted working tree on feature/verification (after 885f22c)
Execution OS and location: macOS laptop, fixtures + widget tests
Changed files: `relay/service.py`, `agents/grants.py`, `agents/companion.py`, `lib/components/computer_actions.dart`, `relay/tests/test_service.py`, `agents/tests/test_grants.py`, `test/request_routing_test.dart`, `docs/pico-features.md`
Observed failure and fix: three stacked causes, all in current code. (1) The Mac had no folder grant — approving the phone review is not a grant, and every re-pair wiped `grants` + `allowed_apps` in `bind_device`. Grants and app approvals are machine-local user approvals now: re-pairing archives state but keeps them (`grants.fresh_pair_state`, device-bound lists still reset). (2) The relay dropped the helper's failure message, so the phone showed bare "permission denied" with no guidance. Failed results now keep a bounded `message`, which the task bubble already renders. (3) The phone queued folder-needing commands with zero granted folders. It now says "Choose an approved folder on your computer first" instead (missing data from old helpers still goes through).
Commands actually run: agents 96 / relay 50 / server 34 (OK), `flutter test --no-pub` (102 OK), `dart analyze` (clean), `compileall` (clean), system-python integration pytest (31 passed)
Expected result / observed result: failed rows carry `message`; fresh-pair state keeps grants/apps and resets places/mail/journal; find/open/delete with explicitly-empty workspaces guide instead of queuing.
Evidence and artifact IDs/paths: `test_failed_result_keeps_the_helper_message`, `test_repair_keeps_folder_and_app_approvals`, "find with no granted folders guides instead of queuing"
Positive cases / negative cases: permission message stored verbatim (300 chars max); re-pair keeps 1 grant + 1 app approval and clears 4 device-bound keys without mutating the input; guard fires only on explicit empty workspaces
Physical device or fixture run: fixture + widget only; owner must re-grant the Mac folder once, then retry without re-pairing
Known limitations / untested claims: delete-level grants need the CLI (the permissions UI saves read/write only); a stale-empty capabilities snapshot could over-block until the next helper poll
Measured or estimated cost, account owner and basis: $0 observed, no model calls
Next dependency-ready task: owner grants folder + retries open-file on the paired Mac

---

## Batch 12 — games, timers, PDF pages, open-anything questions (Nov 2, 2026)

### Guessing game + riddles, in-app timer/reminders, pdf_pages, "Which one?"
Status: VERIFIED
Commit / branch: uncommitted working tree on feature/verification (after 885f22c)
Execution OS and location: macOS laptop, fixtures + widget tests
Changed files: `lib/services/local_play.dart` (NEW), `lib/services/pico_play_store.dart` (NEW), `lib/services/pico_store.dart`, `lib/services/pico_chat_store.dart`, `lib/services/command_parser.dart`, `lib/components/computer_actions.dart`, `lib/components/workflow_review.dart`, `lib/components/task_bubble.dart`, `lib/screens/home_screen.dart`, `agents/tools.py`, `agents/handlers.py`, `agents/task_execution.py`, `relay/workflows.py`, `relay/service.py`, `server/contract.py`, `test/game_test.dart` (NEW), `test/timer_test.dart` (NEW), `test/command_parser_test.dart`, `test/request_routing_test.dart`, `test/small_talk_test.dart`, `agents/tests/test_handlers.py`, `agents/tests/test_tools.py`, `test/desktop_dispatch_test.py`, `relay/tests/test_tool_path.py`, `docs/pico-features.md`
Observed failure and fix: new scope (user chose in-app timers, core+extras PDF). (1) Guessing game (1-20, higher/lower) and 8-riddle bank play multi-turn via a pending-prompt slot; computer commands always pass through, `stop` backs out, a new computer intent clears the prompt. (2) In-app countdown timer + reminders announce as Pico messages; bare "remind me to X" asks "in how many minutes?" first. (3) New `pdf_pages` tool (merge/split/rotate/delete/watermark/unlock/images) wired phone->relay->helper with review; watermark is a dependency-free diagonal stamp; unlock refuses wrong passwords; images needs poppler with an honest setup error. (4) Ambiguous "open" now asks "Which one? ... Reply with the exact file name." Also fixed a real gap found on the way: convert/delete/restore/pdf were missing from the connected companion's tool set, and write-grant filtering ignored delete-ranked folders — both fixed with ranked enforcement.
Commands actually run: `flutter test --no-pub test/game_test.dart` (4 OK), `test/timer_test.dart` (4 OK), `test/command_parser_test.dart` (19 OK incl. pdf), full `flutter test --no-pub` (101 OK), `dart analyze` (clean), agents 95 / relay 49 / server 34 (OK), `compileall` (clean), system-python integration pytest (31 passed)
Expected result / observed result: games/riddles/timers/reminders converse multi-turn locally; pdf phrasing dispatches reviewed tasks producing verified byte-level outputs; ambiguous open asks a naming question; connected-path convert/delete/restore/pdf execute with ranked grants.
Evidence and artifact IDs/paths: `test/game_test.dart`, `test/timer_test.dart`, "edits pdf pages" parser test, `test_pdf_pages_*`, `test_connected_file_tools_run_with_write_grant`, `test_pdf_pages_merge_over_mail`, `test_open_document_asks_which_on_many_matches`
Positive cases / negative cases: win/retry/give-up/stop flows; timer announce + cancel; reminder follow-up + fire; merge/split/rotate/delete/watermark/unlock on real bytes; refusals for bad pages, bad angle, locked input, wrong password, missing poppler, single-file merge, out-of-range pages
Physical device or fixture run: fixture + widget only; live pdf/game runs on paired hardware pending owner hands
Known limitations / untested claims: games/timers/reminders are in-memory (lost on restart), in-app only (no background alarms, sound, or vibration); poppler absent here so images happy path is unverified on this machine; watermark is plain text; no compress/page-numbers/PDF-to-Excel; phones never display unlock passwords (relay-only)
Measured or estimated cost, account owner and basis: $0 observed, no model calls
Next dependency-ready task: owner hardware pass (pdf merge + single-approval open + game round on the paired Mac)

---

## Batch 11 — open-pdf fix, single approval, small-talk (Nov 2, 2026)

### "open report.pdf" opened Safari + double approval + "hi pico" / "what can you do"
Status: VERIFIED
Commit / branch: uncommitted working tree on feature/verification (after 885f22c)
Execution OS and location: macOS laptop, fixtures + widget tests
Changed files: `lib/services/command_parser.dart`, `lib/components/workflow_review.dart`, `lib/components/computer_actions.dart`, `lib/services/pico_chat_store.dart`, `lib/screens/home_screen.dart`, `test/command_parser_test.dart`, `test/request_routing_test.dart`, `test/small_talk_test.dart` (NEW), `relay/tests/test_tool_path.py`, `test/desktop_dispatch_test.py`, `docs/pico-features.md`
Observed failure and fix: (1) "open report.pdf" parsed as website `https://report.pdf` — Safari opened with the name in the address bar. `_websiteUrl` now rejects bare `name.ext` hosts (archives/installers/media included); real hosts and `host/path.pdf` URLs still open as sites. (2) Reported double approval: traced the design — phone review stamps `_pico_phone_approved`, helper skips the computer dialog when stamped. Proved with tests at both ends; current code asks exactly once. (3) convert/delete/restore were missing from the phone review set, so the relay rejected them 400 — added to `reviewedKinds`, delete reviews once then sends each file confirmed, and delete-ranked folders count as writable in the picker. (4) "hi pico" now answers "Hey!! So good to see you!..." and "what can you do" gives the computer-skills intro, both stored as conversation, linked or not; "hello, open chrome" works via a hello prefix.
Commands actually run: `flutter test --no-pub test/command_parser_test.dart` (18 OK), `test/request_routing_test.dart` (5 OK), `test/small_talk_test.dart` (4 OK), `.venv/bin/python -m unittest relay.tests.test_tool_path.ToolPathTests.test_reviewed_create_stamps_phone_approval` (OK), `test/desktop_dispatch_test` (5 OK)
Expected result / observed result: pdf/txt/jpg names open as documents; example.com stays a website; review sheet appears once per convert/delete with confirmed=true captured; stamped helper never calls computer approve; greeting/intro save user+assistant places while commands pass through untouched.
Evidence and artifact IDs/paths: "file names with extensions" parser test, `test_reviewed_create_stamps_phone_approval`, `test_phone_approval_skips_computer_approval`, routing review/cancel tests, `test/small_talk_test.dart`
Positive cases / negative cases: report.pdf/notes.txt/scan.jpg documents vs example.com sites; unreviewed kinds unstamped; refused review sends nothing; empty/command/note inputs get no small-talk reply
Physical device or fixture run: fixture + widget only; live single-approval open on paired Mac pending owner hands
Known limitations / untested claims: if two approval dialogs still appear on fresh code, report the exact text of each; `.zip` is also a real TLD — "open foo.zip" opens the file (full `https://` URL still opens the site)
Measured or estimated cost, account owner and basis: $0 observed, no model calls
Next dependency-ready task: in-app games, timer/reminders, PDF page tools (user-scoped)

---

## Batch 10 — start greeting + open apps/files/folders (Nov 2, 2026)

### Greeting on start + broad open_app vocabulary + folder opening
Status: VERIFIED
Commit / branch: uncommitted working tree on feature/verification (after 885f22c)
Execution OS and location: macOS laptop, fixtures + widget tests
Changed files: `lib/components/place_empty_state.dart`, `lib/services/command_parser.dart`, `agents/tools.py`, `agents/handlers.py`, `agents/task_execution.py`, `agents/native_search.py`, `test/greeting_test.dart` (NEW), `test/places_test.dart`, `test/command_parser_test.dart`, `agents/tests/test_handlers.py`, `agents/tests/test_tools.py`, `test/desktop_dispatch_test.py`, `docs/pico-features.md`
Observed failure and fix: (1) start screen showed "Hold that thought." with no greeting — the empty-state headline is now a time-of-day greeting ("Good morning, I'm Pico.") plus a capability hint. (2) `open chrome/safari/files/...` fell through to document search or null — the parser now recognizes 35 app spellings mapping to 22 canonical ids (was 8 spellings to 5), the tool enum and macOS bundle map match, and connected-desktop matching resolves ids against approved real app names via alias sets ("files" opens Finder or File Explorer per machine). (3) `open_document` matched files only — it now also matches folders by name and opens them in the file manager; `resolve_candidate` resolves directory ids.
Commands actually run: `.venv/bin/python -m unittest discover -s agents/tests` (91 OK), `-s relay/tests` (46 OK), `-s server/tests` (34 OK), `flutter test --no-pub` (82 OK), `dart analyze` (clean), `compileall` (clean), `PYTHONPATH=. /usr/bin/python3 -m pytest test/app_access_test.py test/integrated_task_test.py test/workflow_integration_test.py test/desktop_dispatch_test.py` (29 passed)
Expected result / observed result: greeting renders on empty conversation; `open chrome`/`open my files`/`open terminal` dispatch open_app; `open my trip photos folder` opens the folder; unapproved apps fail with "choose this app in the computer's Open apps menu first."
Evidence and artifact IDs/paths: `test/greeting_test.dart`, parser "opens everyday apps" test, `test_open_app_resolves_new_allowlisted_apps`, `test_open_document_opens_a_folder_by_name`, `test_open_app_matches_real_names_by_alias`
Positive cases / negative cases: 10 parser app spellings + organize-guard ("open my files and arrange...") + document escape ("open the music file" stays a document); unapproved-app and ambiguous-match refusals preserved
Physical device or fixture run: fixture + widget only; live open on paired Mac pending owner hands
Known limitations / untested claims: each app needs one-time approval in the computer's Open apps menu; agent_server (dev) path launches by macOS bundle id only; a folder and file sharing one substring now correctly reports ambiguity instead of opening the file
Measured or estimated cost, account owner and basis: $0 observed, no model calls
Next dependency-ready task: D06 merge/split/extract (pypdf already installed, deterministic)

---

## Batch 9 — human-time skills: convert, safe delete, multi-root (Nov 2, 2026)

### convert_file — JPG/PNG/PDF/DOCX/TXT/MD conversion slice (D03/D04/D05)
Status: VERIFIED
Commit / branch: uncommitted working tree on feature/verification (after 885f22c)
Execution OS and location: macOS laptop, fixture dirs under unittest/tmp
Changed files: `agents/tools.py`, `agents/handlers.py`, `agents/workspace.py`, `relay/workflows.py`, `relay/service.py`, `server/contract.py`, `server/verification/checks.py`, `lib/services/command_parser.dart`, `lib/components/computer_actions.dart`, `lib/components/task_bubble.dart`, `lib/screens/home_screen.dart`, `requirements.txt` (NEW), `.venv/` (NEW, gitignored)
Observed failure and fix: no conversion path existed; images/PDF/DOCX each needed different engines. Added one `convert_file` tool: Pillow for raster, pypdf for PDF, python-docx for DOCX, LibreOffice (`soffice`) for DOCX->PDF. Missing engines fail with the exact setup line instead of a fake path. Outputs never overwrite (numbered suffix).
Commands actually run: `.venv/bin/python -m unittest discover -s agents/tests` (89 OK), `-s relay/tests` (46 OK), `-s server/tests` (34 OK), `flutter test --no-pub` (80 OK), `dart analyze` (clean), `python3 -m compileall` (clean)
Expected result / observed result: images<->PDF, PDF->DOCX/TXT, DOCX->PDF/TXT/MD, TXT/MD->DOCX/PDF verified on real bytes in fixtures; phone "convert A to pdf" dispatches the tool.
Evidence and artifact IDs/paths: `agents/tests/test_handlers.py::test_convert_file_real_matrix`, `::test_convert_file_refusals_and_missing_engines`, `relay/tests/test_tool_path.py` vocab pin (19 tools), `test/command_parser_test.dart` convert cases
Positive cases / negative cases: 12-pair real-byte matrix incl. EXIF rotation and multi-page images; refusals for unknown format, missing engine, missing file, write-denied folder
Physical device or fixture run: fixture only; hardware proof pending owner hands
Known limitations / untested claims: DOCX->PDF needs LibreOffice installed; PDF->DOCX is text paragraphs (layout/columns/equations not preserved); no OCR (scanned PDFs yield no text); D06 page ops and D07 resize/crop not built
Measured or estimated cost, account owner and basis: $0 observed, no model calls; Pillow/pypdf/python-docx are free libs
Next dependency-ready task: D06 merge/split/extract (pypdf already installed, deterministic)

### delete_files + restore_deleted — trash-only delete with permission (B02 recoverable slice)
Status: VERIFIED
Commit / branch: uncommitted working tree on feature/verification (after 885f22c)
Execution OS and location: macOS laptop, fixture dirs
Changed files: `agents/tools.py`, `agents/handlers.py`, `agents/workspace.py`, `relay/workflows.py`, `server/contract.py`, `server/verification/checks.py`, `lib/services/command_parser.dart`, `lib/components/computer_actions.dart`, `lib/components/task_bubble.dart`, `lib/screens/home_screen.dart`
Observed failure and fix: no delete path existed. Added `delete_files` (requires `delete` grant + exact `confirm: DELETE`, moves to `.pico-trash/` with JSON sidecar manifest) and `restore_deleted` (latest-by-name, numbered on collision). Phone dispatches one task per file, max 5 per utterance.
Commands actually run: same full regression as above (89/46/34/80, analyzer clean)
Expected result / observed result: delete moves bytes to trash with manifest; restore returns them; nothing is permanently erased by either tool.
Evidence and artifact IDs/paths: `test_delete_moves_to_trash_and_restores`, `test_delete_refuses_without_delete_grant_or_confirm`, `test_delete_refuses_missing_and_outside` in `agents/tests/test_handlers.py`; vocab pin 19; parser delete/restore tests
Positive cases / negative cases: trash+restore round-trip, collision numbering, latest-wins restore; refusals for read/write-only grants, wrong confirm, missing file, outside-root path
Physical device or fixture run: fixture only
Known limitations / untested claims: trash is per-root `.pico-trash`, not the OS Trash (no Finder integration); no trash listing/expiry UI; directories cannot be deleted (files only); B04 edit-snapshots not built
Measured or estimated cost, account owner and basis: $0 observed, no model calls
Next dependency-ready task: B06 archives (stdlib zipfile, deterministic)

### organize_photos across every granted root (B02 multi-root slice)
Status: VERIFIED
Commit / branch: uncommitted working tree on feature/verification (after 885f22c)
Execution OS and location: macOS laptop, fixture dirs
Changed files: `agents/handlers.py`, `agents/tests/test_handlers.py`
Observed failure and fix: organize scanned only the first granted folder, so photos in other granted folders were silently missed. The scan now walks every granted root; the target folder stays in the primary write root; cross-root duplicates dedupe by content hash.
Commands actually run: `.venv/bin/python -m unittest discover -s agents/tests` (89 OK)
Expected result / observed result: photos split across two granted roots gather into one folder with no duplicates.
Evidence and artifact IDs/paths: `test_organize_photos_scans_every_granted_root`
Positive cases / negative cases: two-root gather incl. cross-root duplicate hashing; write-denied and bad-folder refusals unchanged
Physical device or fixture run: fixture only
Known limitations / untested claims: open_document/search/convert/delete still resolve names under the primary write root; overlapping grants walk shared files twice (deduped by hash, costs time); no general by-type rules engine, no change manifest
Measured or estimated cost, account owner and basis: $0 observed, no model calls
Next dependency-ready task: B03 exact/range edits with revision guard (deterministic core; NL scoping needs A16)

### Project Python environment (A14 slice)
Status: VERIFIED
Changed files: `requirements.txt` (NEW: pillow, pypdf, python-docx), `.venv/` (NEW, gitignored; `.gitignore` already excluded it)
Observed failure and fix: Homebrew Python is PEP 668 externally-managed, so `pip install` refused. Created the project-local `.venv` and installed the three approved libs there; all suites run under `.venv/bin/python`.
Commands actually run: `python3 -m venv .venv`, `.venv/bin/pip install -r requirements.txt`, full regression above
Known limitations: owner must run the same two commands on any fresh machine/checkout; LibreOffice (DOCX->PDF) and tesseract (future OCR) remain system installs outside pip
Measured cost: $0

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
