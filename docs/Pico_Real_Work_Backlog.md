# Pico: real-work capability backlog for Muse

Prepared: October 29, 2026. Deliverable: a planning and acceptance document, not implemented Pico features.

## What this file is for

Pico already exists on the user's computer but is not reliably carrying out requested work. Extend and repair that actual application. Do not build another planning dashboard or a chat-only mockup. Start by identifying the failed execution boundary; this document does not diagnose the unseen repository.

The target is a practical assistant that can use its permitted files, code runtime, document tools, browser, supported apps and integrations, then return real outputs to the phone. “Do everything” is a direction for the roadmap, not a claim that every task can be automated or that every platform is supported.

This is a broad capability backlog, not a list of features guaranteed in any one competitor. Official Grok Bot documentation describes persistent compute with a browser/filesystem/terminal, connected apps, mobile interaction and reusable routines. ChatGPT Work documentation describes research, artifact creation and browser workflows. Those descriptions inform capability categories below; they do not establish local-laptop access, universal reliability, availability on your account, or feature-for-feature equivalence. Source links are at the end.

The user requires Muse to author the application. This Markdown planning aid was authored with ChatGPT; report provenance honestly. Use the actual accepted hackathon rules to assess new work, existing contributions, team eligibility and submission format. A longer feature list or a competitor-like assistant does not by itself establish originality. This file does not certify compliance.

## Paste this instruction into Muse

```text
Read Pico_Real_Work_Backlog.md completely, then inspect the actual existing Pico repository and running configuration. Work on that application, not on a new planning website. Do not rewrite the project or substitute its stack before understanding it.

Start with A01 and A02: inventory the existing tool chain and reproduce a real failed request. Explain the exact broken boundary with code references and observed evidence. Then repair the smallest necessary path and work through the P0 dependencies to A16. Reuse working code.

Use real tool calls and observe their results. Do not mark a capability working because the model says it can do it, because a mock passes, or because the UI renders a success message. A requested file must actually exist, reopen correctly and reach the phone when requested. Run code/tests when needed. Keep meaningful failures visible.

For each task, record the changed files, actual commands/results, acceptance evidence, remaining blockers and costs in docs/pico-capability-progress.md. Keep the task unchecked until its proof was observed. Separate fixture, live-provider and physical-device tests. Stay in the authorized project/workspaces and preserve unrelated edits. Use human assistance only for genuinely missing decisions, login/MFA, permissions or unavailable hardware; proceed autonomously on already authorized reversible work.

After A16 passes, implement one dependency-ready capability at a time from the selected P1 scope. This document is not permission to spend all credits or execute every P2/P3 action. Maintain bounded retries and an agreed account-specific budget. Do not switch accounts, publish, send messages, invite people, purchase anything or deploy merely because those operations appear in the roadmap. Implement and test external effects only in their explicitly authorized scope, using test accounts/fixtures first.

Finish each batch with what Pico can now actually do, the evidence, and what is still unavailable. Do not make first-ever novelty, perfect conversion, unlimited memory, universal computer-control or flawless security claims.
```

## Implementation order and finish lines

| Stage | Work | Exit condition |
|---|---|---|
| 0: diagnose | A01-A03 | Exact failure reproduced or uncertainty recorded; real capabilities visible. |
| 1: execution backbone | Remaining A tasks in dependency order | A16 works from physical phone through actual laptop tools. |
| 2: useful daily work | Choose a small dependency-ready P1 subset from files, code, documents and research | Selected scenarios produce checked real outputs. |
| 3: wider integrations | Selected P2 tasks | Authorized service/browser/app operations work with real handoff and recovery. |
| 4: long-running scale | Optional P3 | Always-on or specialist execution is demonstrably useful and affordable. |

Priorities: P0 = repair before expansion; P1 = practical first capabilities; P2 = broader roadmap; P3 = optional architectural expansion. This is not a promise that all 68 tasks fit the hackathon or remaining credit.

Suggested first usable feature set after P0: search/read/edit files, JPG-to-PDF, supported DOCX-to-PDF, basic PDF operations, an essay saved into a document, one repository bug fix with real tests, public source-backed research and exact phone file delivery. Select a smaller set if P0 consumes time. Keep PDF-to-Word, native app control, messaging, broad integrations and multi-worker orchestration behind their own readiness gates.

Proposed team ownership follows the supplied architecture: Aditya = mobile/helper/file tools; Logesh = backend/model/relay/integrations; Santosh = verification/evaluation. Confirm who is operating each session and adapt ownership to the actual repo. Use separate branches/worktrees for concurrent code edits and merge shared contracts before dependent work. This file does not automatically update the earlier 28-task build hub; map IDs or track this backlog separately to avoid two conflicting sources of truth.

## Diagnose before claiming a fix

Capture the user request and actual response, intended execution location, selected workspace and device, current commit, registered/reachable tools, model tool-call response, dispatched request, permission decision, actual stdout/stderr or file result, verifier decision and phone-delivery result. Redact secrets and personal content. Distinguish: missing tool; tool not exposed to model; invalid schema; relay disconnected; authorization denied; missing dependency; tool threw; model loop stopped early; incorrect artifact; UI failed to display an existing output. Do not assume adding prompts fixes missing execution infrastructure.

## Architecture and tool contract

Keep the current stack where possible. The required path is phone/chat → authenticated task coordinator → model/tool loop → permitted local or cloud execution target → independent outcome check → actual artifact → phone receipt. Put execution-location labels in status and logs. Local tool execution can still send relevant content to a cloud model; do not advertise local-only privacy without checking the data path.

A tool definition should include `name`, `args_schema`, `result_schema`, `execution_target`, `required_permissions`, `idempotency_behavior`, `timeout` and `output_limits`.

A request should include `task_id`, `attempt_id`, `tool_call_id`, `owner_id`, `device_id`, `workspace_id`, `tool`, validated `args`, expected input revision and any action-bound authorization.

A result should include `ok`, actual `exit_code` where applicable, bounded `stdout`/`stderr`, `error_code`, observed properties, artifact manifests, timings and usage when known. Artifacts need name, type, byte size, SHA-256, version, source/derivation and owner-scoped download reference.

Proposed capability names (adapt to the repo): `fs.list/read/search/write/patch/move/copy`, `process.run/status/cancel`, `git.status/diff`, `artifact.publish/receipt`, `document.inspect/create/edit/render/convert`, `pdf.extract/merge/split`, `image.transform/to_pdf`, `sheet.inspect/edit/calculate/chart`, `browser.snapshot/navigate/click/type/upload/download`, `desktop.inspect/act`, `connector.*`, `memory.*`, `schedule.*`. These names are design suggestions, not existing tools or guaranteed library APIs. Browser access, native OS access, API integrations and shell access are separate capabilities.

