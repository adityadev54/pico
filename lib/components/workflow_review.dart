import 'dart:convert';

import 'package:flutter/material.dart';

import '../services/pico_store.dart';
import 'pico_dialog.dart';
import 'pico_sheet.dart';

const reviewedKinds = {
  'create_note',
  'edit_file',
  'receive_upload',
  'run_command',
  'organize_photos',
  'open_website',
  'open_document',
};
const writeKinds = {
  'create_note',
  'edit_file',
  'receive_upload',
  'run_command',
  'organize_photos',
};

Map<String, dynamic> _reviewDetails(Map<String, dynamic> input) {
  const labels = {
    'name': 'File',
    'path': 'File',
    'text': 'Contents',
    'content': 'Contents',
    'folder': 'Destination folder',
    'argv': 'Command arguments',
    'argv_json': 'Command arguments',
    'cwd': 'Working folder',
    'url': 'Website',
    'size_bytes': 'Size in bytes',
    'timeout_s': 'Time limit in seconds',
  };
  return {
    for (final item in input.entries)
      if (labels.containsKey(item.key)) labels[item.key]!: item.value,
  };
}

Future<bool> reviewWorkflow(
  BuildContext context,
  String kind,
  Map<String, dynamic> input,
) async =>
    await showPicoSheet<bool>(
      context: context,
      builder: (context) => PicoDialog(
        title: const Text('Review this action'),
        content: ConstrainedBox(
          constraints: const BoxConstraints(maxHeight: 280),
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(kind.replaceAll('_', ' ')),
                const SizedBox(height: 12),
                for (final detail in _reviewDetails(input).entries)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          detail.key,
                          style: Theme.of(context).textTheme.labelMedium,
                        ),
                        const SizedBox(height: 4),
                        SelectableText(
                          detail.value is String
                              ? detail.value as String
                              : jsonEncode(detail.value),
                        ),
                      ],
                    ),
                  ),
                const SizedBox(height: 12),
                const Text(
                  'Approved file actions run in your selected workspace. Commands still need approval on your computer.',
                ),
              ],
            ),
          ),
        ),
        actions: [
          PicoDialogAction(
            label: 'Cancel',
            onPressed: () => Navigator.pop(context, false),
          ),
          PicoDialogAction(
            label: 'Approve',
            primary: true,
            onPressed: () => Navigator.pop(context, true),
          ),
        ],
      ),
    ) ??
    false;

Future<String?> chooseWorkspace(
  BuildContext context,
  PicoStore store,
  String device, {
  bool write = false,
}) async {
  final row = store.devices.where((d) => d['id'] == device).firstOrNull;
  final workspaces = (row?['workspaces'] as List? ?? [])
      .whereType<Map>()
      .where((g) => !write || g['access'] == 'write')
      .toList();
  if (workspaces.isEmpty) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          write
              ? 'Choose a write workspace in Pico’s computer permissions first.'
              : 'Choose an approved folder on your computer first.',
        ),
      ),
    );
    return null;
  }
  if (workspaces.length == 1) return workspaces.single['id'] as String;
  return showPicoDialog<String>(
    context: context,
    builder: (context) => PicoDialog(
      title: const Text('Choose a folder'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            for (final g in workspaces)
              ListTile(
                title: Text(g['name'] as String),
                subtitle: Text(g['access'] as String),
                onTap: () => Navigator.pop(context, g['id'] as String),
              ),
          ],
        ),
      ),
      actions: [
        PicoDialogAction(
          label: 'Cancel',
          onPressed: () => Navigator.pop(context),
        ),
      ],
    ),
  );
}
