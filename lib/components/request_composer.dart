import 'package:flutter/material.dart';
import 'package:heroicons/heroicons.dart';

import 'capsule_input.dart';

class RequestComposer extends StatelessWidget {
  const RequestComposer({
    super.key,
    required this.controller,
    required this.listening,
    required this.busy,
    required this.onVoice,
    required this.onSend,
    this.autofocus = true,
    this.focusNode,
  });
  final TextEditingController controller;
  final FocusNode? focusNode;
  final bool listening, busy, autofocus;
  final VoidCallback onVoice, onSend;
  @override
  Widget build(BuildContext context) => Padding(
    padding: EdgeInsets.fromLTRB(12, 12, 12, 12),
    child: CapsuleInput(
      controller: controller,
      focusNode: focusNode,
      hint: listening ? 'Listening…' : 'Ask or save a thought…',
      icon: HeroIcons.microphone,
      leading: IconButton(
        tooltip: 'Voice',
        onPressed: onVoice,
        icon: HeroIcon(
          HeroIcons.microphone,
          size: 20,
          color: Theme.of(context).colorScheme.onSurfaceVariant,
        ),
      ),
      autofocus: autofocus,
      maxLines: 4,
      inputAction: TextInputAction.send,
      onSubmitted: (_) => onSend(),
      trailing: IconButton(
        tooltip: 'Send',
        onPressed: busy ? null : onSend,
        icon: HeroIcon(
          HeroIcons.arrowUpCircle,
          size: 27,
          color: busy
              ? Theme.of(context).colorScheme.onSurfaceVariant
              : Theme.of(context).colorScheme.primary,
        ),
      ),
    ),
  );
}