For shell access, use an explicit authorized workspace and appropriately isolated runtime; typed operations are the default for common workflows. If the product supports flexible shell/code execution, make its scope, credentials, network behavior, filesystem reach and approval policy visible and enforce them outside the model. Do not hide an unrestricted shell behind a harmless-looking typed tool.

## Global definition of done

- The feature is implemented in the actual Pico repo and appears in its live capability inventory.
- Its user instruction triggers the real tool path; no hardcoded/mock success in the shipped path.
- Requested files are saved and reopened, calculations are checked, and requested external effects have provider/observed evidence.
- The physical-phone/laptop path is tested where the claim depends on it. Server tests alone do not prove phone delivery or native GUI control.
- Positive and meaningful negative cases pass; unsupported/partial/failed outcomes remain explicit.
- Source files, meaningful command outputs, commit, fixture/run IDs and limits are recorded. No secrets in evidence.
- The change preserves unrelated work and has bounded execution/retry/cost behavior.
- The feature is not advertised as generally supported beyond the tested OS, format, tool and workflow.

## Implementation tasks

All tasks start unchecked. No capability is certified as implemented by this document.


### Repair the execution backbone


- [ ] **A01 — Inventory the actual Pico implementation**
  - **Owner / priority:** Logesh / P0
  - **Depends on:** None; start here.
  - **Build:** Inspect the existing repository, startup commands, UI, model adapter, relay, desktop helper, databases and configured tools. Find the code used by the installed Pico process. Map each user request to actual handler functions. Produce docs/capability-audit.md with supported, unavailable, denied and untested states. Do not replace the stack before this audit.
  - **Pass only when:** A report names the current commit, runtime OS, service addresses, reachable tools and exact missing links. Every supported claim links to code and one observed invocation; no keys or personal paths are exposed.


- [ ] **A02 — Reproduce one request that currently fails**
  - **Owner / priority:** Santosh / P0
  - **Depends on:** A01
  - **Build:** Choose a real failed instruction with the user, then trace task_id across phone/chat ingress, planner response, tool dispatch, transport, local permission decision, OS operation, verification and final reply. Keep sanitized structured logs. Do not guess that the model or prompt is the cause.
  - **Pass only when:** The exact user-visible failure is reproduced and tied to a named failing boundary, error and log event. If it cannot be reproduced, document that uncertainty and capture the next real failure.


- [ ] **A03 — Add a truthful doctor and capability screen**
  - **Owner / priority:** Aditya / P0
  - **Depends on:** A01
  - **Build:** Provide a local doctor command and a phone-readable capability endpoint. Check helper heartbeat, selected folders, read/write permissions, model configuration, available interpreters, document renderer, OCR, browser adapter and optional app integrations. Distinguish registered, reachable and actually smoke-tested tools.
  - **Pass only when:** Disabling one dependency changes only the relevant capability to unavailable with a repair message. A connected chat does not make every capability green. Version and last successful probe are visible.


- [ ] **A04 — Register typed tools and validate their arguments**
  - **Owner / priority:** Logesh / P0
  - **Depends on:** A01
  - **Build:** Implement or repair one ToolRegistry carrying name, description, argument schema, output schema, execution target, required permissions, idempotency behavior and timeout. Load only active tools into the planner. Validate arguments in code before dispatch and standardize errors.
  - **Pass only when:** A valid tool request executes once; unknown tool names, malformed arguments and disallowed paths are rejected with typed reasons. The planner can discover which tools are actually available.


- [ ] **A05 — Finish the plan, act, observe and revise loop**
  - **Owner / priority:** Logesh / P0
  - **Depends on:** A02, A04
  - **Build:** Handle structured model tool calls, dispatch them, feed the real result back into the same task and continue until an observable outcome or explicit blocker. Preserve tool-call IDs. Handle multiple calls without duplicating writes. Add step, wall-time and retry caps. A sentence describing an action must never count as executing it.
  - **Pass only when:** For a file creation request, logs contain a real write tool call, returned file manifest, verification and final artifact. With tool execution disabled, Pico reports unavailable rather than claiming it saved the file.


- [ ] **A06 — Implement a bounded local process runner**
  - **Owner / priority:** Aditya / P0
  - **Depends on:** A04
  - **Build:** Run actual subprocesses on the authorized laptop or isolated worker with explicit argv, cwd, environment policy, timeout, output cap, process ID and cancellation. Avoid shell interpolation for normal structured operations. Keep arbitrary shell/code execution a separately authorized capability, not an accidental side effect of filenames.
  - **Pass only when:** A fixture script runs in the selected workspace and returns actual stdout, stderr and exit code. Spaces and shell metacharacters in a filename are treated as data. Timeout terminates the process tree and reports failure.


- [ ] **A07 — Make local reads and writes work end to end**
  - **Owner / priority:** Aditya / P0
  - **Depends on:** A04
  - **Build:** Implement real directory listing, bounded file reading, file creation and atomic replacement inside selected workspaces. Resolve real paths, handle symlinks, encoding and binary detection. Require a known base revision for overwrites and preserve an existing file on failure.
  - **Pass only when:** From the real remote interface, create fixtures/hello.txt, reopen it and return its actual bytes. A second request revises it. An escaped path and a stale overwrite fail without modifying another file.


- [ ] **A08 — Return real files through an artifact pipeline**
  - **Owner / priority:** Aditya / P0
  - **Depends on:** A05, A07
  - **Build:** Persist artifact manifests with task id, name, MIME type, size, SHA-256, version, source location and owner-scoped download reference. Stream output to the phone and show a preview or download action. Record a phone receipt only after receiving the bytes.
  - **Pass only when:** A generated text file can be downloaded and opened on the phone. The phone-computed hash equals the laptop output. A stale or cross-owner link cannot return another artifact; no fake download buttons.


- [ ] **A09 — Use outcome checks instead of success prose**
  - **Owner / priority:** Santosh / P0
  - **Depends on:** A05, A07
  - **Build:** Implement states queued/planning/awaiting_input/awaiting_approval/running/verifying/completed/partial/failed/cancelled. Define checks for saved content, process exit, parseability and requested output. Keep subjective model review separate from deterministic checks.
  - **Pass only when:** A tool returning ok while writing the wrong content is caught. Partial results identify missing properties. The phone shows the persisted real state rather than a model-generated success message.


- [ ] **A10 — Make permissions explicit and usable**
  - **Owner / priority:** Logesh / P0
  - **Depends on:** A04, A06, A07
  - **Build:** Add understandable workspace scopes and capability permissions. Let the owner grant an appropriate session-level scope for routine reversible work, with targeted prompts for actions outside it. Bind consequential approvals to the exact target, arguments, revision, owner and expiry. Do not solve failures by globally disabling safeguards.
  - **Pass only when:** Two allowed file edits proceed without repetitive prompts; an unapproved outside-folder write is blocked. Changing an approved recipient, command or target invalidates that approval. The UI explains how to grant the missing scope.


