# Pico features and how to test them

Pico lets your phone send instructions to your computer. The phone app talks to
a relay, the relay queues mail for the computer helper, and the helper runs
typed tools inside folders you granted. Nothing runs outside a grant, and
delete is trash-only (recoverable, never permanent).

Setup first (one time): see [runbook.md](runbook.md) — project `.venv`,
`requirements.txt`, local relay on port 8765, phone pointed at the relay,
computer helper paired and running, folders granted (grant a folder `delete`
access only if you want Pico to delete there).

## Folder permissions (read this on "permission denied")

Approving an action on the phone is NOT a folder grant. The Mac must also
grant Pico the folder itself, or every file command fails:

```sh
cd /Users/santoshadabala/PICO/pico
.venv/bin/python agents/grants.py list          # shows current grants
.venv/bin/python agents/grants.py grant ~/Documents --access write
```

- `read` lets Pico find/open files; `write` adds create/convert/organize;
  `delete` adds trash (only where you want it).
- Grants live in `~/.pico/places.json` on the Mac and survive re-pairing.
- First find/open with no folders granted pops one approval on the
  computer ("grant_folder" for Documents, read-only); approving stores
  the grant and runs the request, so later opens need only the phone
  review. The phone tells you to check the computer; approve there
  within 45 seconds or ask again. A missed approval says so plainly
  instead of a bare denial.
- Write-level commands with no granted folders say "Choose an approved
  folder on your computer first" instead of queuing a doomed task.
- Fastest live fix: right-click the Pico character → **Permissions…** →
  **Approved folders** → **Write workspace…** and pick the folder. No
  restart needed; the running helper picks it up immediately.
- The terminal-run agent server (`python3 -m agents.agent_server`) shows a
  one-tap approval popup when it starts with no folders: approving grants
  full file access for the session and also saves it for the companion
  (restart the companion to pick that side up).

Automated gates live in [qa-matrix.md](qa-matrix.md). This file is the
user-facing catalog: each feature, an example command, and how to check it
worked.

## Find and organize files

### Find files by name or content
- **Try:** `find my brief` or `find the file with the launch budget`
- **Verify:** Pico names the matching file(s) with a snippet. If two files
  match, it asks you to choose instead of guessing.
- **Limit:** searches granted folders only; secrets and dependency folders
  are excluded.

### Organize photos into one folder
- **Try:** `put all my photos in one folder named Santosh_Photos, no duplicates`
- **Verify:** the folder appears in your primary granted folder with every
  photo gathered, duplicates skipped by content hash (same photo in two
  folders is copied once), originals untouched, nothing overwritten.
- **Limit:** scans every granted folder; the target always lands in the
  first write-granted folder. No by-type rules engine yet.

### Rename and duplicate files
- **Try:** `rename old.txt to new.txt` or `duplicate photo.jpg`
- **Verify:** the rename lands in the same folder with the old name gone;
  the duplicate appears as `photo_copy.jpg` (`photo_copy_2.jpg` when
  taken). Both need a write workspace plus phone and computer approval.
- **Limit:** files only, never folders; renames never overwrite — a taken
  name fails instead of replacing.

### Zip and unzip
- **Try:** `zip report.pdf and notes.txt as bundle.zip` or `unzip bundle.zip to restored`
- **Verify:** the zip appears with everything inside (folders keep their
  shape); extracting recreates the files under the named folder without
  touching existing files.
- **Limit:** 5000 files or 100 MB per archive; hostile zips that try to
  escape their folder are refused.

### Show recent files
- **Try:** `recent files` or `recent files from the last 30 days`
- **Verify:** Pico lists the newest files first with names and sizes;
  quiet folders return an empty list, not an error.
- **Limit:** granted folders only; hidden files skipped.

### Search inside files
- **Try:** `find files containing launch budget`
- **Verify:** Pico names each matching file with the line number and a
  text snippet around the match.
- **Limit:** plain-text files up to 1 MB; binaries, scanned PDFs (no
  text layer), and oversized files are skipped and counted, not searched.

### Find duplicates and largest files
- **Try:** `find duplicate files` or `show my largest files`
- **Verify:** duplicates arrive grouped by identical content with names
  you can act on; largest files arrive biggest-first with sizes.
- **Limit:** empty files never count as duplicates; scans are bounded
  and say so when truncated.

## Read and open documents

### Open a document or folder
- **Try:** `open my resume`, `open the Q3 report`, `open report.pdf`, `open my trip photos folder`, `open lecture video`
- **Verify:** any file type opens on the computer in its default app
  (PDFs, videos, music, archives — not just documents), or the folder
  opens in the file manager. Type words work too: video, song, zip,
  ebook. Pico only opens on a unique match — several matches ask
  "Which one? ... Reply with the exact file name," and zero matches say
  so plainly.
