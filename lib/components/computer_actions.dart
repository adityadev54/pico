import 'package:flutter/material.dart';
import '../services/command_parser.dart';
import '../services/pico_store.dart';
import 'computer_target.dart';

/// The same bounded actions are available from voice, typing and search.
Future<bool> dispatchComputerAction(
  BuildContext context,
  PicoStore store,
  String value,
) async {
  final command = parseComputerCommand(value);
  if (command == null) return false;
  if (command.kind == 'summarize_document') {
    final docs = store.tasks.reversed.where(
      (task) =>
          task['status'] == 'completed' &&
          (task['result']?['excerpt'] as String? ?? '').isNotEmpty,
    );
    if (docs.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('find a document first, then ask for a summary.'),
        ),
      );
    } else {
      await store.summarizeDocument(docs.first['result']['excerpt']);
    }
    return true;
  }
  if (command.kind == 'steer_output') {
    final notes = store.tasks.where(
      (task) => task['kind'] == 'create_note' && task['status'] == 'queued',
    );
    if (notes.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('nothing to rename right now — create a note first.'),
        ),
      );
    } else {
      await store.steerTask(notes.first['id'], command.input['path']);
    }
    return true;
  }
  final device = await chooseComputer(context, store, hint: command.deviceHint);
  if (device == null || !context.mounted) return true;
  final helper = store.devices.firstWhere((item) => item['id'] == device);
  final helperVersion = helper['helper_version'] as String?;
  if (['open_app', 'manage_permissions'].contains(command.kind) &&
      helperVersion != null &&
      !['0.2.0', '0.3.0'].contains(helperVersion)) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text(
          'update the computer helper from the setup page first.',
        ),
      ),
    );
    return true;
  }
  await store.requestTask(
    device,
    command.kind,
    command.input,
    utterance: value,
  );
  return true;
}