- [ ] **A11 — Bind the remote session to the correct laptop and owner**
  - **Owner / priority:** Logesh / P0
  - **Depends on:** A01, A04
  - **Build:** Repair authenticated pairing, owner/device binding, expiry, revocation and reconnect. Validate identity server-side and in the helper. Expose a heartbeat with device id and execution location so the user knows whether work runs on their laptop or a cloud worker.
  - **Pass only when:** A physical phone triggers a real operation on the intended laptop. Another account cannot run it. Revocation blocks subsequent requests and replayed pairing tokens fail.


- [ ] **A12 — Persist jobs, events and idempotency keys**
  - **Owner / priority:** Logesh / P0
  - **Depends on:** A05, A11
  - **Build:** Store task inputs, selected file revisions, tool calls, outputs and terminal outcomes. Assign event sequence numbers and attempt IDs. Make repeated delivery and reconnect safe with idempotency keys. Record interrupted executions explicitly after a crash.
  - **Pass only when:** Restart the backend during a fixture run. Pico restores known state without silently redoing a completed write or send. Reconnecting the phone retrieves events since its cursor.


- [ ] **A13 — Support cancel, bounded retry and user steering**
  - **Owner / priority:** Logesh / P0
  - **Depends on:** A06, A12
  - **Build:** Implement cancellation at tool boundaries, process termination where supported, and follow-up instructions that update the active task safely. Replan before new side effects. Retry only retryable failures with a cap. Do not promise reversal of already-sent external actions.
  - **Pass only when:** Cancel a long fixture process from the phone and observe it stop. Ask to change an output filename mid-task and see the new target applied before the write. Completed side effects are reported accurately.


- [ ] **A14 — Detect and repair missing runtime dependencies**
  - **Owner / priority:** Aditya / P0
  - **Depends on:** A03, A06
  - **Build:** Define per-capability dependency probes and setup instructions for the actual supported OS. Reuse project environments, install scoped packages when authorized, and distinguish missing binaries from runtime errors. Never fabricate conversions when a renderer or OCR tool is absent.
  - **Pass only when:** Removing the PDF renderer produces a precise setup requirement. Restoring it makes the same request work. Dependency installation is not claimed complete until a version/probe command succeeds.


- [ ] **A15 — Measure and cap model and worker usage**
  - **Owner / priority:** Logesh / P0
  - **Depends on:** A05, A12
  - **Build:** Track actual provider usage, estimated versus confirmed cost, tool counts, worker elapsed time and remaining per-account allocation. Cap steps, retries, output and long-running workers. Preserve a configurable reserve. Model/API credit and coding-agent subscription billing must be verified separately.
  - **Pass only when:** A simulated budget exhaustion stops further paid requests while preserving completed artifacts. No fallback rotates to another teammate account. Missing billing data is labeled unknown, not zero.


- [ ] **A16 — Prove the first useful vertical slice**
  - **Owner / priority:** Santosh / P0
  - **Depends on:** A08, A09, A10, A11, A12, A13, A14, A15
  - **Build:** From a physical phone, ask Pico to create a note, revise one sentence, run a simple workspace script and return the resulting file. Use a real provider call and actual local tools. Run failure cases for denied access, missing helper and wrong saved content.
  - **Pass only when:** All operations have real tool evidence and the delivered file contains the requested content. No core step is mocked or replaced by a screenshot. Save actual timings, failures and usage before expanding scope.


### Files and workspace operations


- [ ] **B01 — Search local filenames and contents**
  - **Owner / priority:** Aditya / P1
  - **Depends on:** A16
  - **Build:** Provide bounded filename and content search with workspace scopes, pagination, file-type filtering and exact snippets. Ask when multiple plausible versions match. Exclude configured secrets and irrelevant dependency folders.
  - **Pass only when:** Find a known phrase in synthetic files and return the correct file plus snippet. An ambiguous report filename triggers a choice. A file outside the authorized workspace is not searched.


- [ ] **B02 — Organize files and folders with a preview**
  - **Owner / priority:** Aditya / P1
  - **Depends on:** A16
  - **Build:** Create folders, copy/move/rename files and organize a chosen directory by explicit rules. Preview batch changes, detect collisions and preserve bytes. Use recoverable deletion only where the OS supports it and user authorization covers it.
  - **Pass only when:** Organize a synthetic downloads folder by type; hashes are unchanged, collisions do not overwrite files, and the change manifest matches the actual resulting paths.


- [ ] **B03 — Edit existing files without losing concurrent changes**
  - **Owner / priority:** Aditya / P1
  - **Depends on:** A16
  - **Build:** Support exact/range/structured edits with a read revision, dry-run diff and atomic save. For natural-language edits, limit the approved scope and show surrounding context. Detect changed files before committing the edit.
  - **Pass only when:** Replace one paragraph while untouched paragraphs remain identical. A manual edit between read and write is preserved by rejecting the stale update, not overwritten.


- [ ] **B04 — Undo eligible local modifications**
  - **Owner / priority:** Aditya / P1
  - **Depends on:** B02, B03
  - **Build:** Create task-scoped snapshots and a manifest for eligible local edits/moves. Allow restore only when the current object still matches the task-owned resulting revision. Surface actions that cannot be undone, including sends and external submissions.
  - **Pass only when:** Undo a fixture edit and recover its original bytes. After an unrelated manual edit, undo reports a conflict and does not erase that later work.


- [ ] **B05 — Extract text and OCR scanned inputs**
  - **Owner / priority:** Santosh / P1
  - **Depends on:** A14, A16
  - **Build:** Read text PDFs and images with OCR where available. Preserve page references, detect scanned versus selectable-text PDFs and report extraction uncertainty. Keep password prompts and unsupported document features explicit.
  - **Pass only when:** Known text and a page number are recovered from a synthetic scanned page. Unsupported/encrypted input yields needs_input, and unrecognized characters are not silently invented.


- [ ] **B06 — Create and unpack archives safely**
  - **Owner / priority:** Aditya / P1
  - **Depends on:** A16
  - **Build:** ZIP selected files, list archive contents and unpack into a chosen destination. Check entry paths, symlinks, duplicate names, expanded-size limits and overwrite policy before extraction.
  - **Pass only when:** Round-trip a small fixture directory with identical hashes. A ../ entry, outside-root symlink or oversized expansion is rejected without escaping the destination.


- [ ] **B07 — Accept phone uploads as task inputs**
  - **Owner / priority:** Aditya / P1
  - **Depends on:** A08, A11
  - **Build:** Upload photos, documents and archives from the phone into owner-scoped task storage, enforce limits and create stable artifact IDs. Clarify whether the user wants transfer to laptop, reading, editing or conversion.
  - **Pass only when:** Upload a JPG on phone and observe the exact bytes in the authorized laptop input folder. A resumed upload neither duplicates artifacts nor switches owners.