- **Limit:** name matching runs over granted folders only.

### Read a document aloud into chat
- **Try:** `read the meeting notes`
- **Verify:** Pico returns the document's text (PDF text, DOCX paragraphs,
  TXT/Markdown as-is) in the task result.
- **Limit:** scanned PDFs have no text layer yet (no OCR), so they return
  nothing — that is reported, not invented.

## Convert files

### Convert between image, PDF, Word and text formats
- **Try:** `convert photo.jpg to pdf`, `convert report.pdf to word`,
  `convert notes.md to docx`
- **Verify:** the converted file appears next to the original with a
  numbered suffix when the name is taken (originals are never overwritten
  or modified). Supported pairs:
  - images (JPG/PNG/WebP/BMP/GIF) to PDF and between image formats
  - PDF to Word (.docx) or plain text
  - Word to PDF (needs LibreOffice installed) or plain text
  - TXT/Markdown to Word or PDF
- **Limit:** Word-to-PDF needs LibreOffice (`soffice` on PATH); PDF-to-Word
  keeps text paragraphs, not exact layout/columns/equations. No OCR, no
  resize/crop yet.

## PDF page tools (iLovePDF-style)

- **Try:** `merge a.pdf and b.pdf [into combined.pdf]`,
  `split report.pdf pages 1-3`, `extract pages 2-5 from report.pdf`,
  `rotate scan.pdf 90 degrees`, `delete pages 1-2 from draft.pdf`,
  `watermark report.pdf with DRAFT`, `unlock secure.pdf with password
  rosebud`, `convert scan.pdf to images`.
- **Verify:** one reviewed task produces the edited PDF next to the
  original (never overwritten, originals untouched); merge joins in
  order, split/rotate/delete keep the right pages, watermark stamps
  diagonal gray text, unlock needs the correct password.
- **Limit:** images need poppler (`brew install poppler`, 50 pages max);
  watermark is plain diagonal text (no logos); locked PDFs refuse every
  action except unlock; no compress, page numbers, or PDF-to-Excel.

## Create and edit

### Create notes and text files
- **Try:** `write a note called ideas.txt saying call the bank`
- **Verify:** the file appears in the granted folder with exactly that text.
- **Limit:** plain text only; no in-place editing of existing files yet.

## Delete and restore (permission-gated)

### Delete files to trash
- **Try:** `delete old.txt` (up to 5 files per command: `remove a.txt and b.txt`)
- **Verify:** every file gets its own approval popup naming exactly that
  file — approving moves it to that folder's `.pico-trash` with a
  manifest entry; cancelling stops the batch and leaves the remaining
  files unasked and undeleted. Refusals to check: a folder granted only
  read/write access must refuse; so must a missing file or a path
  outside the grants.
- **Limit:** files only, no folders; trash is per-folder (not the OS
  Trash app); nothing Pico deletes is permanent.

### Restore deleted files
- **Try:** `restore old.txt`
- **Verify:** the latest trashed copy returns to its original folder
  (numbered if something now occupies the name).

### Undo a Pico edit
- **Try:** `undo changes to notes.txt`
- **Verify:** an edited file returns to its previous version; a file
  Pico created moves to Pico trash (recoverable via restore). Repeating
  undo walks back through versions, one edit at a time.
- **Limit:** content writes only — renames, duplicates, and zips have
  no undo; refuses when the file changed outside Pico since that edit.

### Empty trash and check disk usage
- **Try:** `empty trash` or `disk usage`
- **Verify:** emptying reports how many files left Pico trash and how
  many bytes were freed; disk usage reports totals plus the largest
  top-level folders.
- **Limit:** emptying trash is permanent and needs a delete grant plus
  the explicit EMPTY confirmation; usage scans granted folders only.

## Start greeting

- **Try:** open the app with an empty conversation.
- **Verify:** Pico greets you by time of day ("Good morning, I'm Pico.")
  with a hint of what to ask.

## Small-talk (no computer needed)

- **Try:** `hi pico`, or `what can you do`
- **Verify:** Pico answers excitedly ("Hey!! So good to see you!...") or
  with a brief intro of its computer skills. Works even before a
  computer is connected; commands like `hey pico open chrome` still run
  as tasks instead.

## Games and puzzles (no computer needed)

- **Try:** `play a game`, then guess; `tell me a riddle`, then answer.
- **Verify:** Pico picks a number from 1 to 20 and answers higher/lower
  until you get it ("You got it in N tries!!"); riddles retry on wrong
  answers, praise correct ones ("Brilliant!!"), and `give up` reveals
  the answer. `stop` backs out anytime, and real commands (`open
  chrome`) always run as tasks instead of game moves.
- **Limit:** one game at a time; a new computer command ends the game.

