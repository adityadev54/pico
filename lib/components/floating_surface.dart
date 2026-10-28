import 'dart:ui';
import 'package:flutter/material.dart';

/// Gita-style frosted controls; tint and geometry are owned by the app.
class FloatingSurface extends StatelessWidget {
  const FloatingSurface({super.key, required this.child, this.radius = 25});
  final Widget child;
  final double radius;
  @override
  Widget build(BuildContext context) {
    final highContrast = MediaQuery.highContrastOf(context);
    return ClipRRect(
      borderRadius: BorderRadius.circular(radius),
      child: BackdropFilter(
        filter: ImageFilter.blur(
          sigmaX: highContrast ? 0 : 8,
          sigmaY: highContrast ? 0 : 8,
        ),
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surface
                .withValues(alpha: highContrast ? 1 : .94),
            borderRadius: BorderRadius.circular(radius),
            border: Border.all(
              color: highContrast
                  ? Theme.of(context).colorScheme.onSurfaceVariant
                  : Theme.of(context).colorScheme.onSurface
                        .withValues(alpha: .08),
              width: highContrast ? 1.5 : .5,
            ),
          ),
          child: child,
        ),
      ),
    );
  }
}
