import sys
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import TOOL_REGISTRY, ToolError  # noqa: E402


class ToolRegistryTests(unittest.TestCase):
    def test_vocabulary_matches_relay_and_contract(self):
        from relay.service import TOOL_NAMES
        from server.contract import SUPPORTED_TOOLS
        self.assertEqual(TOOL_REGISTRY.names(), set(TOOL_NAMES))
        self.assertEqual(set(TOOL_NAMES), set(SUPPORTED_TOOLS))

    def test_list_tools_is_planner_visible(self):
        listed = {t['name']: t for t in TOOL_REGISTRY.list_tools()}
        self.assertEqual(len(listed), 16)
        search = listed['search_documents']
        self.assertIn('query', search['args'])
        self.assertEqual(search['execution_target'], 'helper')
        self.assertIn('folders:read', search['permissions'])
        self.assertTrue(search['available'])
        self.assertFalse(listed['capture_current_tab']['available'])
        self.assertFalse(listed['create_checklist']['available'])
        self.assertFalse(listed['open_resource']['available'])

    def test_valid_calls_pass_and_drop_unknown_keys(self):
        cid = str(uuid.uuid4())
        self.assertEqual(
            TOOL_REGISTRY.validate('search_documents', {'query': 'brief', 'task_id': 't'}),
            {'query': 'brief'})
        self.assertEqual(
            TOOL_REGISTRY.validate('transfer_selected_file',
                                   {'candidate_id': cid, 'approval_id': 'a1'}),
            {'candidate_id': cid, 'approval_id': 'a1'})
        self.assertEqual(
            TOOL_REGISTRY.validate('open_website', {'url': 'https://example.com'}),
            {'url': 'https://example.com'})
        self.assertEqual(
            TOOL_REGISTRY.validate('open_app', {'app': 'vscode'}), {'app': 'vscode'})
        self.assertEqual(TOOL_REGISTRY.validate('manage_permissions', {}), {})
        self.assertEqual(
            TOOL_REGISTRY.validate('fs_write', {'path': 'n.txt', 'content': 'hi'}),
            {'path': 'n.txt', 'content': 'hi'})
        self.assertEqual(
            TOOL_REGISTRY.validate('process_run', {'argv_json': '["echo"]',
                                                   'timeout_s': '10'}),
            {'argv_json': '["echo"]', 'timeout_s': 10})

    def test_unknown_and_unavailable_tools_rejected(self):
        with self.assertRaises(ToolError) as ctx:
            TOOL_REGISTRY.validate('wipe_disk', {})
        self.assertEqual(ctx.exception.code, 'unsupported_tool')
        with self.assertRaises(ToolError) as ctx:
            TOOL_REGISTRY.validate('capture_current_tab', {})
        self.assertEqual(ctx.exception.code, 'unsupported_tool')

    def test_malformed_arguments_rejected_with_field(self):
        cases = [
            ('search_documents', {}, 'query'),
            ('search_documents', {'query': '   '}, 'query'),
            ('search_documents', {'query': 'x' * 501}, 'query'),
            ('search_documents', {'query': 42}, 'query'),
            ('transfer_selected_file', {'candidate_id': 'not-a-uuid', 'approval_id': 'a'}, 'candidate'),
            ('transfer_selected_file', {'candidate_id': str(uuid.uuid4())}, 'approval'),
            ('read_back_file', {'candidate_id': 'zzz'}, 'candidate'),
            ('open_website', {'url': 'http://example.com'}, 'https'),
            ('open_website', {'url': 'notaurl'}, 'https'),
            ('open_app', {'app': 'photoshop'}, 'app'),
            ('open_app', {}, 'app'),
            ('fs_read', {'path': '/etc/hosts'}, 'relative'),
            ('fs_write', {'path': 'n.txt'}, 'content'),
            ('process_run', {'argv_json': '["echo"]', 'timeout_s': 'many'}, 'number'),
            ('process_run', {'argv_json': '["echo"]', 'timeout_s': '999'}, 'range'),
        ]
        for tool, args, hint in cases:
            with self.assertRaises(ToolError, msg=(tool, args)) as ctx:
                TOOL_REGISTRY.validate(tool, args)
            self.assertEqual(ctx.exception.code, 'invalid_args')
            self.assertIn(hint, ctx.exception.message)


if __name__ == '__main__':
    unittest.main()