## Timers and reminders (in-app)

- **Try:** `set a timer for 5 minutes`; `remind me in 10 minutes to call
  mom`; `remind me to stretch` (Pico asks "in how many minutes?").
- **Verify:** the timer announces ("Time's up!...") and reminders post
  ("Reminder: ...") in the conversation; `check timer` shows time left,
  `my reminders` lists pending ones, `cancel timer` / `cancel
  reminders` clear them.
- **Limit:** in-app only — timers and reminders fire while Pico is open
  and do not survive a restart. No sound, vibration, or background
  alarms.

## Open apps and websites

- **Try:** `open chrome`, `open safari`, `open my files`, `open terminal`,
  `open word`, `open system settings`, `open calculator`,
  `open https://example.com`
- **Verify:** the app launches (Chrome, Safari, Firefox, Edge, Finder /
  File Explorer, Terminal, Mail, Photos, Music, Messages, FaceTime,
  Maps, Settings, App Store, Calculator, Calendar, Notes, VS Code, Word,
  Excel, PowerPoint, or your default browser) or the site opens in the
  default browser on the paired computer.
- **Limit:** on the connected computer, each app must first be approved
  in the computer's Open apps menu; otherwise Pico tells you to approve
  it there instead of failing silently.

## Phone uploads

- **Try:** attach a photo or document to a task from the phone.
- **Verify:** the exact bytes land in the task's laptop input folder as a
  stable artifact, ready to convert, read, or organize.
- **Limit:** upload first, then tell Pico what to do with it in a
  follow-up command.

## Control running work

### Cancel a task
- **Try:** start a long organize, then cancel it from the task bubble.
- **Verify:** the task stops, queued work is removed, the helper process
  is signaled, and the task shows cancelled with a receipt of what did
  and did not finish.

### Steer a queued note's filename
- **Try:** send `write a note called draft.txt saying hello`, then before
  it runs send `actually call it final.txt` (or `rename it to final.txt`).
- **Verify:** the queued note is saved under the new name. If the helper
  already picked it up, Pico reports that honestly instead of pretending.
- **Limit:** steering covers the pending note's filename only, not
  general follow-up instructions.

## Pairing, devices and history

### Pair phone to computer
- **Try:** Devices screen → get a code on one side, enter it on the other.
- **Verify:** both sides show connected; tasks flow. Codes expire; wrong
  codes lock out after bounded attempts.

### Dead devices clean themselves up
- **Try:** pair a device, then leave it offline.
- **Verify:** the stale entry is auto-forgotten with re-pair guidance
  instead of lingering as "not found" forever.

### Copy previous commands
- **Try:** long-press / copy on any earlier task bubble.
- **Verify:** the exact command text copies so you can resend without
  retyping.

## Health and capabilities

### Doctor and dependency check
- **Run on the computer:** `.venv/bin/python agents/doctor.py` and
  `.venv/bin/python agents/deps.py`
- **Verify:** each row shows available/missing with the exact install
  command for anything missing (Python version, tkinter, Pillow, pypdf,
  python-docx, LibreOffice, tesseract).
- **Limit:** the phone capability screen is not built yet; these are
  computer-side commands.

## Ask Pico (AI-planned requests)

- **Try:** send a plain-English request from Ask Pico, e.g. `find my resume`
- **Verify:** the relay plans exactly one action from the enabled tools
  (or asks one clarification question), the phone shows the usual review
  sheet, and approving runs it like any typed command.
- **Limit:** needs the relay's model setup — API key, owner allowlist,
  and budget ledger (`PICO_MODEL_*` in the relay env file). Each request
  reserves $0.10 against a $1/day, $5 lifetime test budget; over-budget
  or unlisted callers fall back to basic commands with a plain message.

## Automated tests (release gates)

```sh
.venv/bin/python -m unittest discover -s agents/tests   # expect 97 OK
.venv/bin/python -m unittest discover -s relay/tests    # expect 50 OK
.venv/bin/python -m unittest discover -s server/tests   # expect 34 OK
flutter test --no-pub                                   # expect 105 OK
dart analyze                                            # expect clean
python3 -m compileall -q agents relay server scripts    # expect clean
```

Live-backend check (needs your `server.env`, never committed):

```sh
python3 scripts/check_connection.py --env-file ~/.pico/server.env
```

## Not built yet (do not demo as working)

In-place file editing, OCR of scanned pages, spreadsheet cleaning and
charts, slide decks, PDF compress/page-numbers, image resize/crop,
browser/computer-use control, email or calendar connections, reminders
and schedules, and the model-planned coding agent (needs API keys and
budget approval). Anything in
[Pico_Real_Work_Backlog.md](Pico_Real_Work_Backlog.md) outside this file
is still backlog.
