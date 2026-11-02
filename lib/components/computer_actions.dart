import 'package:flutter/material.dart';

import '../services/command_parser.dart';
import '../services/local_play.dart';
import '../services/pico_store.dart';
import 'computer_target.dart';
import 'workflow_review.dart';

/// Answers greetings and capability questions locally, with no computer
/// needed. Returns true when the input was small-talk.
Future<bool> answerSmallTalk(PicoStore store, String value) async {
  final reply = picoSmallTalk(value);
  if (reply == null) return false;
  await store.savePlace(value);
  await store.saveAssistantReply(reply);
  return true;
}

/// Answers phone-local play (games, riddles, timers, reminders) and pending
/// follow-ups. Real computer commands always pass through untouched.
Future<bool> answerLocalPlay(PicoStore store, String value) async {
  final command = parseLocalPlay(value);
  if (command != null) {
    await store.savePlace(value);
    await store.saveAssistantReply(store.runLocalCommand(command));
    return true;
  }
  final pending = store.pendingPrompt;
  if (pending == null) return false;
  if (parseComputerCommand(value) != null) return false;
  final speech = value.trim().replaceAll(RegExp(r'[.!?]+$'), '');
  if (isLocalStop(speech)) {
    await store.savePlace(value);
    if (pending['kind'] == 'riddle' &&
        RegExp(r'^give up$', caseSensitive: false).hasMatch(speech)) {
      await store.saveAssistantReply(store.giveUpRiddle());
    } else {
      await store.saveAssistantReply(store.cancelPendingPrompt());
    }
    return true;
  }
  final String? reply = switch (pending['kind']) {
    'guess' => store.guessTurn(speech),
    'riddle' =>
      speech.toLowerCase() == 'another' || speech.toLowerCase() == 'another one'
          ? store.startRiddle()
          : store.riddleTurn(speech),
    'reminder_time' => store.reminderTimeTurn(speech),
    _ => null,
  };
  if (reply == null) return false;
  await store.savePlace(value);
  await store.saveAssistantReply(reply);
  return true;
}

/// Kinds that run without any folder grant.
bool _needsNoFolder(String kind) =>
    const {'open_app', 'open_website', 'manage_permissions'}.contains(kind);

/// Read-only kinds the computer can one-time grant: find and open go
/// through with zero folders so the helper asks once, then never again.
bool _asksOnceOnComputer(String kind) =>
    const {'find_document', 'open_document'}.contains(kind);

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
  if (command.kind == 'delete_files') {
    final names = (command.input['names'] as List).cast<String>();
    if (names.length > 5) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('delete up to 5 files at a time.')),
      );
      return true;
    }
    final device = await chooseComputer(context, store, hint: command.deviceHint);
    if (device == null || !context.mounted) return true;
    final target = store.devices.firstWhere((item) => item['id'] == device);
    if ((target['workspaces'] as List?)?.isEmpty == true) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Choose an approved folder on your computer first.'),
        ),
      );
      return true;
    }
    // Every file gets its own popup; cancelling stops the batch and
    // keeps the remaining files unasked and undeleted.
    for (final name in names) {
      if (!context.mounted) return true;
      if (!await reviewWorkflow(context, command.kind, {'path': name}) ||
          !context.mounted) {
        return true;
      }
      await store.requestTask(
        device,
        'delete_files',
        {'path': name, 'confirm': 'DELETE'},
        utterance: value,
        confirmed: true,
      );
    }
    return true;
  }
  final device = await chooseComputer(context, store, hint: command.deviceHint);
  if (device == null || !context.mounted) return true;
  final helper = store.devices.firstWhere((item) => item['id'] == device);
  if (!_needsNoFolder(command.kind) &&
      !_asksOnceOnComputer(command.kind) &&
      (helper['workspaces'] as List?)?.isEmpty == true) {
    // The computer reports zero granted folders: explain before queuing
    // a task the helper can only refuse. Missing data (old helper)
    // still goes through; the helper answers honestly.
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Choose an approved folder on your computer first.'),
      ),
    );
    return true;
  }
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
  if (_asksOnceOnComputer(command.kind) &&
      (helper['workspaces'] as List?)?.isEmpty == true &&
      context.mounted) {
    // First find/open with no folders: the computer is about to ask for
    // the one-time grant, so point the user at that popup.
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text(
          'Check your computer too — approve the folder request there.',
        ),
      ),
    );
  }
  return true;
}
