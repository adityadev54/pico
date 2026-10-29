import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from native_search import (  # noqa: E402
    NativeError,
    candidate_id_for,
    digest_of,
    read_excerpt,
    resolve_candidate,
    search_documents,
    transfer_evidence,
)


class NativeSearchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='pico-native-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'project-brief.txt').write_text('hello brief')
        (self.root / 'notes.md').write_text('other')
        (self.root / 'sub').mkdir()
        (self.root / 'sub' / 'brief-v2.txt').write_text('v2')
        self.grants = [{'path': str(self.root)}]

    def test_search_matches_filenames_case_insensitively(self):
        names = sorted(c['name'] for c in search_documents('BRIEF', self.grants))
        self.assertEqual(names, ['brief-v2.txt', 'project-brief.txt'])

    def test_search_misses_raise_no_match(self):
        with self.assertRaises(NativeError) as ctx:
            search_documents('zzz-no-such-file', self.grants)
        self.assertEqual(ctx.exception.code, 'no_match')
        with self.assertRaises(NativeError):
            search_documents('   ', self.grants)

    def test_search_needs_a_grant(self):
        with self.assertRaises(NativeError) as ctx:
            search_documents('brief', [{'path': str(self.root / 'missing')}])
        self.assertEqual(ctx.exception.code, 'permission_denied')

    def test_evidence_is_stable_until_file_changes(self):
        candidate = search_documents('project-brief', self.grants)[0]
        before = transfer_evidence(candidate['candidate_id'], self.grants)
        self.assertEqual(before['name'], 'project-brief.txt')
        (self.root / 'project-brief.txt').write_text('changed bytes here!!')
        after = transfer_evidence(candidate['candidate_id'], self.grants)
        self.assertNotEqual(after['digest'], before['digest'])

    def test_unknown_candidate_fails_closed(self):
        with self.assertRaises(NativeError) as ctx:
            resolve_candidate('00000000-0000-0000-0000-000000000000', self.grants)
        self.assertEqual(ctx.exception.code, 'candidate_changed')

    def test_candidate_ids_are_stable_paths(self):
        path = self.root / 'notes.md'
        self.assertEqual(candidate_id_for(path), candidate_id_for(path))
        self.assertEqual(resolve_candidate(candidate_id_for(path), self.grants), path.resolve())

    def test_excerpt_returns_text_and_skips_binary(self):
        candidate = search_documents('project-brief', self.grants)[0]
        self.assertIn('hello', read_excerpt(candidate['candidate_id'], self.grants))
        (self.root / 'blob.bin').write_bytes(bytes(range(256)))
        binary = search_documents('blob', self.grants)[0]
        self.assertEqual(read_excerpt(binary['candidate_id'], self.grants), '')

    def test_digest_matches_sha256(self):
        import hashlib
        path = self.root / 'notes.md'
        self.assertEqual(digest_of(path), hashlib.sha256(path.read_bytes()).hexdigest())


if __name__ == '__main__':
    unittest.main()
