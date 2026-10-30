# Pico capability audit (A01)

Prepared: 2026-10-29. Commit `1f51e67` on `main`, 58 uncommitted
additions/modifications (all work below is on this uncommitted tree).
Audit runtime: macOS arm64, Python 3.14.4, Flutter SDK with Dart 3.11.4
(`flutter test --no-pub` works; `flutter pub get` needs a newer SDK).
No network access from the audit environment; no paid calls made ($0).

Service addresses: relay prod `https://pico-companion.fly.dev` (Fly app
`pico-companion`), local relay `127.0.0.1:8765`, agent server
`127.0.0.1:8000` (localhost only), Supabase project
`melngaeuytjuvfolwabd` (public URL only; no keys held here).

## Live execution path (as built)

Phone deterministic parser (`lib/services/command_parser.dart`) → relay
task queue (`relay/service.py` tasks + `tool_call` mailbox) → desktop
helper `execute_tool` (`agents/companion.py` + `agents/native_search.py`)
→ relay `complete_tool_result` / `upload_transfer` → phone receipt
(`submit_receipt` + `server/verification` checks).

`server/agent/` (planner loop, dispatch, Meta adapter) and `server/app.py`
task endpoints have **no live callers** (grep 2026-10-29: only unit tests
and a filename coincidence). They are tested code awaiting integration,
not the shipped planner. The shipped planner is the phone's
deterministic parser.

## Inventory

States: VERIFIED (observed here) / REPORTED (user-observed, not by me) /
UNTESTED / MISSING / BLOCKED.

### Phone (Flutter) — full suite 40/40 passing, observed this session

| Capability | Handler | State | Evidence |
| ---------- | ------- | ----- | -------- |
| Places save/park/finish/delete, local persist | `pico_chat_store.dart` | VERIFIED | `flutter test` places/interface suites |
| Voice/type dispatch to tasks | `home_screen.dart` `_dispatch` | VERIFIED | `test/home_dispatch_test.dart` 2/2 |
| Command recognition + natural phrasing | `command_parser.dart` | VERIFIED | `test/command_parser_test.dart` 11/11 |
| Unrecognized-request hint | `looksLikeCommand` + `_notice` | VERIFIED | widget test + probe run |
| Pairing code fetch, unpair | `devices_screen.dart`, `createPairing` | UNTESTED post-fix | relayBase bug fixed, analyzer-clean; user re-test pending |
| Task cards, exact-file approval, receipt | `task_bubble.dart`, `pico_store.dart` | UNTESTED live | code + analyzer only; needs paired run |
| Push-notification-free polling (4s refresh) | `pico_connection_store.dart` | REPORTED | user saw Connected state |

### Relay (Python) — 17/17 offline tests passing, observed this session

| Capability | Handler | State | Evidence |
| ---------- | ------- | ----- | -------- |
| Pairing, claim, lockout, mailbox, receipts | `relay/service.py`, `state.py` | VERIFIED offline | `relay/tests/` vs fake Supabase |
| Task queue, cancel, transfer, receipt verify | same | VERIFIED offline | same suite |
| Access logs (path-only), deep `/health` | `relay/app.py` | VERIFIED offline | `access_line` tests; serving unobserved (bind blocked here) |
| Live prod behavior | Fly deployment | REPORTED | user paired once; cold-start flakiness seen |
| `tasks` table + buckets in prod project | Supabase | BLOCKED | migration written (`supabase/`), owner must diff/apply |

### Desktop helper (Python + Swift)

| Capability | Handler | State | Evidence |
| ---------- | ------- | ----- | -------- |
| Overlay builds, pairing window, idle Places, snapshots, char sync | `agents/*.py`, `native/*.swift` | UNTESTED by me | overlay compiles (`make_macos_app.py` run); runtime needs tkinter/PIL absent here; user runs it |
| Tool execution: search/transfer/readback/open/permissions | `companion.execute_tool` | PARTIAL | `native_search` 8/8 tests; dispatch branch untested → fixed by A04 registry |
| Write/move/shell/document conversion | — | MISSING | no code; requested by user 2026-10-29 (photo organize) |

### Agent backend (`server/`)

| Capability | Handler | State | Evidence |
| ---------- | ------- | ----- | -------- |
| Contract validation, loop, dispatch, verifier | `contract.py`, `agent/`, `verification/` | VERIFIED | 18/18 `server/tests` |
| Localhost HTTP task loop | `server/app.py` | UNTESTED live | serving never observed (bind blocked) |
| Model provider calls | `agent/meta.py` | BLOCKED | no keys configured; smoke test never run live |

### Release engineering

| Capability | State | Evidence |
| ---------- | ----- | -------- |
| macOS overlay compile, source zip + SHA256SUMS (secret-audit clean) | VERIFIED | both scripts run this session |
| Full DMG/EXE/APK builds, signing, notarization | UNTESTED | needs PyInstaller/dotnet/network/owner certs |
| PWA served from relay | UNTESTED | needs `build_phone.sh` + deploy |

## Exact missing links

1. No model in the shipped path: planner is the deterministic phone
   parser; multi-step requests ("find X and organize Y") cannot plan.
2. No helper write/move/shell/document tools: organizing, editing,
   converting files is impossible (user-hit 2026-10-29).
3. Prod Supabase state unknown to this session: migration unapplied,
   `tasks`/`pico-transfers` presence unverified live.
4. Helper dispatch is an unvalidated if/elif chain (`execute_tool`):
   unknown tools and malformed args are not rejected with typed errors
   (repaired by A04 this batch).