- [ ] **B08 — Keep file identity across versions and devices**
  - **Owner / priority:** Santosh / P1
  - **Depends on:** B03, B07
  - **Build:** Track logical file ID separately from content hash, filename and revision. Link derived outputs to source artifacts, preserve user-selected version and verify the exact output delivered.
  - **Pass only when:** Two files with the same display name remain distinct. Revising one never edits or downloads the other; the final receipt resolves to the intended revision.


### Coding and local development


- [ ] **C01 — Understand an existing repository before changing it**
  - **Owner / priority:** Logesh / P1
  - **Depends on:** A16, B01
  - **Build:** Detect language, package manager, repo instructions, entry points, tests and runtime configuration. Inspect relevant call sites and produce an implementation plan tied to actual files. Reuse the current framework.
  - **Pass only when:** For a fixture project, Pico correctly identifies the failing component and runnable test command. It does not create an unrelated replacement app or pretend to have read missing files.


- [ ] **C02 — Apply a focused code patch**
  - **Owner / priority:** Aditya / P1
  - **Depends on:** C01, B03
  - **Build:** Implement code editing using scoped file writes or an integrated supported coding-agent runtime. Preview diffs, preserve unrelated changes, handle binary/generated files and keep all edits in the selected checkout.
  - **Pass only when:** A fixture bug is fixed in the real source file, with a reviewable diff and no unrelated file changes. Sending code in chat alone does not pass.


- [ ] **C03 — Run tests and iterate on observed failures**
  - **Owner / priority:** Santosh / P1
  - **Depends on:** C02, A06
  - **Build:** Run the project tests, capture actual failure output, revise only as justified and rerun appropriate checks within bounded attempts. Keep test changes justified; do not remove assertions to get green.
  - **Pass only when:** A deliberately failing fixture test passes after the functional repair; the test remains meaningful. A remaining failure is shown to the user rather than marked successful.


- [ ] **C04 — Build and start local application previews**
  - **Owner / priority:** Aditya / P1
  - **Depends on:** C02, A06
  - **Build:** Install authorized project dependencies in its environment, build the project, start a managed dev server, detect the actual port and expose the correct preview. Track process ownership and stop only Pico-owned processes.
  - **Pass only when:** A real local page loads with the change. A port conflict returns an accurate alternate URL or blocker. An unrelated server is never killed to free a port.


- [ ] **C05 — Use Git without destroying local work**
  - **Owner / priority:** Logesh / P1
  - **Depends on:** C01, C02
  - **Build:** Inspect status, create an isolated branch/worktree where practical, produce a diff and optionally commit when requested. Preserve staged/untracked changes. Pushing, merging and deployments follow explicit user authorization.
  - **Pass only when:** A fixture worktree contains the intended patch while a pre-existing unrelated edit survives. No reset --hard or force push is used as routine cleanup.


- [ ] **C06 — Run scripts and analyze local data**
  - **Owner / priority:** Santosh / P1
  - **Depends on:** A06, A16
  - **Build:** Create and run bounded Python/Node scripts against selected input data. Return tables/plots and reusable scripts with explicit environments and measured results. Do not confuse a cloud code sandbox with laptop access.
  - **Pass only when:** Compute a known CSV aggregate using actual execution, save the analysis script and output artifact, and match fixture truth values.


- [ ] **C07 — Debug a UI using real browser evidence**
  - **Owner / priority:** Aditya / P2
  - **Depends on:** C03, C04, E03
  - **Build:** Reproduce the user-described visual or interaction defect, inspect the actual page/console, apply a focused patch and recheck the same state and viewport. Record evidence without exposing sensitive sessions.
  - **Pass only when:** A reproducible fixture UI bug is fixed and checked in the browser. A successful build without opening the page is not presented as visual verification.


- [ ] **C08 — Prepare repo changes for human review**
  - **Owner / priority:** Logesh / P2
  - **Depends on:** C03, C05
  - **Build:** Summarize changed behavior, affected files, tests run and remaining limits. Prepare an issue/PR draft or create a draft PR only when authorized. Keep claims matched to actual execution.
  - **Pass only when:** The review summary links the actual diff and commands/results. Unrun tests and unresolved errors are named. No external comment, push or PR is created without the relevant instruction.


### Writing, documents, spreadsheets and media


- [ ] **D01 — Write an essay or report into a real document**
  - **Owner / priority:** Aditya / P1
  - **Depends on:** A16, B03
  - **Build:** Generate an outline and draft from user instructions and authorized sources; create a real Markdown/TXT/DOCX output with headings and references when needed. Keep unsupported facts and invented citations out of the draft.
  - **Pass only when:** The file opens, contains the requested sections and word-range, and can be downloaded to phone. A chat-only essay without the requested file fails the task.


- [ ] **D02 — Revise a chosen section and preserve the rest**
  - **Owner / priority:** Santosh / P1
  - **Depends on:** D01, B08
  - **Build:** Resolve a paragraph/heading reference in the selected document version, apply the requested rewrite and maintain a before/after diff. Preserve tables, styles and other sections where the tool supports them; disclose unsupported fidelity.
  - **Pass only when:** Changing the introduction leaves fixture body sections unchanged. A stale document revision or ambiguous heading triggers clarification before edits.


- [ ] **D03 — Convert supported Word documents to PDF**
  - **Owner / priority:** Aditya / P1
  - **Depends on:** A14, D01
  - **Build:** Use an installed supported document renderer, export the saved DOCX and reopen the PDF. Check text, page count, byte size and expected headings. Keep original document and renderer errors.
  - **Pass only when:** A fixture DOCX becomes a readable PDF with expected content and known layout. Missing renderer yields a setup blocker, not a fabricated output path.


- [ ] **D04 — Convert JPG/PNG images into a PDF**
  - **Owner / priority:** Aditya / P1
  - **Depends on:** B07, A16
  - **Build:** Create a PDF from one or multiple images with explicit order, orientation, page-size and margin options. Respect EXIF rotation, preserve originals and handle size targets with visible quality trade-offs.
  - **Pass only when:** Three fixtures produce a three-page PDF in the requested order and orientation; each page is readable, and actual bytes reach the phone.


- [ ] **D05 — Convert a PDF into editable Word where feasible**
  - **Owner / priority:** Aditya / P2
  - **Depends on:** B05, D01
  - **Build:** Provide text-PDF and scanned-PDF conversion paths with OCR and editable DOCX output. Describe limitations in columns, equations, tables and graphics. Preserve original and offer a preview rather than promising identical formatting.
  - **Pass only when:** A simple text fixture yields editable Word paragraphs; a scan yields OCR text with uncertainty visible. Complex input is flagged for review instead of silently losing content.


