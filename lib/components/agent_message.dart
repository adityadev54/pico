import 'package:flutter/material.dart';

import 'chat_bubble_shape.dart';
import 'message_frame.dart';

/// Agent responses share the same surface, including short conversation statuses.
class AgentMessage extends StatelessWidget {
  const AgentMessage({super.key, required this.text});
  final String text;
  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    final style = TextStyle(
      fontSize: 14,
      height: 1.45,
      color: colors.onSurface,
    );
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: MessageFrame(
        mine: false,
        text: text,
        style: style,
        child: Material(
          color: colors.surface,
          shape: const ChatBubbleShape(mine: false),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            child: SelectableText(text, style: style),
          ),
        ),
      ),
    );
  }
}
