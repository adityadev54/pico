import 'package:flutter/material.dart';

/// Soft, directional chat bubbles with a small lower speaker tail.
class ChatBubbleShape extends RoundedRectangleBorder {
  const ChatBubbleShape({required this.mine});
  final bool mine;
  @override
  BorderRadiusGeometry get borderRadius => BorderRadius.only(
    topLeft: const Radius.circular(20),
    topRight: const Radius.circular(20),
    bottomLeft: Radius.circular(mine ? 20 : 5),
    bottomRight: Radius.circular(mine ? 5 : 20),
  );
  @override
  Path getOuterPath(Rect rect, {TextDirection? textDirection}) {
    final body = Path()
      ..addRRect(borderRadius.resolve(textDirection).toRRect(rect));
    final x = mine ? rect.right : rect.left;
    final direction = mine ? 1.0 : -1.0;
    final tail = Path()
      ..moveTo(x - direction * 9, rect.bottom - 13)
      ..quadraticBezierTo(x, rect.bottom - 8, x + direction * 4, rect.bottom)
      ..quadraticBezierTo(
        x - direction * 8,
        rect.bottom + 1,
        x - direction * 13,
        rect.bottom - 3,
      )
      ..close();
    return Path.combine(PathOperation.union, body, tail);
  }

  @override
  Path getInnerPath(Rect rect, {TextDirection? textDirection}) =>
      getOuterPath(rect, textDirection: textDirection);
  @override
  ShapeBorder scale(double t) => ChatBubbleShape(mine: mine);
}
