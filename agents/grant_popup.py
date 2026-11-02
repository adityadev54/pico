"""One-tap file-access approval for the terminal-run tool server.

When agents/agent_server.py starts without explicit folder grants
(PICO_SEARCH_ROOTS / --roots), it shows this popup on the laptop instead
of failing every file tool. One approval grants full access (find, open,
read, write, organize, convert, recoverable trash) under the chosen
folder for the session. Denial, closing the window, or a headless
machine leaves the server running with no grants, and file tools fail
honestly with permission_denied.

On macOS the dialog is a native system popup (osascript, no extra
install). Other platforms use tkinter when available.
"""
from __future__ import annotations

import sys
from pathlib import Path

FULL_ACCESS = "delete"  # Top grant rank: implies read + write + trash.

COMPANION_STATE = Path.home() / ".pico" / "places.json"


def persist_grant_for_companion(path, access=FULL_ACCESS):
    """Record a popup approval in the companion state file so phone tasks
    share it. Only augments an EXISTING file (never creates a partial one);
    the companion picks it up on restart."""
    try:
        if not COMPANION_STATE.is_file():
            return False
        from grants import grant as _grant
        _grant(path, access=access, source="popup-approval",
               state_path=COMPANION_STATE)
    except (OSError, SystemExit, ValueError):
        return False
    return True


def default_scope() -> Path | None:
    """Broadest sensible default: the user's home folder."""
    home = Path.home()
    for candidate in (home, home / "Documents"):
        try:
            if candidate.is_dir():
                return candidate.resolve()
        except OSError:
            continue
    return None


def request_full_access_popup(scope=None, dialog=None) -> list[dict]:
    """Ask the laptop user for full file access. Returns grants or []."""
    if scope is None:
        scope = default_scope()
    if scope is None:
        return []
    try:
        approved, chosen = (dialog or _default_dialog)(Path(scope))
    except Exception:
        return []  # Headless, dialog tool missing, or dialog crashed.
    if not approved:
        return []
    try:
        resolved = Path(chosen).expanduser().resolve()
    except OSError:
        return []
    if not resolved.is_dir():
        return []
    return [{"path": str(resolved), "access": FULL_ACCESS,
             "source": "popup-approval"}]


def startup_grants(explicit: list[dict], allow_popup: bool = True,
                   dialog=None, persist_companion: bool = True) -> list[dict]:
    """Explicit grants win; otherwise offer the approval popup once."""
    if explicit or not allow_popup:
        return list(explicit)
    print("Pico: no folder grants configured — showing permission popup…",
          flush=True)
    grants = request_full_access_popup(dialog=dialog)
    if grants:
        print(f"Pico: full file access approved for {grants[0]['path']}",
              flush=True)
        if persist_companion and persist_grant_for_companion(grants[0]["path"]):
            print("Pico: approval also saved for the companion; "
                  "restart it to pick it up.", flush=True)
    else:
        print("Pico: no file access approved — file tools will fail. "
              "Restart and approve, or set PICO_SEARCH_ROOTS.", flush=True)
    return grants


def _default_dialog(scope: Path) -> tuple[bool, Path]:
    if sys.platform == "darwin":
        return _macos_dialog(scope)
    return _tkinter_dialog(scope)


def _applescript_text(value: str) -> str:
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def _macos_dialog(scope: Path) -> tuple[bool, Path]:
    """Native Allow/Deny popup via osascript. Raises if it fails."""
    import subprocess

    current = Path(scope)
    while True:
        message = (
            "Pico, running in this terminal, wants full access to your "
            f"files under:\n\n{current}\n\nAllow finding, opening, reading, "
            "writing, organizing, converting, and moving files to trash "
            "(recoverable)?")
        proc = subprocess.run(
            ["osascript", "-e",
             f"display dialog {_applescript_text(message)} "
             'buttons {"Choose folder…", "Deny", "Allow full access"} '
             'default button "Allow full access" cancel button "Deny" '
             'with title "Pico file access" with icon caution'],
            capture_output=True, text=True)
        if proc.returncode != 0:
            return False, current  # Deny, close, Esc, or no GUI session.
        if "Choose folder" in proc.stdout:
            picked = subprocess.run(
                ["osascript", "-e",
                 "POSIX path of (choose folder with prompt "
                 '"Choose a folder for Pico" default location '
                 f"POSIX file {_applescript_text(str(current))})"],
                capture_output=True, text=True)
            if picked.returncode == 0 and picked.stdout.strip():
                current = Path(picked.stdout.strip())
            continue
        return True, current


def _tkinter_dialog(scope: Path) -> tuple[bool, Path]:
    """Blocking Allow/Deny dialog. Raises if no display is available."""
    import tkinter as tk
    from tkinter import filedialog

    choice = {"approved": False, "scope": scope}
    root = tk.Tk()
    root.withdraw()
    try:
        window = tk.Toplevel(root)
        window.title("Pico file access")
        window.configure(bg="#F5F1EE")
        window.resizable(False, False)
        window.attributes("-topmost", True)
        frame = tk.Frame(window, bg="#F5F1EE", padx=16, pady=16)
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text="Allow Pico to access your files?",
                 font=("Helvetica", 16), bg="#F5F1EE", fg="#2B2220",
                 anchor="w", justify="left").pack(fill="x", pady=(0, 8))
        tk.Label(frame,
                 text=("Pico, running in this terminal, wants full access "
                       "to your files under:"),
                 bg="#F5F1EE", fg="#2B2220", anchor="w", justify="left",
                 wraplength=420).pack(fill="x")
        scope_var = tk.StringVar(value=str(scope))
        tk.Label(frame, textvariable=scope_var, font=("Helvetica", 12),
                 bg="#F5F1EE", fg="#2B2220", anchor="w", justify="left",
                 wraplength=420).pack(fill="x", pady=(4, 8))
        tk.Label(frame,
                 text=("Allow finding, opening, reading, writing, "
                       "organizing, converting, and moving files to trash "
                       "(recoverable)? You can narrow this to one folder."),
                 bg="#F5F1EE", fg="#746763", anchor="w", justify="left",
                 wraplength=420).pack(fill="x", pady=(0, 12))

        def choose():
            picked = filedialog.askdirectory(
                parent=window, initialdir=str(choice["scope"]),
                title="Choose a folder for Pico")
            if picked:
                choice["scope"] = Path(picked)
                scope_var.set(picked)

        def allow():
            choice["approved"] = True
            window.destroy()

        def deny():
            window.destroy()

        window.protocol("WM_DELETE_WINDOW", deny)
        buttons = tk.Frame(frame, bg="#F5F1EE")
        buttons.pack(fill="x")
        tk.Button(buttons, text="Choose folder…", command=choose,
                  padx=10, pady=8).pack(side="left")
        tk.Button(buttons, text="Allow full access", command=allow,
                  bg="#B83835", fg="#FFFFFF", padx=10, pady=8).pack(
                      side="right")
        tk.Button(buttons, text="Deny", command=deny,
                  padx=10, pady=8).pack(side="right", padx=(0, 8))
        window.update_idletasks()
        x = (window.winfo_screenwidth() - window.winfo_width()) // 2
        y = (window.winfo_screenheight() - window.winfo_height()) // 3
        window.geometry(f"+{x}+{y}")
        window.lift()
        window.focus_force()
        window.wait_window()  # Blocks until Allow, Deny, or close.
        return choice["approved"], choice["scope"]
    finally:
        root.destroy()
