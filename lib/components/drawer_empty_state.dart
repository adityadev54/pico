import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

class DrawerEmptyState extends StatelessWidget {
  const DrawerEmptyState({super.key, required this.character});
  final String character;
  @override
  Widget build(BuildContext context) => Center(
    child: FittedBox(
      fit: BoxFit.scaleDown,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Stack(
            alignment: Alignment.center,
            children: [
              Transform.rotate(
                angle: -.1,
                child: Container(
                  width: 106,
                  height: 78,
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: .04),
                    borderRadius: BorderRadius.circular(22),
                    border: Border.all(
                      color: Colors.white.withValues(alpha: .08),
                    ),
                  ),
                ),
              ),
              Padding(
                padding: const EdgeInsets.only(bottom: 24),
                child: Image.asset(
                  'assets/characters/$character/idle.png',
                  width: 106,
                  height: 106,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          const Text(
            'No chats yet',
            style: TextStyle(fontSize: 13, color: PicoTheme.drawerMuted),
          ),
        ],
      ),
    ),
  );
}
