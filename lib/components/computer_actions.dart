import 'package:flutter/material.dart';

import '../services/command_parser.dart';
import '../services/pico_store.dart';
import 'computer_target.dart';
import 'workflow_review.dart';

/// The same bounded actions are available from voice, typing and search.
Future<bool> dispatchComputerAction(
  BuildContext context,
  PicoStore store,
  String value,
) async {
  final command = parseComputerCommand(value);
  if (command == null) {
    final ai = museRequestText(value);
    if (ai == null) return false;
    final device = await chooseComputer(context, store);
    if (device == null || !context.mounted) return true;
    final request = ai;
    String? grant;
    if (RegExp(
      r'\b(draft|write|create|edit|save|organize|organise)\b',
      caseSensitive: false,
    ).hasMatch(request)) {
      grant = await chooseWorkspace(context, store, device, write: true);
      if (grant == null || !context.mounted) return true;
    }
    await store.askPico(device, request, grantId: grant);
    return true;
  }
  if (command.kind == 'summarize_document' || command.kind == 'send_file') {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          command.kind == 'send_file'
              ? 'Search for the file, then select Send on its exact result.'
              : 'Select Read on a search result, then tap Summarize with Muse.',
        ),
      ),
    );
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
      ![
        '0.2.0',
        '0.3.0',
        '0.4.0',
        '0.5.0',
        '0.6.0',
        '0.7.0',
      ].contains(helperVersion)) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('update the computer helper from the setup page first.'),
      ),
    );
    return true;
  }
  final input = Map<String, dynamic>.from(command.input);
  if (writeKinds.contains(command.kind) ||
      {'read_file', 'list_files'}.contains(command.kind)) {
    final grant = await chooseWorkspace(
      context,
      store,
      device,
      write: writeKinds.contains(command.kind),
    );
    if (grant == null || !context.mounted) return true;
    input['grant_id'] = grant;
  }
  if (reviewedKinds.contains(command.kind) &&
      (!await reviewWorkflow(context, command.kind, input) ||
          !context.mounted)) {
    return true;
  }
  await store.requestTask(
    device,
    command.kind,
    input,
    confirmed: reviewedKinds.contains(command.kind),
    utterance: value,
  );
  return true;
}
