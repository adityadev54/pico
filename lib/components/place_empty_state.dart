import 'package:flutter/material.dart';
import 'package:heroicons/heroicons.dart';
import 'character_ground.dart';
import 'floating_surface.dart';

class PlaceEmptyState extends StatelessWidget {
  const PlaceEmptyState({
    super.key,
    required this.character,
    required this.typing,
    this.scale = 1,
    this.mood = 'idle',
    this.onVoice,
    required this.onCompose,
  });
  final String character, mood;
  final bool typing;
  final double scale;
  final VoidCallback onCompose;
  final VoidCallback? onVoice;
  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final compact = constraints.maxHeight < 400;
      return SingleChildScrollView(
        child: ConstrainedBox(
          constraints: BoxConstraints(minHeight: constraints.maxHeight),
          child: Padding(
            padding: EdgeInsets.symmetric(vertical: 16),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                SizedBox(
                  width: 210,
                  height: (compact ? 100 : 174) * scale,
                  child: Stack(
                    alignment: Alignment.bottomCenter,
                    children: [
                      Positioned.fill(child: CharacterGround()),
                      GestureDetector(
                        onDoubleTap: onVoice,
                        child: Image.asset(
                          'assets/characters/$character/$mood.${MediaQuery.disableAnimationsOf(context) ? 'png' : 'gif'}',
                          width: (compact ? 100 : 162) * scale,
                          height: (compact ? 100 : 162) * scale,
                          gaplessPlayback: true,
                          semanticLabel: 'Your Pico companion, $character',
                        ),
                      ),
                    ],
                  ),
                ),
                SizedBox(height: 16),
                Text(
                  'Hold that thought.',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 28,
                    fontWeight: FontWeight.w500,
                    letterSpacing: -.8,
                    color: Theme.of(context).colorScheme.onSurface,
                  ),
                ),
                if (!typing) ...[
                  SizedBox(height: 8),
                  Text(
                    'A sentence is enough.',
                    style: TextStyle(
                      fontSize: 14,
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                  ),
                  SizedBox(height: 24),
                  FloatingSurface(
                    child: TextButton.icon(
                      style: TextButton.styleFrom(
                        foregroundColor: Theme.of(context).colorScheme.primary,
                        minimumSize: Size(176, 52),
                        padding: EdgeInsets.symmetric(
                          horizontal: 22,
                          vertical: 14,
                        ),
                      ),
                      onPressed: onCompose,
                      icon: HeroIcon(
                        HeroIcons.bookmark,
                        size: 19,
                        color: Theme.of(context).colorScheme.primary,
                      ),
                      label: Text(
                        'Save a Place',
                        style: TextStyle(
                          fontSize: 15,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      );
    },
  );
}

class ComputerConnectionRow extends StatelessWidget {
  const ComputerConnectionRow({
    super.key,
    required this.status,
    required this.onTap,
  });
  final String status;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) => FloatingSurface(
    radius: 22,
    child: Material(
      type: MaterialType.transparency,
      child: ListTile(
        dense: true,
        contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 4),
        leading: HeroIcon(
          HeroIcons.computerDesktop,
          size: 22,
          color: Theme.of(context).colorScheme.onSurfaceVariant,
        ),
        title: Text(
          status == 'Not connected' ? 'Connect a computer' : 'My computer',
          style: TextStyle(fontSize: 14, fontWeight: FontWeight.w400),
        ),
        subtitle: Text(
          status,
          style: TextStyle(
            fontSize: 12,
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
        ),
        trailing: HeroIcon(
          HeroIcons.chevronRight,
          size: 16,
          color: Theme.of(context).colorScheme.onSurfaceVariant,
        ),
        onTap: onTap,
      ),
    ),
  );
}
