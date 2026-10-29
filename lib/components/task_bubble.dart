import 'package:crypto/crypto.dart';
import 'package:flutter/material.dart';
import 'package:heroicons/heroicons.dart';
import 'package:share_plus/share_plus.dart';
import '../services/pico_store.dart';
import '../services/computer_tasks.dart';
import 'pico_dialog.dart';

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
      final data = await widget.store.client!.storage
          .from('pico-transfers')
          .download(
            result['file_path'],
            cacheNonce: DateTime.now().microsecondsSinceEpoch.toString(),
          );
      // Authenticated phone receipt: report received size/digest for verification.
      try {
        await widget.store.submitReceipt(
          task: widget.task['id'],
          size: data.length,
          digest: sha256.convert(data).toString(),
        );
      } catch (_) {
        // Download succeeded; receipt retry happens on next open.
      }
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

  void _summarize(String excerpt) {
    final sessions = widget.store.sessions.where(
      (session) => session.id == widget.task['session_id'],
    );
    if (sessions.isNotEmpty) widget.store.select(sessions.first);
    Navigator.popUntil(context, (route) => route.isFirst);
    widget.store.summarizeDocument(excerpt);
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
                !['0.2.0', '0.3.0', null].contains(device['helper_version']),
          )
          ? 'queued · update pico on your computer'
          : 'queued · waiting for your computer',
      'awaiting_approval': 'select the exact file to transfer',
      'working': 'working on your computer',
      'verifying': 'checking received file',
      'completed': result['receipt'] == 'verified' ? 'done · verified' : 'done',
      'cancelled': 'cancelled',
      'failed': result['error_code'] is String
          ? 'couldn’t finish · ${result['error_code']}'
          : 'couldn’t finish',
    };
    final title = {
      'send_file': 'file to phone',
      'find_document': 'document search',
      'open_website': 'open website',
      'open_app': 'open app',
      'manage_permissions': 'permissions',
      'create_note': 'note',
      'receive_upload': 'upload',
      'organize_photos': 'photos',
      'open_document': 'open document',
    };
    final candidates = (result['candidates'] as List?)
        ?.map((e) => Map<String, dynamic>.from(e))
        .toList();
    return Container(
      margin: EdgeInsets.only(bottom: 16, right: 30),
      padding: EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(22),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  title[task['kind']] ?? 'request',
                  style: TextStyle(fontWeight: FontWeight.w600),
                ),
              ),
              if (result['file_path'] != null &&
                  (status == 'completed' || status == 'verifying'))
                IconButton(
                  tooltip: 'save or share file',
                  onPressed: _busy ? null : _receive,
                  icon: _busy
                      ? SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : HeroIcon(HeroIcons.arrowDownTray, size: 21),
                ),
              if (result['file_path'] != null && status == 'completed')
                IconButton(
                  tooltip: 'remove transferred file',
                  onPressed: _deleteFile,
                  icon: HeroIcon(HeroIcons.trash, size: 19),
                ),
              if (['queued', 'awaiting_approval', 'working', 'verifying']
                  .contains(status))
                IconButton(
                  tooltip: 'cancel request',
                  onPressed: () => widget.store.cancelTask(task['id']),
                  icon: HeroIcon(HeroIcons.xMark, size: 19),
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
              child: Text(result['message'], style: TextStyle(fontSize: 14)),
            ),
          if (result['name'] is String)
            Text(result['name'], style: TextStyle(fontSize: 14)),
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
                    FilledButton.tonal(
                      onPressed: () => widget.store.approveTransfer(
                        device: task['device_id'],
                        searchTask: task,
                        candidate: candidate,
                      ),
                      child: Text('Send'),
                    ),
                  ],
                ),
              ),
          if (result['matches'] is List && candidates == null)
            for (final match in result['matches'])
              Padding(
                padding: EdgeInsets.only(top: 6),
                child: Text(match.toString(), style: TextStyle(fontSize: 13)),
              ),
          if (result['excerpt'] is String &&
              (result['excerpt'] as String).isNotEmpty)
            Align(
              alignment: Alignment.centerRight,
              child: IconButton(
                tooltip: 'summarize document',
                onPressed: widget.store.busy
                    ? null
                    : () => _summarize(result['excerpt']),
                icon: HeroIcon(HeroIcons.documentText, size: 21),
              ),
            ),
        ],
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
