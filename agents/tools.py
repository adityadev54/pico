"""Typed tool registry for the desktop helper (A04).

One registry carries name, description, argument schema, execution
target, required permissions, idempotency behavior and timeout per tool.
Arguments are validated in code before dispatch; unknown tools and
malformed arguments fail with typed reasons instead of executing.
Folder-grant and path enforcement stays in native_search as a second
layer: the registry validates shape, native_search validates access.
"""
from __future__ import annotations

import uuid
from pathlib import Path

EXECUTION_TARGET = 'helper'


class ToolError(Exception):
    """Typed dispatch failure with a relay-compatible error code."""

    def __init__(self, code: str, message: str):
        self.code, self.message = code, message
        super().__init__(f'{code}: {message}')


class Tool:
    def __init__(self, name, description, args, permissions=(),
                 timeout=30, idempotent=True, available=True):
        # args: {name: {'type': 'str', 'required': bool, 'max_len': int,
        #               'enum': [...], 'format': 'uuid'|'https-url'|'rel-path',
        #               'coerce': 'int', 'min': int, 'max': int}}
        self.name = name
        self.description = description
        self.args = args
        self.permissions = tuple(permissions)
        self.timeout = timeout
        self.idempotent = idempotent
        self.available = available


BUILTIN_TOOLS = (
    Tool('search_documents', 'Find files by name under granted folders.',
         {'query': {'type': 'str', 'required': True, 'max_len': 500},
          'grant_id': {'type': 'str', 'required': False, 'max_len': 128}},
         permissions=('folders:read',)),
    Tool('transfer_selected_file', 'Send the exact approved file to the phone.',
         {'candidate_id': {'type': 'str', 'required': True, 'format': 'uuid'},
          'approval_id': {'type': 'str', 'required': True, 'max_len': 128}},
         permissions=('folders:read',), idempotent=False),
    Tool('read_back_file', 'Return a bounded text excerpt of one file.',
         {'candidate_id': {'type': 'str', 'required': True, 'format': 'uuid'}},
         permissions=('folders:read',)),
    Tool('open_website', 'Open an https URL in the default browser.',
         {'url': {'type': 'str', 'required': True, 'max_len': 2000, 'format': 'https-url'}},
         permissions=('browser:open',)),
    Tool('open_app', 'Open one allowlisted application.',
         {'app': {'type': 'str', 'required': True,
                  'enum': ('calculator', 'calendar', 'vscode', 'browser', 'notes',
                           'chrome', 'safari', 'firefox', 'edge', 'files',
                           'terminal', 'mail', 'photos', 'music', 'messages',
                           'facetime', 'maps', 'settings', 'appstore', 'word',
                           'excel', 'powerpoint')}},
         permissions=('apps:launch',)),
    Tool('manage_permissions', 'Show the Pico permissions window.',
         {}, permissions=()),
    Tool('fs_list', 'List one workspace folder.',
         {'path': {'type': 'str', 'required': False, 'max_len': 512, 'format': 'rel-path'}},
         permissions=('folders:read',)),
    Tool('fs_read', 'Read one workspace file (text or binary manifest).',
         {'path': {'type': 'str', 'required': True, 'max_len': 512, 'format': 'rel-path'}},
         permissions=('folders:read',)),
    Tool('fs_write', 'Create a missing file or revise one by digest. Atomic.',
         {'path': {'type': 'str', 'required': True, 'max_len': 512, 'format': 'rel-path'},
          'content': {'type': 'str', 'required': True, 'max_len': 2000},
          'base_revision': {'type': 'str', 'required': False, 'max_len': 128}},
         permissions=('folders:write',), idempotent=False),
    Tool('delete_files', 'Move one file to Pico trash. Recoverable; needs delete grant + DELETE confirm.',
         {'path': {'type': 'str', 'required': True, 'max_len': 512, 'format': 'rel-path'},
          'confirm': {'type': 'str', 'required': True, 'max_len': 16}},
         permissions=('folders:delete',), idempotent=False),
    Tool('restore_deleted', 'Bring back the latest trashed file by name.',
         {'name': {'type': 'str', 'required': True, 'max_len': 128}},
         permissions=('folders:write',), idempotent=False),
    Tool('convert_file', 'Convert one file: images to pdf/png/jpg/webp, pdf text to txt/docx, docx to pdf.',
         {'path': {'type': 'str', 'required': True, 'max_len': 512, 'format': 'rel-path'},
          'to': {'type': 'str', 'required': True, 'max_len': 8}},
         permissions=('folders:write',), idempotent=False),
    Tool('open_document', 'Open one file, PDF or folder with its default app. Unique match only.',
         {'query': {'type': 'str', 'required': True, 'max_len': 500}},
         permissions=('folders:read',), idempotent=False),
    Tool('rename_file', 'Rename one file within its folder. Never overwrites.',
         {'path': {'type': 'str', 'required': True, 'max_len': 512, 'format': 'rel-path'},
          'new_name': {'type': 'str', 'required': True, 'max_len': 128}},
         permissions=('folders:write',), idempotent=False),
    Tool('duplicate_file', 'Copy one file next to itself with a numbered name.',
         {'path': {'type': 'str', 'required': True, 'max_len': 512, 'format': 'rel-path'}},
         permissions=('folders:write',), idempotent=False),
    Tool('archive', 'Zip files or a folder, or extract one zip. Capped and slip-guarded.',
         {'action': {'type': 'str', 'required': True, 'enum': ('create', 'extract')},
          'paths_json': {'type': 'str', 'required': True, 'max_len': 2000},
          'output': {'type': 'str', 'required': False, 'max_len': 128, 'format': 'rel-path'}},
         permissions=('folders:write',), idempotent=False),
    Tool('recent_files', 'List recently changed files under granted folders.',
         {'days': {'type': 'str', 'required': False, 'coerce': 'int', 'min': 1, 'max': 90}},
         permissions=('folders:read',)),
    Tool('search_contents', 'Find files containing text, with one snippet each.',
         {'query': {'type': 'str', 'required': True, 'max_len': 500}},
         permissions=('folders:read',)),
    Tool('find_duplicates', 'Group byte-identical files by content hash.',
         {},
         permissions=('folders:read',)),
    Tool('largest_files', 'List the largest files under granted folders.',
         {'limit': {'type': 'str', 'required': False, 'coerce': 'int', 'min': 1, 'max': 20}},
         permissions=('folders:read',)),
    Tool('undo_edit', 'Undo one Pico write: restore the saved version or trash an untouched create.',
         {'path': {'type': 'str', 'required': True, 'max_len': 512, 'format': 'rel-path'}},
         permissions=('folders:write',), idempotent=False),
    Tool('empty_trash', 'Permanently clear Pico trash. Needs delete grant + EMPTY confirm.',
         {'confirm': {'type': 'str', 'required': True, 'max_len': 16}},
         permissions=('folders:delete',), idempotent=False),
    Tool('disk_usage', 'Summarize space used across granted folders.',
         {},
         permissions=('folders:read',)),
    Tool('organize_photos', 'Copy each unique photo into one folder. Copy-only; hash dedupe.',
         {'folder': {'type': 'str', 'required': True, 'max_len': 128, 'format': 'rel-path'}},
         permissions=('folders:write',), idempotent=False),
    Tool('fetch_upload', 'Fetch one phone upload by artifact digest and save it.',
         {'artifact_id': {'type': 'str', 'required': True, 'max_len': 64},
          'path': {'type': 'str', 'required': True, 'max_len': 512, 'format': 'rel-path'}},
         permissions=('folders:write',), idempotent=False),
    Tool('process_run', 'Run a command in the workspace. No shell. Bounded.',
         {'argv_json': {'type': 'str', 'required': True, 'max_len': 2000},
          'cwd': {'type': 'str', 'required': False, 'max_len': 512, 'format': 'rel-path'},
          'timeout_s': {'type': 'str', 'required': False, 'coerce': 'int', 'min': 1, 'max': 120}},
         permissions=('process:run',), timeout=120, idempotent=False),
    Tool('pdf_pages', 'Merge, split, rotate, delete, watermark, unlock or rasterize PDF pages.',
         {'action': {'type': 'str', 'required': True,
                     'enum': ('merge', 'split', 'rotate', 'delete', 'watermark',
                              'unlock', 'images')},
          'paths_json': {'type': 'str', 'required': True, 'max_len': 2000},
          'pages': {'type': 'str', 'required': False, 'max_len': 200},
          'angle': {'type': 'str', 'required': False, 'coerce': 'int',
                    'min': 90, 'max': 270},
          'text': {'type': 'str', 'required': False, 'max_len': 64},
          'password': {'type': 'str', 'required': False, 'max_len': 128},
          'output': {'type': 'str', 'required': False, 'max_len': 128,
                     'format': 'rel-path'}},
         permissions=('folders:write',), idempotent=False),
    # Declared for contract compatibility; not implemented on this helper.
    # validate() rejects them with typed reasons instead of executing.
    Tool('capture_current_tab', 'Planned; not implemented on this helper.',
         {}, available=False),
    Tool('create_checklist', 'Planned; not implemented on this helper.',
         {}, available=False),
    Tool('open_resource', 'Planned; not implemented on this helper.',
         {}, available=False),
)


