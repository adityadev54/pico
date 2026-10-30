import 'package:flutter/material.dart';

/// Results grow with the conversation; only the conversation itself scrolls.
class TaskText extends StatelessWidget {
  const TaskText(this.text, {super.key});
  final String text;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(top: 12),
    child: SelectionArea(
      child: Text(text, style: const TextStyle(fontSize: 15, height: 1.45)),
    ),
  );
}