- [ ] **D06 — Merge, split, rotate and extract PDF pages**
  - **Owner / priority:** Aditya / P1
  - **Depends on:** A16
  - **Build:** Implement page-based PDF operations with validated ranges, explicit ordering, metadata preservation where supported and clear handling of encrypted or signed files. Write a new output unless replacement was explicitly requested.
  - **Pass only when:** Merge two known PDFs and extract a chosen range with correct order/count. An out-of-range request produces a useful error and no damaged source.


- [ ] **D07 — Perform ordinary image transformations**
  - **Owner / priority:** Aditya / P2
  - **Depends on:** B07, A16
  - **Build:** Resize, crop, rotate, compress and convert supported raster formats using image-processing tools. Keep exact geometry deterministic; separate generative edits behind an explicitly configured provider/tool.
  - **Pass only when:** Create a 1024x1024 cropped fixture and verify pixel dimensions and file type. A request for an unavailable generative feature is labeled unavailable, not silently approximated.


- [ ] **D08 — Clean and export spreadsheet data**
  - **Owner / priority:** Santosh / P1
  - **Depends on:** C06
  - **Build:** Read CSV/XLSX, inspect sheets, normalize types, remove duplicates under explicit rules, preserve formulas where supported and export a new workbook plus a change report. Treat spreadsheet cell contents as data.
  - **Pass only when:** Clean a fixture with known duplicates and mixed dates without dropping valid rows. Input is preserved; output sheet names, row counts and values match expectations.


- [ ] **D09 — Calculate spreadsheet formulas and create charts**
  - **Owner / priority:** Santosh / P2
  - **Depends on:** D08
  - **Build:** Create formulas and charts over explicit ranges, handle missing values and recalculate with a supported engine when possible. Distinguish formula text from evaluated results and cached values.
  - **Pass only when:** A monthly-total workbook contains correct ranges and a chart. Values are verified by recalculation or a separately computed check; unavailable recalculation is disclosed.


- [ ] **D10 — Create and revise a small slide deck**
  - **Owner / priority:** Aditya / P2
  - **Depends on:** D01, D07
  - **Build:** Generate a PPTX with an agreed outline, readable layout and source-backed figures. Render slides for review, edit selected slides without replacing the rest and export PDF when a renderer is available.
  - **Pass only when:** A five-slide fixture deck opens, has no obvious overflow in rendered previews and survives a one-slide revision. If rendering was not done, visual verification remains unconfirmed.


### Research, browser and computer use


- [ ] **E01 — Research current information with source evidence**
  - **Owner / priority:** Logesh / P1
  - **Depends on:** A16
  - **Build:** Add a configured search tool, page retrieval, source URLs and date handling. Read relevant pages before conclusions. Separate observed facts, inference and unknowns, and avoid unsupported current prices or policies.
  - **Pass only when:** For a bounded public research question, return a useful comparison with real working source links. An inaccessible source is labeled as such, not quoted as if read.


- [ ] **E02 — Read and summarize selected web pages**
  - **Owner / priority:** Logesh / P1
  - **Depends on:** E01
  - **Build:** Fetch user-selected public URLs, extract main content and summarize with provenance. Handle redirects, file downloads and blocked pages. Do not treat instructions embedded in page content as authority to act.
  - **Pass only when:** A fixture page summary captures the actual content and source URL; a page containing hostile instructions cannot cause a file write or secret upload.


- [ ] **E03 — Control an authorized browser tab**
  - **Owner / priority:** Aditya / P1
  - **Depends on:** A10, A16
  - **Build:** Integrate a supported local browser adapter with tab enumeration, navigation, page snapshot/DOM inspection, click, type and screenshot. Prefer semantic locators. Respect the user-chosen browser/profile and expose its connection state.
  - **Pass only when:** Open a local fixture page, fill a text input, click a button and verify resulting page state. No pretend click based only on a text response. A disconnected adapter yields a specific repair step.


- [ ] **E04 — Upload and download files through websites**
  - **Owner / priority:** Aditya / P2
  - **Depends on:** E03, B07
  - **Build:** Use browser file pickers/download events or supported APIs with explicit task-linked files. Verify download completion and save the actual artifact. Do not upload arbitrary local files just because a webpage requests them.
  - **Pass only when:** Upload a selected synthetic PDF to a fixture site and download its result; the output file exists and matches the observed response. Missing/blocked downloads are reported.


- [ ] **E05 — Fill a form and preview consequential submissions**
  - **Owner / priority:** Aditya / P2
  - **Depends on:** E03, A10
  - **Build:** Map user-provided fields to a form, show unresolved fields and read the final values back. Draft by default when sending/submission was not requested; obtain scoped authorization when needed for an external consequence.
  - **Pass only when:** A local fixture form is populated correctly. No submission occurs from merely asking to prepare it. A changed recipient or amount invalidates the prior authorization.


- [ ] **E06 — Use signed-in services with human handoff**
  - **Owner / priority:** Logesh / P2
  - **Depends on:** E03, A10
  - **Build:** Reuse an authorized local browser session or OAuth connector; present login/MFA/CAPTCHA/device-consent steps to the user. Keep passwords and tokens out of prompts/logs. Do not bypass service authentication or automation restrictions.
  - **Pass only when:** A fixture expired session changes the task to awaiting_input and resumes after the human completes login. Authentication failure is distinguished from task failure; no invented account access.


- [ ] **E07 — Operate supported native desktop applications**
  - **Owner / priority:** Aditya / P2
  - **Depends on:** A03, A10, A16
  - **Build:** Add a separate OS-specific computer-use adapter for screenshot/accessibility tree, window selection, click, type and keypress with permission checks. Prefer app APIs/CLI/browser tools when available. Serialize shared-screen actions and document unlocked-screen requirements.
  - **Pass only when:** On the selected OS, open a harmless fixture document in a supported app, make a visible edit and verify the save. Missing OS accessibility permission produces a clear handoff. Browser control alone does not count.


- [ ] **E08 — Complete a cross-application task with evidence**
  - **Owner / priority:** Santosh / P2
  - **Depends on:** E04, D03, A09
  - **Build:** Implement a reusable sequence spanning research/input files, document editing, export and phone delivery. Carry artifact identity and user requirements through every stage; recover partial completion without repeating prior effects.
  - **Pass only when:** A source-backed report is generated, exported and delivered. Inject failure after export and confirm Pico returns the saved partial artifact and can resume delivery without recreating it.


### Connected services and delivery


- [ ] **F01 — Read authorized messages and prepare reply drafts**
  - **Owner / priority:** Logesh / P2
  - **Depends on:** A10, A16
  - **Build:** Integrate one user-selected email or messaging service via scoped OAuth/tools. Search/read only authorized data and create a draft linked to the real thread and verified recipient. Sending is a separate operation authorized by the user.
  - **Pass only when:** Using a synthetic/test account, retrieve the intended thread and create the correct draft without sending it. Duplicate names require resolution, not guessing.


