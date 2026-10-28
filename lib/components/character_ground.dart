import 'dart:ui';
import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

/// A quiet pool of blue-hour light and contact shadow anchors each character.
class CharacterGround extends StatelessWidget {
  const CharacterGround({super.key});
  @override
  Widget build(BuildContext context) => IgnorePointer(
    child: Stack(
      alignment: Alignment.bottomCenter,
      children: [
        Positioned(
          bottom: 14,
          child: Container(
            width: 200,
            height: 156,
            decoration: BoxDecoration(
              gradient: RadialGradient(
                colors: [
                  PicoTheme.accentSoft.withValues(alpha: .12),
                  PicoTheme.accentSoft.withValues(alpha: 0),
                ],
                stops: const [.15, 1],
              ),
            ),
          ),
        ),
        Positioned(
          bottom: 20,
          child: ImageFiltered(
            imageFilter: ImageFilter.blur(sigmaX: 9, sigmaY: 4),
            child: Container(
              width: 108,
              height: 14,
              decoration: BoxDecoration(
                color: PicoTheme.ink.withValues(alpha: .17),
                borderRadius: BorderRadius.circular(60),
              ),
            ),
          ),
        ),
        Positioned(
          bottom: 23,
          child: ImageFiltered(
            imageFilter: ImageFilter.blur(sigmaX: 3, sigmaY: 2),
            child: Container(
              width: 50,
              height: 5,
              decoration: BoxDecoration(
                color: PicoTheme.ink.withValues(alpha: .12),
                borderRadius: BorderRadius.circular(30),
              ),
            ),
          ),
        ),
      ],
    ),
  );
}
