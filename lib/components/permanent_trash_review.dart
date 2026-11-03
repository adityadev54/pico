import 'package:flutter/material.dart';

import 'pico_dialog.dart';

Future<bool> confirmPermanentTrash(BuildContext context) async =>
    await showPicoDialog<bool>(
      context: context,
      builder: (_) => const _TrashConfirmation(),
    ) ??
    false;

class _TrashConfirmation extends StatefulWidget {
  const _TrashConfirmation();
  @override
  State<_TrashConfirmation> createState() => _TrashConfirmationState();
}

class _TrashConfirmationState extends State<_TrashConfirmation> {
  final controller = TextEditingController();
  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => PicoDialog(
    title: const Text('Permanently empty Pico trash?'),
    content: Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Only Pico’s trash in the selected folder is cleared. This cannot be undone. Type EMPTY to continue; your Mac will also ask for approval.',
        ),
        const SizedBox(height: 12),
        TextField(
          controller: controller,
          autofocus: true,
          onChanged: (_) => setState(() {}),
          decoration: const InputDecoration(hintText: 'Type EMPTY'),
        ),
      ],
    ),
    actions: [
      PicoDialogAction(
        label: 'Cancel',
        onPressed: () => Navigator.pop(context, false),
      ),
      if (controller.text == 'EMPTY')
        PicoDialogAction(
          label: 'Empty permanently',
          destructive: true,
          onPressed: () => Navigator.pop(context, true),
        ),
    ],
  );
}