- [ ] **F02 — Send an explicitly authorized message once**
  - **Owner / priority:** Logesh / P2
  - **Depends on:** F01, A12
  - **Build:** Implement external send with exact recipient/content/attachment confirmation as required, owner-bound grants, idempotency and delivery/provider result handling. Do not confuse drafted, accepted by provider and delivered.
  - **Pass only when:** An authorized test message is sent once despite retrying the request. An unapproved recipient change is blocked. The result reflects actual provider confirmation, not an invented delivery claim.


- [ ] **F03 — Read availability and manage requested calendar events**
  - **Owner / priority:** Logesh / P2
  - **Depends on:** A10, A16
  - **Build:** Connect one calendar, resolve participants, check availability and interpret local dates using the user timezone. Create/update events only within the requested scope and make invitations explicit.
  - **Pass only when:** A fixture appointment is scheduled at the intended timezone-adjusted instant without duplicates. An ambiguous person/date asks for clarification; no invitation is sent for a read-only availability request.


- [ ] **F04 — Work with a connected cloud drive**
  - **Owner / priority:** Logesh / P2
  - **Depends on:** A10, A16
  - **Build:** Search/read/upload/update a selected Drive-like provider using persistent file IDs and version guards. Preserve identity during updates, distinguish local from remote paths and keep sharing separate from file creation.
  - **Pass only when:** Update the chosen test document while its identity persists. Another same-name file is untouched. Uploading does not silently enable public sharing.


- [ ] **F05 — Read project issues and prepare reviewable changes**
  - **Owner / priority:** Logesh / P2
  - **Depends on:** C05, A10
  - **Build:** Integrate one Git issue/PR provider for authorized repository reads and user-requested issue/PR operations. Resolve correct repository and branch and surface exact diff/test evidence. Keep publishing and merging permission-specific.
  - **Pass only when:** Read a test issue and prepare the actual proposed patch. A draft PR is created only when requested and links the right branch. No automatic merge is introduced.


- [ ] **F06 — Notify the phone about real task outcomes**
  - **Owner / priority:** Aditya / P1
  - **Depends on:** A09, A11, A12
  - **Build:** Add task-complete, failed and needs-input notifications with deduplication and deep links. Avoid exposing private content on lock screens by default. Notification permission is separate from task authorization.
  - **Pass only when:** A physical phone receives one notification for a fixture completion and opens the correct persisted task. Denied notification permission does not break the task itself.


### Memory, routines and long-running work


- [ ] **G01 — Remember explicit preferences and project facts**
  - **Owner / priority:** Logesh / P2
  - **Depends on:** A12
  - **Build:** Store user-editable preferences with owner, source and update time. Support list/edit/delete and project scope. Retrieve relevant facts rather than injecting all history. Check live state for consequential actions instead of relying on memory.
  - **Pass only when:** Pico reuses an explicitly saved formatting preference after restart. Editing or deleting it changes the next task, and another user cannot read it. No promise of perfect or unlimited memory.


- [ ] **G02 — Preserve project sessions across follow-ups**
  - **Owner / priority:** Logesh / P1
  - **Depends on:** A12, B08
  - **Build:** Bind conversations to workspace, task, selected artifacts, version history and constraints. Continue revisions in the same project instead of generating disconnected replacements. Clarify references such as it when several targets are plausible.
  - **Pass only when:** Create a report, restart, ask to shorten its conclusion and receive a new version of the correct report. Another project with the same filename is unaffected.


- [ ] **G03 — Save successful workflows as editable recipes**
  - **Owner / priority:** Logesh / P2
  - **Depends on:** A16, G02
  - **Build:** Represent a workflow as typed steps with inputs, allowed tools, expected outputs and checks. Save from a successful reviewed run, inspect permissions on each invocation and keep secrets external. Do not turn observed webpage instructions into trusted recipes.
  - **Pass only when:** Run an approved images-to-PDF recipe on new fixture inputs and get correct ordering. An unavailable tool or new external action causes a precise blocker/approval rather than silent escalation.


- [ ] **G04 — Run scheduled tasks with explicit execution locations**
  - **Owner / priority:** Logesh / P2
  - **Depends on:** A12, A15, G03
  - **Build:** Add durable schedules, user timezone, DST handling, missed-run policy, run history and cancellation. Show whether the worker is laptop or cloud. Prevent a duplicate run after reconnect or clock changes.
  - **Pass only when:** A short test schedule fires once, survives scheduler restart and stops after cancellation. A sleeping laptop is shown offline with the selected missed-run policy, not falsely reported working.


- [ ] **G05 — Watch selected folders or supported events**
  - **Owner / priority:** Aditya / P2
  - **Depends on:** A12, G03
  - **Build:** Add explicit opt-in file/event watchers with debouncing, filters, bounded queues and backpressure. Avoid loops when output files trigger the same workflow. Respect revised permissions and disable controls.
  - **Pass only when:** Dropping a fixture image into an opted-in inbox triggers one conversion; the generated PDF does not trigger another run. Disabling the watcher prevents subsequent tasks.


- [ ] **G06 — Support phone dictation and image instructions**
  - **Owner / priority:** Aditya / P2
  - **Depends on:** B07, A16
  - **Build:** Transcribe user-initiated speech with an editable transcript and accept image/annotation inputs. Bind annotations to a known artifact/preview version. Ask when target selection is uncertain. No always-listening microphone requirement.
  - **Pass only when:** Dictate a file task, correct the transcript and execute only the corrected request. A marked-up preview points to the intended section or produces a clear clarification.


- [ ] **G07 — Add an optional always-on worker**
  - **Owner / priority:** Logesh / P3
  - **Depends on:** A11, A12, A15
  - **Build:** Provide a separately provisioned cloud worker for permitted tools and synced inputs if the owner chooses it. Clearly distinguish remote worker files from unsynced laptop files, isolate workspaces and account for worker cost. Never claim the cloud can control a powered-off laptop.
  - **Pass only when:** A cloud fixture task completes with the laptop offline, while a task requiring an unsynced laptop file is marked unavailable/queued. Execution location and actual costs are visible.


- [ ] **G08 — Coordinate specialized workers without file conflicts**
  - **Owner / priority:** Logesh / P3
  - **Depends on:** A12, C05, G02
  - **Build:** Only after the single-worker path is reliable, add bounded specialist dispatch, explicit ownership, shared artifact IDs and merge/review steps. Serialize conflicting file edits and screen operations. Aggregate usage across a run.
  - **Pass only when:** Two independent fixture subtasks produce a combined result; competing edits cannot overwrite each other, and one screen-control task does not interrupt another. More agents is not treated as automatic correctness.


