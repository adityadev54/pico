import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from workspace import Workspace  # noqa: E402
from native_search import NativeError  # noqa: E402


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='pico-workspace-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'hello.txt').write_text('line one\nline two\n')
        (self.root / 'sub').mkdir()
        (self.root / 'sub' / 'inner.md').write_text('# hi\n')
        (self.root / 'blob.bin').write_bytes(bytes(range(256)))
        self.ws = Workspace(self.root)

    def test_list_shows_sorted_bounded_entries(self):
        names = [(e['name'], e['type']) for e in self.ws.list('.')]
        self.assertEqual(names, [('blob.bin', 'file'), ('hello.txt', 'file'), ('sub', 'dir')])
        self.assertEqual(self.ws.list('sub'), [
            {'name': 'inner.md', 'type': 'file', 'size_bytes': 5}])

    def test_read_returns_text_and_full_digest(self):
        import hashlib
        out = self.ws.read('hello.txt')
        self.assertEqual(out['content'], 'line one\nline two\n')
        self.assertFalse(out['truncated'])
        self.assertEqual(out['digest'], hashlib.sha256(b'line one\nline two\n').hexdigest())

    def test_read_reports_binary_without_text(self):
        out = self.ws.read('blob.bin')
        self.assertTrue(out['binary'])
        self.assertNotIn('content', out)
        self.assertEqual(out['size_bytes'], 256)

    def test_read_is_bounded(self):
        out = self.ws.read('hello.txt', limit=4)
        self.assertEqual(out['content'], 'line')
        self.assertTrue(out['truncated'])

    def test_create_then_revise_with_revision(self):
        created = self.ws.write('note.txt', 'v1')
        self.assertEqual((self.root / 'note.txt').read_text(), 'v1')
        revised = self.ws.write('note.txt', 'v2', base_revision=created['digest'])
        self.assertEqual((self.root / 'note.txt').read_text(), 'v2')
        self.assertNotEqual(revised['digest'], created['digest'])

    def test_create_refuses_existing_path(self):
        with self.assertRaises(NativeError) as ctx:
            self.ws.write('hello.txt', 'overwrite?')
        self.assertEqual(ctx.exception.code, 'candidate_changed')
        self.assertEqual((self.root / 'hello.txt').read_text(), 'line one\nline two\n')

    def test_stale_revision_preserves_newer_bytes(self):
        first = self.ws.read('hello.txt')
        (self.root / 'hello.txt').write_text('manual edit wins\n')
        with self.assertRaises(NativeError) as ctx:
            self.ws.write('hello.txt', 'stale write', base_revision=first['digest'])
        self.assertEqual(ctx.exception.code, 'candidate_changed')
        self.assertEqual((self.root / 'hello.txt').read_text(), 'manual edit wins\n')

    def test_escape_absolute_and_symlink_rejected(self):
        for bad in ('../outside.txt', '/etc/hosts', '', 'a\x00b'):
            with self.assertRaises(NativeError, msg=bad):
                self.ws.read(bad)
        (self.root / 'link').symlink_to('/etc/hosts')
        with self.assertRaises(NativeError) as ctx:
            self.ws.read('link')
        self.assertEqual(ctx.exception.code, 'permission_denied')
        outside = Path(self.tmp.name).parent / 'pico-escape-probe.txt'
        try:
            with self.assertRaises(NativeError):
                self.ws.write('../pico-escape-probe.txt', 'x')
            self.assertFalse(outside.exists())
        finally:
            outside.unlink(missing_ok=True)

    def test_trash_and_restore_round_trip(self):
        (self.root / 'old.txt').write_text('bye')
        manifest = self.ws.trash('old.txt')
        self.assertEqual(manifest['original'], 'old.txt')
        self.assertFalse((self.root / 'old.txt').exists())
        back = self.ws.restore('old.txt')
        self.assertEqual(back['path'], 'old.txt')
        self.assertEqual((self.root / 'old.txt').read_text(), 'bye')
        (self.root / 'old.txt').write_text('newer')
        self.ws.trash('old.txt')
        (self.root / 'old.txt').write_text('brand new')
        back = self.ws.restore('old.txt')
        self.assertEqual(back['path'], 'old_2.txt')
        self.assertEqual((self.root / 'old_2.txt').read_text(), 'newer')

    def test_trash_refuses_dirs_missing_and_trash_itself(self):
        with self.assertRaises(NativeError):
            self.ws.trash('sub')
        with self.assertRaises(NativeError):
            self.ws.trash('missing.txt')
        (self.root / 'x.txt').write_text('x')
        self.ws.trash('x.txt')
        with self.assertRaises(NativeError):
            self.ws.trash('.pico-trash')
        with self.assertRaises(NativeError):
            self.ws.restore('never-trashed.txt')

    def test_write_bytes_round_trips_binary(self):
        raw = bytes(range(256)) * 100
        manifest = self.ws.write_bytes('img.jpg', raw)
        self.assertEqual((self.root / 'img.jpg').read_bytes(), raw)
        self.assertEqual(manifest['size_bytes'], len(raw))
        with self.assertRaises(NativeError):
            self.ws.write_bytes('img.jpg', b'other')
        with self.assertRaises(NativeError):
            self.ws.write_bytes('img.jpg', 'text not bytes')

    def test_missing_paths_fail_cleanly(self):
        with self.assertRaises(NativeError):
            self.ws.read('nope.txt')
        with self.assertRaises(NativeError):
            self.ws.list('nope')
        with self.assertRaises(NativeError):
            self.ws.write('nope/nested.txt', 'x')
        with self.assertRaises(NativeError):
            self.ws.write('ghost.txt', 'x', base_revision='0' * 64)

    def test_write_journals_revisions_for_undo(self):
        self.ws.write('note.txt', 'v1')
        out = self.ws.read('note.txt')
        self.ws.write('note.txt', 'v2', out['digest'])
        entries = self.ws.journal_entries()
        self.assertEqual([entry['op'] for _, entry in entries],
                         ['create', 'revise'])
        self.assertTrue(all(entry['path'] == 'note.txt' for _, entry in entries))
        index, revise = entries[1]
        self.assertTrue(revise['backup'])
        self.assertEqual((self.root / revise['backup']).read_bytes(), b'v1')
        self.ws.forget_entry(index)
        self.assertEqual([entry['op'] for _, entry in self.ws.journal_entries()],
                         ['create'])
        self.assertFalse((self.root / revise['backup']).exists())

    def test_journal_normalizes_paths_and_prunes(self):
        (self.root / 'sub').mkdir(exist_ok=True)
        self.ws.write('sub/../note.txt', 'v1')
        entries = self.ws.journal_entries()
        self.assertEqual([entry['path'] for _, entry in entries], ['note.txt'])
        for n in range(510):
            self.ws.note_created(f'f{n}.txt', 'd' * 64)
        entries = self.ws.journal_entries()
        self.assertEqual(len(entries), 410)
        self.assertEqual(entries[0][1]['path'], 'f100.txt')
        self.assertEqual(entries[-1][1]['path'], 'f509.txt')


if __name__ == '__main__':
    unittest.main()
