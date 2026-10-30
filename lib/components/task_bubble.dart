import 'package:crypto/crypto.dart';
import 'package:flutter/material.dart';
import 'package:heroicons/heroicons.dart';
import 'package:share_plus/share_plus.dart';

import '../services/pico_store.dart';
import '../services/computer_tasks.dart';
import 'pico_dialog.dart';
import 'workflow_review.dart';
import 'task_text.dart';
import 'message_frame.dart';
import 'chat_bubble_shape.dart';

class TaskBubble extends StatefulWidget {
  const TaskBubble({super.key, required this.task, required this.store});
  final Map<String, dynamic> task;
  final PicoStore store;
  @override
  State<TaskBubble> createState() => _TaskBubbleState();
}

class _TaskBubbleState extends State<TaskBubble> {
  bool _busy = false;
  Future<void> _receive() async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      final result = Map<String, dynamic>.from(widget.task['result'] ?? {});
      final data = await ComputerTasks(widget.store.client!)
          .download(widget.task['id']);
      if (data.length != result['size_bytes'] ||
          sha256.convert(data).toString() != result['digest']) {
        throw StateError('File digest mismatch');
      }
      await widget.store.submitReceipt(
        task: widget.task['id'],
        size: data.length,
        digest: sha256.convert(data).toString(),
      );
      if (!mounted) return;
      final box = context.findRenderObject() as RenderBox;
      await SharePlus.instance.share(
        ShareParams(
          files: [XFile.fromData(data, mimeType: 'application/octet-stream')],
          fileNameOverrides: [result['name']],
          sharePositionOrigin: box.localToGlobal(Offset.zero) & box.size,
        ),
      );
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('couldn’t download. try again.')),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _deleteFile() async {
    final yes = await showPicoDialog<bool>(
      context: context,
      builder: (context) => PicoDialog(
        title: Text('remove this file?'),
        content: Text('The copy on your computer stays there.'),
        actions: [
          PicoDialogAction(
            label: 'keep',
            onPressed: () => Navigator.pop(context, false),
          ),
          PicoDialogAction(
            label: 'remove',
            destructive: true,
            onPressed: () => Navigator.pop(context, true),
          ),
        ],
      ),
    );
    if (yes != true) return;
    try {
      await ComputerTasks(widget.store.client!).removeFile(widget.task['id']);
      await widget.store.refreshTasks();
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('couldn’t remove. try again.')));
      }
    }
  }

  Future<void> _summarize(String excerpt) async {
    final yes = await showPicoDialog<bool>(
      context: context,
      builder: (context) => PicoDialog(
        title: const Text('Summarize with Muse?'),
        content: const Text(
          'Send up to 1,500 characters from this selected result to Meta/Muse. One paid request within your test limits. Nothing runs automatically.',
        ),
        actions: [
          PicoDialogAction(
            label: 'Cancel',
            onPressed: () => Navigator.pop(context, false),
          ),
          PicoDialogAction(
            label: 'Summarize',
            primary: true,
            onPressed: () => Navigator.pop(context, true),
          ),
        ],
      ),
    );
    if (yes == true) await widget.store.summarizeTask(widget.task['id']);
  }

  Future<void> _approveProposal() async {
    final input = Map<String, dynamic>.from(widget.task['input'] ?? {});
    final kind = widget.task['kind'] as String;
    final device = widget.store.devices
        .where((d) => d['id'] == widget.task['device_id'])
        .firstOrNull;
    final folders = (device?['workspaces'] as List? ?? []).whereType<Map>();
    final existingGrant = folders.any(
      (g) => g['id'] == input['grant_id'] && g['access'] == 'write',
    );
    if (writeKinds.contains(kind) && !existingGrant) {
      final grant = await chooseWorkspace(
        context,
        widget.store,
        widget.task['device_id'],
        write: true,
      );
      if (grant == null || !mounted) return;
      input['grant_id'] = grant;
    }
    if (!await reviewWorkflow(context, kind, input) || !mounted) return;
    await widget.store.approveTask(
      widget.task['id'],
      grant: input['grant_id'] as String?,
    );
  }

  Future<void> _editFile(Map<String, dynamic> result) async {
    final text = TextEditingController(text: result['content'] as String);
    final content = await showPicoDialog<String>(
      context: context,
      builder: (context) => PicoDialog(
        title: const Text('Edit file'),
        content: TextField(
          controller: text,
          maxLines: 8,
          maxLength: 2000,
          decoration: const InputDecoration(hintText: 'File contents'),
        ),
        actions: [
          PicoDialogAction(
            label: 'Cancel',
            onPressed: () => Navigator.pop(context),
          ),
          PicoDialogAction(
            label: 'Review',
            primary: true,
            onPressed: () => Navigator.pop(context, text.text),
          ),
        ],
      ),
    );
    // The route transition may still render the field; dispose after it finishes.
    Future<void>.delayed(const Duration(seconds: 1), text.dispose);
    if (content == null || !mounted) return;
    final grant = await chooseWorkspace(
      context,
      widget.store,
      widget.task['device_id'],
      write: true,
    );
    if (grant == null || !mounted) return;
    final input = {
      'name': result['path'],
      'text': content,
      'base_revision': result['digest'],
      'grant_id': grant,
    };
    if (!await reviewWorkflow(context, 'edit_file', input) || !mounted) return;
    await widget.store.requestTask(
      widget.task['device_id'],
      'edit_file',
      input,
      confirmed: true,
    );
  }

  @override
  Widget build(BuildContext context) {
    final task = widget.task;
    final result = Map<String, dynamic>.from(task['result'] ?? {});
    final status = task['status'];
    final labels = {
      'queued':
          widget.store.devices.any(
            (device) =>
                device['id'] == task['device_id'] &&
                ![
                  '0.2.0',
                  '0.3.0',
                  '0.4.0',
                  '0.5.0',
                  '0.6.0',
                  '0.7.0',
                  null,
                ].contains(device['helper_version']),
          )
          ? 'queued · update pico on your computer'
          : 'Queued · waiting for your computer',
      'awaiting_approval': result['proposal'] != null
          ? 'Review before running'
          : 'Choose the exact file',
      'working': 'Working on your computer',
      'verifying': 'Checking received file',
      'completed': result['receipt'] == 'verified' ? 'Done · verified' : 'Done',
      'cancelled': 'cancelled',
      'failed': result['error_code'] is String
          ? 'Couldn’t finish · ${result['error_code']}'
          : 'Couldn’t finish',
    };
    final title = {
      'send_file': 'File to phone',
      'find_document': 'Document search',
      'open_website': 'Open website',
      'open_app': 'Open app',
      'manage_permissions': 'Permissions',
      'create_note': 'Note',
      'receive_upload': 'Upload',
      'organize_photos': 'Photos',
      'open_document': 'Open document',
      'read_document': 'Read document',
      'read_file': 'Read file',
      'list_files': 'Files',
      'edit_file': 'Edit file',
      'run_command': 'Command',
    };
    final candidates = (result['candidates'] as List?)
        ?.map((e) => Map<String, dynamic>.from(e))
        .toList();
    final bubbleText = [
      result['message'],
      result['content'],
      result['excerpt'],
      result['summary'],
      task['input'] is Map ? task['input']['text'] : null,
      if (candidates != null) ...candidates.map((c) => c['name']),
    ].whereType<String>().join('\n');
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: MessageFrame(
        mine: false,
        text: bubbleText,
        minimumWidth: 240,
        style: const TextStyle(fontSize: 15, height: 1.45),
        child: Material(
          color: Theme.of(context).colorScheme.surface,
          shape: const ChatBubbleShape(mine: false),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        '${widget.store.character[0].toUpperCase()}${widget.store.character.substring(1)}',
                        semanticsLabel:
                            '${widget.store.character}: ${title[task['kind']] ?? 'Request'}',
                        style: TextStyle(fontWeight: FontWeight.w600),
                      ),
                    ),
                    if ((result['file_path'] != null ||
                            result['artifact_id'] != null) &&
                        (status == 'completed' || status == 'verifying'))
                      IconButton(
                        tooltip: 'save or share file',
                        onPressed: _busy ? null : _receive,
                        icon: _busy
                            ? SizedBox(
                                width: 18,
                                height: 18,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                ),
                              )
                            : HeroIcon(
                                HeroIcons.arrowDownTray,
                                size: 21,
                                color: Theme.of(context)
                                    .colorScheme
                                    .onSurfaceVariant,
                              ),
                      ),
                    if ((result['file_path'] != null ||
                            result['artifact_id'] != null) &&
                        status == 'completed')
                      IconButton(
                        tooltip: 'remove transferred file',
                        onPressed: _deleteFile,
                        icon: HeroIcon(
                          HeroIcons.trash,
                          size: 19,
                          color: Theme.of(context).colorScheme.onSurfaceVariant,
                        ),
                      ),
                    if ([
                      'queued',
                      'awaiting_approval',
                      'working',
                      'verifying',
                    ].contains(status))
                      IconButton(
                        tooltip: 'cancel request',
                        onPressed: () => widget.store.cancelTask(task['id']),
                        icon: HeroIcon(
                          HeroIcons.xMark,
                          size: 19,
                          color: Theme.of(context).colorScheme.onSurfaceVariant,
                        ),
                      ),
                  ],
                ),
                Text(
                  labels[status] ?? status,
                  style: TextStyle(
                    fontSize: 12,
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
                ),
                if (result['message'] is String)
                  Padding(
                    padding: EdgeInsets.only(top: 10),
                    child: Text(
                      result['message'],
                      style: TextStyle(fontSize: 14),
                    ),
                  ),
                if (result['name'] is String)
                  Text(result['name'], style: TextStyle(fontSize: 14)),
                if (result['proposal'] != null && status == 'awaiting_approval')
                  Padding(
                    padding: const EdgeInsets.only(top: 12),
                    child: FilledButton.tonal(
                      onPressed: _approveProposal,
                      child: const Text('Review action'),
                    ),
                  ),
                if (candidates != null && status == 'awaiting_approval')
                  for (final candidate in candidates)
                    Padding(
                      padding: EdgeInsets.only(top: 8),
                      child: Row(
                        children: [
                          Expanded(
                            child: Text(
                              '${candidate['name']} · ${_sizeLabel(candidate['size_bytes'])}',
                              style: TextStyle(fontSize: 13),
                            ),
                          ),
                          IconButton(
                            tooltip: 'Read file',
                            onPressed: () =>
                                widget.store.readCandidate(task, candidate),
                            icon: HeroIcon(
                              HeroIcons.documentText,
                              size: 20,
                              color: Theme.of(context)
                                  .colorScheme
                                  .onSurfaceVariant,
                            ),
                          ),
                          FilledButton.tonal(
                            onPressed: () async {
                              if (!await reviewWorkflow(
                                    context,
                                    'Send selected file',
                                    {
                                      'name': candidate['name'],
                                      'size_bytes': candidate['size_bytes'],
                                    },
                                  ) ||
                                  !mounted) {
                                return;
                              }
                              await widget.store.approveTransfer(
                                device: task['device_id'],
                                searchTask: task,
                                candidate: candidate,
                              );
                            },
                            child: Text('Send'),
                          ),
                        ],
                      ),
                    ),
                if (result['matches'] is List && candidates == null)
                  for (final match in result['matches'])
                    Padding(
                      padding: EdgeInsets.only(top: 6),
                      child: Text(
                        match.toString(),
                        style: TextStyle(fontSize: 13),
                      ),
                    ),
                if (result['content'] is String &&
                    result['digest'] is String &&
                    result['path'] is String)
                  Align(
                    alignment: Alignment.centerRight,
                    child: TextButton.icon(
                      onPressed: () => _editFile(result),
                      icon: HeroIcon(
                        HeroIcons.pencilSquare,
                        size: 18,
                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                      ),
                      label: const Text('Edit file'),
                    ),
                  ),
                if (task['kind'] == 'create_note' &&
                    result['content'] == null &&
                    task['input'] is Map &&
                    task['input']['text'] is String &&
                    (task['input']['text'] as String).isNotEmpty)
                  TaskText(task['input']['text'] as String),
                if (result['content'] is String)
                  TaskText(result['content'] as String),
                if (result['excerpt'] is String)
                  TaskText(result['excerpt'] as String),
                if (result['stdout'] is String)
                  TaskText(result['stdout'] as String),
                if (result['entries'] is List)
                  for (final entry in (result['entries'] as List).take(20))
                    Padding(
                      padding: const EdgeInsets.only(top: 6),
                      child: Text(entry['name'] as String),
                    ),
                if (result['summary'] is String)
                  TaskText(result['summary'] as String),
                if ((result['excerpt'] is String ||
                        result['content'] is String) &&
                    (result['excerpt'] ?? result['content'] as String)
                        .isNotEmpty &&
                    widget.store.museState == 'ready')
                  Align(
                    alignment: Alignment.centerRight,
                    child: IconButton(
                      tooltip: 'Summarize with Muse',
                      onPressed: widget.store.busy
                          ? null
                          : () => _summarize(
                              (result['excerpt'] ?? result['content'])
                                  as String,
                            ),
                      icon: HeroIcon(
                        HeroIcons.documentText,
                        size: 21,
                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  String _sizeLabel(dynamic bytes) {
    if (bytes is! int) return '';
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
    return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
  }
}