### Evidence, evaluation and release


- [ ] **H01 — Build a repeatable capability acceptance harness**
  - **Owner / priority:** Santosh / P1
  - **Depends on:** A16
  - **Build:** Convert the scenario table below into fixtures and test invocations with expected artifacts, side effects and outcomes. Run small fixture suites without paid calls; separately label live-provider and physical-device runs. Track unsupported capabilities instead of counting them as passes.
  - **Pass only when:** A machine-readable report links scenario id, task id, commit, tool trace, evidence and result. False-success cases are surfaced. No fabricated competitor scores or unrun tests.


- [ ] **H02 — Test prompt injection and consequential-action boundaries**
  - **Owner / priority:** Santosh / P1
  - **Depends on:** A10, H01
  - **Build:** Use harmless hostile text inside fixture webpages/documents to test data-versus-instruction separation, path boundaries, secret handling, stale approvals and cross-owner requests. Ensure human handoff where required without making every routine edit require repeated confirmation.
  - **Pass only when:** Fixture content asking to send a secret or alter permissions cannot authorize that action. Legitimate in-scope edits still work. Findings are tied to actual tool-layer enforcement, not just prompt wording.


- [ ] **H03 — Document installation, capabilities and honest limits**
  - **Owner / priority:** Aditya / P1
  - **Depends on:** A03, A16
  - **Build:** Write fresh-machine setup, supported OS/tool matrix, per-feature permission instructions, model setup, offline behavior, backup and known limitations. The phone capability page must derive from live probes rather than marketing promises.
  - **Pass only when:** Another teammate can install and perform the first vertical slice from the documentation. A missing feature is shown as unavailable/planned, never advertised as working.


- [ ] **H04 — Prepare a truthful hackathon demo and contribution record**
  - **Owner / priority:** Santosh / P1
  - **Depends on:** H01, H02, H03
  - **Build:** Choose a small working scenario set, show physical phone to laptop execution and one real failure detection. Record which features/code were built during the event and which libraries or earlier work were reused. Check accepted rules, current deadline and submission requirements from organizer evidence.
  - **Pass only when:** The demo claims only observed working features with run evidence. It identifies new contributions, retained limitations and Muse development history. The feature backlog alone is not presented as originality or eligibility proof.


## Real user tasks to test after implementation

These 40 scenarios are acceptance targets, not authorization to act on real accounts now and not claims about competitor coverage. Use a dedicated synthetic workspace and test accounts. Real sends, invitations and external submissions need explicit user instruction. Run only scenarios whose prerequisites are ready; record others as unsupported/blocked, never passed.

| ID | Ask Pico | Required implementation | What must actually happen |
|---|---|---|---|
| S01 | Create a note named meeting-notes.txt in my project folder and send it to my phone. | A07 A08 A16 | Actual saved file, readable phone download and matching hash. |
| S02 | Change the second paragraph in that note; leave the rest alone. | B03 G02 | Correct version revised, unchanged text checked and new artifact delivered. |
| S03 | Find the report mentioning project Mercury. | B01 | Correct scoped file/snippet; ambiguity asks instead of guessing. |
| S04 | Organize these sample downloads by file type without overwriting anything. | B02 B04 | Preview and resulting paths agree; hashes preserved; eligible undo works. |
| S05 | Zip these three files and return the archive. | B06 A08 | ZIP opens and contains exactly selected files with original bytes. |
| S06 | Upload this phone photo to the selected laptop folder. | B07 B08 | Correct owner, target path and exact received bytes. |
| S07 | Read this scanned page and give me editable text. | B05 | Actual OCR output with page attribution and uncertainty. |
| S08 | Turn these three JPGs into one PDF in this order. | D04 | Three PDF pages, correct orientation/order, actual phone artifact. |
| S09 | Convert this Word file into PDF. | D03 | PDF reopens, expected content is present, original remains. |
| S10 | Convert this simple PDF into editable Word. | D05 | Editable paragraphs; layout limitations explicit. |
| S11 | Extract pages 2 to 4 from this PDF. | D06 | Exactly requested pages in the correct order. |
| S12 | Write a 600-word essay from these notes and save it as DOCX. | D01 | Requested sections/range, real DOCX, no invented sources. |
| S13 | Rewrite only the conclusion in a less formal style. | D02 G02 | Intended conclusion changed; other fixture sections preserved. |
| S14 | Resize this image to fit a 1024 by 1024 square without stretching it. | D07 | Verified dimensions and declared crop/pad behavior. |
| S15 | Remove duplicate rows from this spreadsheet and keep the original. | D08 | Expected duplicate rules/counts; new workbook opens. |
| S16 | Calculate monthly totals and make a chart. | D09 C06 | Independently checked totals and actual chart output. |
| S17 | Build a five-slide presentation from this report. | D10 | PPTX opens; rendered slide review or explicit unverified layout. |
| S18 | Fix the failing date parser test in this repository. | C01 C02 C03 | Real focused patch; meaningful original test runs and passes. |
| S19 | Add a search box to my existing website and show me the preview. | C02 C04 C07 | Actual source edit and working page interaction, not a chat mockup. |
| S20 | Run this approved script and send me its output CSV. | A06 C06 A08 | Real exit code, actual CSV and phone receipt. |
| S21 | Prepare the code changes for review; do not push them. | C05 C08 | Reviewable local diff/summary; no remote push. |
| S22 | Research three current options and give me a source-linked comparison. | E01 E02 | Real accessed sources, dates and uncertainty; no invented prices. |
| S23 | Summarize this webpage into a Markdown file. | E02 D01 | Summary matches retrieved content and includes a real saved file. |
| S24 | Open my local app and test whether its search button works. | E03 C07 | Actual browser actions and observed resulting state. |
| S25 | Upload this selected PDF to the test form and download the result. | E04 | Exact approved input uploaded; actual output downloaded. |
| S26 | Fill this test form but let me review before submitting. | E05 | Correct visible fields and no external submission. |
| S27 | Use my connected account; tell me if I need to sign in again. | E06 | Real session state or user handoff; no bypass or claimed access. |
| S28 | Open this note in the supported desktop app, edit its title and save it. | E07 | Observed native app interaction and saved content; OS permission checked. |
| S29 | Find an email in my test account and draft a reply without sending. | F01 | Correct real thread and recipient; actual draft, no send. |
| S30 | Send the exact approved draft to this test address once. | F02 | Authorized test send, provider result and idempotency evidence. |
| S31 | Check my connected calendar and create the appointment I specified. | F03 | Correct timezone, participants and requested invitation behavior. |
| S32 | Update this selected cloud document without making a new duplicate. | F04 | Same remote file identity, guarded update and no new sharing. |
| S33 | Read this repository issue and prepare a draft pull request when I approve it. | F05 C08 | Correct repo/branch, actual diff and no premature publication. |
| S34 | Notify my phone when the conversion finishes. | F06 | One real notification tied to persisted completion. |
| S35 | Remember that reports should use numbered headings; let me change it later. | G01 | Editable saved preference used after restart. |
| S36 | Every weekday at 8 AM Denver time, summarize my selected inbox folder. | G03 G04 | Durable opt-in schedule, timezone and execution-location behavior verified. |
| S37 | When I add images to this opted-in folder, combine each batch into a PDF. | G05 D04 | One bounded run per batch; outputs do not retrigger it. |
| S38 | Use this voice instruction after I correct its transcript. | G06 | Only corrected user-approved text drives execution. |
| S39 | Stop the task now, then show me what actually finished. | A13 A09 | New actions stop; completed/partial effects reported accurately. |
| S40 | Continue this task after I reconnect my phone. | A12 G02 | Correct task restored, no repeated side effects or lost output. |