class ToolRegistry:
    def __init__(self, tools=BUILTIN_TOOLS):
        self._tools = {tool.name: tool for tool in tools}

    def names(self):
        return set(self._tools)

    def list_tools(self):
        """Planner-visible inventory: only active tools, with schemas."""
        return [{'name': tool.name, 'description': tool.description,
                 'args': tool.args, 'execution_target': EXECUTION_TARGET,
                 'permissions': list(tool.permissions), 'timeout': tool.timeout,
                 'idempotent': tool.idempotent, 'available': tool.available}
                for tool in self._tools.values()]

    def validate(self, name, raw):
        """Return cleaned args for tool `name`, or raise ToolError."""
        tool = self._tools.get(name)
        if tool is None:
            raise ToolError('unsupported_tool', f'Unknown tool: {name}.')
        if not tool.available:
            raise ToolError('unsupported_tool', f'{name} is not available on this helper.')
        cleaned = {}
        for arg, spec in tool.args.items():
            value = (raw or {}).get(arg)
            if value is None:
                if spec.get('required'):
                    raise ToolError('invalid_args', f'Missing {arg}.')
                continue
            if not isinstance(value, str):
                raise ToolError('invalid_args', f'{arg} must be text.')
            if spec.get('required') and not value.strip():
                raise ToolError('invalid_args', f'Missing {arg}.')
            if len(value) > spec.get('max_len', 2000):
                raise ToolError('invalid_args', f'{arg} is too long.')
            if 'enum' in spec and value not in spec['enum']:
                raise ToolError('invalid_args', f'Unknown {arg}: {value}.')
            if spec.get('format') == 'uuid':
                try:
                    uuid.UUID(value)
                except ValueError:
                    raise ToolError('invalid_args', f'Invalid {arg}.') from None
            if spec.get('format') == 'https-url' and not value.startswith('https://'):
                raise ToolError('invalid_args', f'{arg} must use https.')
            if spec.get('format') == 'rel-path':
                if '\x00' in value or Path(value).is_absolute():
                    raise ToolError('invalid_args', f'{arg} must be a relative path.')
            if spec.get('coerce') == 'int':
                try:
                    number = int(value.strip())
                except ValueError:
                    raise ToolError('invalid_args', f'{arg} must be a number.') from None
                if not spec.get('min', 1) <= number <= spec.get('max', 120):
                    raise ToolError('invalid_args', f'{arg} out of range.')
                cleaned[arg] = number
                continue
            cleaned[arg] = value
        return cleaned


TOOL_REGISTRY = ToolRegistry()
