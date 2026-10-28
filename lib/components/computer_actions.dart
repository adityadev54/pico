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
  final device = await chooseComputer(context, store, hint: command.deviceHint);
  if (device == null || !context.mounted) return true;
  final helper = store.devices.firstWhere((item) => item['id'] == device);
  if (['open_app', 'manage_permissions'].contains(command.kind) &&
      helper['helper_version'] != '0.3.0') {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text(
          'update the computer helper from pico-relay.fly.dev/setup first.',
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
