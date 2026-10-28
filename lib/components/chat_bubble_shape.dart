import 'package:flutter/material.dart';

/// Rounded message with a square upper corner on the speaker's side -- new
class ChatBubbleShape extends RoundedRectangleBorder {
  const ChatBubbleShape({required this.mine});
  final bool mine;
  @override
  BorderRadiusGeometry get borderRadius => BorderRadius.only(
    topLeft: Radius.circular(mine ? 18 : 0),
    topRight: Radius.circular(mine ? 0 : 18),
    bottomLeft: const Radius.circular(18),
    bottomRight: const Radius.circular(18),
  );
  @override
  ShapeBorder scale(double t) => ChatBubbleShape(mine: mine);
}
