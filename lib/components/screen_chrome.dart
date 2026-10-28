import 'package:flutter/material.dart';
import 'package:heroicons/heroicons.dart';
import 'floating_surface.dart';

class CircleControl extends StatelessWidget {
  const CircleControl({
    super.key,
    required this.icon,
    required this.label,
    required this.onTap,
  });
  final HeroIcons icon;
  final String label;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) => FloatingSurface(
    child: IconButton(
      style: IconButton.styleFrom(
        foregroundColor: Theme.of(context).colorScheme.onSurface,
        minimumSize: Size(48, 48),
      ),
      tooltip: label,
      onPressed: onTap,
      icon: HeroIcon(
        icon,
        size: 23,
        color: Theme.of(context).colorScheme.onSurface,
      ),
    ),
  );
}

class ScreenToolbar extends StatelessWidget {
  const ScreenToolbar({
    super.key,
    required this.onBack,
    this.actions = const [],
  });
  final VoidCallback onBack;
  final List<Widget> actions;
  @override
  Widget build(BuildContext context) => SafeArea(
    bottom: false,
    child: Padding(
      padding: EdgeInsets.fromLTRB(12, 8, 12, 8),
      child: Row(
        children: [
          CircleControl(
            icon: HeroIcons.chevronLeft,
            label: 'Back',
            onTap: onBack,
          ),
          Spacer(),
          ...actions,
        ],
      ),
    ),
  );
}

class EdgeFades extends StatelessWidget {
  const EdgeFades({super.key, required this.child});
  final Widget child;
  @override
  Widget build(BuildContext context) => Stack(
    children: [
      child,
      for (final top in [true, false])
        Positioned(
          top: top ? 0 : null,
          bottom: top ? null : 0,
          left: 0,
          right: 0,
          child: IgnorePointer(
            child: Container(
              height: top ? MediaQuery.paddingOf(context).top + 90 : 125,
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: top ? Alignment.topCenter : Alignment.bottomCenter,
                  end: top ? Alignment.bottomCenter : Alignment.topCenter,
                  colors: [
                    Theme.of(context).scaffoldBackgroundColor,
                    Theme.of(context).scaffoldBackgroundColor
                        .withValues(alpha: 0),
                  ],
                ),
              ),
            ),
          ),
        ),
    ],
  );
}
