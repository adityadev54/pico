import 'dart:math' as math;

import 'package:flutter/material.dart';

/// Fit short messages to their content, and cap long ones for readable wrapping.
class MessageFrame extends StatelessWidget {
  const MessageFrame({
    super.key,
    required this.mine,
    required this.text,
    required this.style,
    required this.child,
    this.detail,
    this.detailStyle,
    this.minimumWidth = 0,
  });
  final bool mine;
  final double minimumWidth;
  final String text;
  final TextStyle style;
  final String? detail;
  final TextStyle? detailStyle;
  final Widget child;
  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final limit = math.min(520.0, constraints.maxWidth * .88);
      double measure(String value, TextStyle style) {
        final painter = TextPainter(
          text: TextSpan(
            text: value,
            style: DefaultTextStyle.of(context).style.merge(style),
          ),
          textDirection: Directionality.of(context),
          textScaler: MediaQuery.textScalerOf(context),
        )..layout(maxWidth: math.max(1, limit - 28));
        final width = painter.maxIntrinsicWidth;
        painter.dispose();
        return width;
      }

      final natural = math.max(
        measure(text, style),
        detail == null ? 0.0 : measure(detail!, detailStyle ?? style),
      );
      final width = math.min(limit, math.max(minimumWidth, natural + 32));
      return Align(
        alignment: mine ? Alignment.centerRight : Alignment.centerLeft,
        child: SizedBox(width: width, child: child),
      );
    },
  );
}