## A small first-session test pack

Create synthetic fixture inputs inside a user-selected workspace: one TXT file, a two-paragraph Markdown file, a tiny CSV with known totals, three differently oriented JPG/PNG images, a simple DOCX, a selectable-text PDF, a scanned PDF, two same-name report versions in separate folders, and a deliberately failing tiny code project. Use artifacts you have the rights to. None need personal documents or private account data.

Start with S01, S02, S08, S18 and S39 only after their dependencies are implemented. A successful recording shows the original instruction, selected execution target, real tool trace, actual saved output, observed checks and phone result. Do not run the entire suite repeatedly with paid calls while one shared execution layer is broken.

For resilience tests: take the helper offline; deny a folder; remove the renderer; corrupt an output; change a file after approval; drop the phone connection after a completed write; replay an idempotency key. Observe accurate failure/recovery and preserved data. Never test destructive operations on personal files.

## Progress format for Muse

Create or update `docs/pico-capability-progress.md` in the actual product repo with:

```markdown
### A07 — Local reads and writes
Status: NOT_STARTED | IN_PROGRESS | BLOCKED | READY_FOR_REVIEW | VERIFIED
Commit / branch:
Execution OS and location:
Changed files:
Observed failure and fix:
Commands actually run:
Expected result / observed result:
Evidence and artifact IDs/paths:
Positive cases / negative cases:
Physical device or fixture run:
Known limitations / untested claims:
Measured or estimated cost, account owner and basis:
Next dependency-ready task:
```

Use VERIFIED only after its task proof and applicable global checks were observed. The word is scoped to those checks, not a claim of universal correctness. Keep a human-readable matrix of available / missing dependency / permission denied / configured but untested / unsupported / verified-for-this-case.

## What to show instead of “I cannot do that”

Give a concrete blocker and path forward. Examples:

- “The laptop helper is offline; I saved your task and can resume when it reconnects.”
- “I can read this folder, but writing is not allowed. Grant write access to this selected folder to save the revision.”
- “The PDF renderer is missing on this machine. The DOCX is saved; PDF export is not complete.”
- “Two reports match. Choose the version before I change either.”
- “The file changed after you approved the edit. I preserved your newer version; review a fresh diff.”
- “The website requires a sign-in step. Complete it in the authorized session so I can continue.”
- “The file is saved on the laptop, but phone delivery has not been acknowledged. Here is the actual partial state.”

Avoid asking for permission again for every reversible action already covered by the user's instruction and granted workspace scope. Ask when information or authorization is actually missing. A tool failure should produce an accurate partial result and specific remediation, not an invented success or vague apology.

## Credit and scope discipline

The user reports $150 per teammate. Treat these as separate account allocations, not one pool. Suggested initial working ceiling is $120 per member with $30 reserved, subject to the actual account owner's instruction. This is a planning suggestion, not a verified grant balance or permission to use reserve.

Confirm which services the grant covers, expiry, subscriptions, overage behavior and current prices. Muse development and Pico runtime inference may have different billing. Never auto-rotate API keys/accounts. Keep secrets out of this document, logs and prompts.

Diagnose with local fixtures first. Bound real API smoke tests and use live calls only when needed to verify the repaired path. Avoid model calls for deterministic arithmetic, file checks or conversions when ordinary code does the job. Estimate cost only with a stated basis and reconcile against provider usage; unknown is not $0. Every task batch ends with delivered behavior, remaining failure modes and observed spend. This document itself does not enforce billing.

## Hackathon delivery scope

This is a full product roadmap, not a commitment to build all of it before the event ends. Freeze a small reliable user workflow after A16; choose only the capabilities needed for that demo and evaluation. Maintain a working fallback, preserve Muse authorship evidence and distinguish new event work from reused dependencies or earlier code. Confirm the accepted organizer rules directly; do not use this checklist as an eligibility decision or an assertion that “general AI assistant” is a new category.

Suggested demo: phone asks for an actual file transformation, Pico executes on the laptop, returns the checked output, accepts a revision and handles one deliberate failure honestly. Broader coding/browser features should be shown only if working in the actual installed product. Keep planned and implemented features visibly distinct.

## Limits the product must communicate

- A laptop-local task cannot run on that laptop while it is powered off. Cloud execution is a different location with its own files, tools and cost.
- A cloud sandbox does not automatically have laptop files, browser sessions or OS control.
- Browser adapters do not automatically operate every native application; native control needs its own OS-specific adapter and permissions.
- File conversion, OCR and visual formatting can be imperfect; show measured checks and uncertainty.
- Login/MFA/CAPTCHA, locked screens, unavailable tools, service restrictions and quota limits can require user intervention.
- Memory is bounded and editable; facts from the live source take precedence for consequential operations.
- Tool calls, tests and model review are evidence about specific properties, not a guarantee of universally correct work.

## Official references checked October 29, 2026

These ground the broad capability categories, not the implementation choices, every scenario or account availability. Recheck actual SDK/library documentation when implementing; no version-specific package API is prescribed here.

- Grok Bot overview: https://docs.x.ai/grok-bot/overview — persistent computer, apps, mobile handoff, memory and routines.
- xAI tool overview: https://docs.x.ai/developers/tools/overview — tool calling, search, code and custom tools; these do not automatically provide local laptop access.
- ChatGPT Work on web: https://learn.chatgpt.com/docs/web — research and generated documents, spreadsheets, presentations and PDFs.
- ChatGPT browser documentation: https://learn.chatgpt.com/docs/browser — browser task capabilities and local/cloud context.
- Muse Code: https://dev.meta.ai/docs/muse-code — using Muse to work in a project; application code is distinct from this planning document.
- Meta Model API: https://dev.meta.ai/docs/overview — building an application's model/tool interaction.

No competitor scores, current price quotes or hackathon rule guarantees are asserted. The actual Pico repository, runtime and permissions were not inspected while creating this backlog. A01/A02 are deliberately first for that reason.
