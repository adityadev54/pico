"""Tests for the terminal-run approval popup (agents/grant_popup.py).

The real tkinter dialog cannot run headless, so tests inject a fake
`dialog` callable returning (approved, scope) and verify grant mapping:
approve-all yields one full-access grant, deny/headless yields none,
and explicit grants or --no-popup never trigger the dialog.
"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import grant_popup  # noqa: E402
from grant_popup import request_full_access_popup, startup_grants  # noqa: E402


class GrantPopupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="pico-popup-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_approve_grants_full_access_to_scope(self):
        grants = request_full_access_popup(
            scope=self.root, dialog=lambda scope: (True, scope))
        self.assertEqual(grants, [{"path": str(self.root.resolve()),
                                  "access": "delete",
                                  "source": "popup-approval"}])

    def test_approve_honors_narrowed_folder(self):
        sub = self.root / "docs"
        sub.mkdir()
        grants = request_full_access_popup(
            scope=self.root, dialog=lambda scope: (True, sub))
        self.assertEqual(grants[0]["path"], str(sub.resolve()))
        self.assertEqual(grants[0]["access"], "delete")

    def test_deny_returns_no_grants(self):
        self.assertEqual(
            request_full_access_popup(
                scope=self.root, dialog=lambda scope: (False, scope)),
            [])

    def test_headless_dialog_returns_no_grants(self):
        def boom(scope):
            raise Exception("no display")
        self.assertEqual(
            request_full_access_popup(scope=self.root, dialog=boom), [])

    def test_missing_scope_returns_no_grants(self):
        self.assertEqual(
            request_full_access_popup(
                scope=self.root / "nope",
                dialog=lambda scope: (True, scope)),
            [])

    def test_default_scope_is_home_when_present(self):
        seen = {}

        def dialog(scope):
            seen["scope"] = scope
            return (False, scope)

        request_full_access_popup(dialog=dialog)
        self.assertEqual(seen.get("scope"), grant_popup.default_scope())
        self.assertTrue(seen.get("scope") is None
                        or seen["scope"].is_dir())

    def test_explicit_grants_skip_popup(self):
        explicit = [{"path": str(self.root), "access": "write"}]
        dialog = mock.Mock(side_effect=AssertionError("popup must not run"))
        self.assertEqual(startup_grants(explicit, dialog=dialog), explicit)
        dialog.assert_not_called()

    def test_no_popup_flag_skips_popup(self):
        dialog = mock.Mock(side_effect=AssertionError("popup must not run"))
        self.assertEqual(
            startup_grants([], allow_popup=False, dialog=dialog), [])
        dialog.assert_not_called()

    def test_empty_grants_offer_popup_once(self):
        state_file = self.root / "places.json"
        state_file.write_text('{"grants": [], "paired_device": {"id": "p1"}}')
        dialog = mock.Mock(return_value=(True, self.root))
        with mock.patch.object(grant_popup, "COMPANION_STATE", state_file):
            grants = startup_grants([], dialog=dialog)
        self.assertEqual(len(grants), 1)
        self.assertEqual(grants[0]["access"], "delete")
        dialog.assert_called_once()

    def test_approval_persists_for_companion(self):
        import json
        state_file = self.root / "places.json"
        state_file.write_text('{"grants": [{"id": "old", "path": "%s", '
                              '"access": "read", "source": "cli"}], '
                              '"paired_device": {"id": "p1"}}'
                              % str(self.root.resolve()))
        dialog = mock.Mock(return_value=(True, self.root))
        with mock.patch.object(grant_popup, "COMPANION_STATE", state_file):
            startup_grants([], dialog=dialog)
        saved = json.loads(state_file.read_text())
        self.assertEqual(len(saved["grants"]), 1)
        self.assertEqual(saved["grants"][0]["access"], "delete")
        self.assertEqual(saved["grants"][0]["source"], "popup-approval")
        self.assertEqual(saved["paired_device"], {"id": "p1"})

    def test_persist_skips_missing_state_file(self):
        dialog = mock.Mock(return_value=(True, self.root))
        missing = self.root / "absent" / "places.json"
        with mock.patch.object(grant_popup, "COMPANION_STATE", missing):
            grants = startup_grants([], dialog=dialog)
        self.assertEqual(len(grants), 1)
        self.assertFalse(missing.exists())


class MacosDialogTests(unittest.TestCase):
    """Native popup logic with osascript mocked out (never shows UI)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="pico-popup-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    @staticmethod
    def _proc(returncode=0, stdout=""):
        return mock.Mock(returncode=returncode, stdout=stdout, stderr="")

    def test_allow_returns_scope(self):
        with mock.patch("subprocess.run", return_value=self._proc(
                0, "button returned:Allow full access\n")) as run:
            approved, scope = grant_popup._macos_dialog(self.root)
        self.assertTrue(approved)
        self.assertEqual(scope, self.root)
        self.assertEqual(run.call_count, 1)

    def test_deny_close_returns_not_approved(self):
        with mock.patch("subprocess.run",
                        return_value=self._proc(1, "")):
            approved, scope = grant_popup._macos_dialog(self.root)
        self.assertFalse(approved)
        self.assertEqual(scope, self.root)

    def test_choose_folder_then_allow(self):
        sub = self.root / "docs"
        calls = [self._proc(0, "button returned:Choose folder…\n"),
                 self._proc(0, str(sub) + "\n"),
                 self._proc(0, "button returned:Allow full access\n")]
        with mock.patch("subprocess.run", side_effect=calls) as run:
            approved, scope = grant_popup._macos_dialog(self.root)
        self.assertTrue(approved)
        self.assertEqual(scope, sub)
        self.assertEqual(run.call_count, 3)

    def test_quotes_in_path_are_escaped(self):
        with mock.patch("subprocess.run",
                        return_value=self._proc(1, "")) as run:
            grant_popup._macos_dialog(Path('/tmp/a"b\\c'))
        script = run.call_args[0][0][2]
        self.assertIn('/tmp/a\\"b\\\\c', script)

    def test_dispatch_uses_native_dialog_on_macos(self):
        with mock.patch.object(sys, "platform", "darwin"), \
                mock.patch.object(grant_popup, "_macos_dialog",
                                  return_value=(True, self.root)) as mac, \
                mock.patch.object(grant_popup, "_tkinter_dialog") as tk:
            grant_popup._default_dialog(self.root)
        mac.assert_called_once_with(self.root)
        tk.assert_not_called()

    def test_dispatch_uses_tkinter_elsewhere(self):
        with mock.patch.object(sys, "platform", "win32"), \
                mock.patch.object(grant_popup, "_macos_dialog") as mac, \
                mock.patch.object(grant_popup, "_tkinter_dialog",
                                  return_value=(True, self.root)) as tk:
            grant_popup._default_dialog(self.root)
        tk.assert_called_once_with(self.root)
        mac.assert_not_called()


if __name__ == "__main__":
    unittest.main()
