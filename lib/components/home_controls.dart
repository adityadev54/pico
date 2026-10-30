import 'package:flutter/material.dart';
import 'package:heroicons/heroicons.dart';

import 'floating_surface.dart';
import 'screen_chrome.dart';
import '../services/pico_store.dart';

class HomeControls extends StatelessWidget {
  const HomeControls({
    super.key,
    required this.onMenu,
    required this.onType,
    required this.onSearch,
    this.store,
  });
  final PicoStore? store;
  final VoidCallback onMenu;
  final VoidCallback onType;
  final VoidCallback onSearch;
  @override
  Widget build(BuildContext context) => SafeArea(
    bottom: false,
    child: Padding(
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 0),
      child: Row(
        children: [
          CircleControl(
            icon: HeroIcons.bars3,
            label: 'Open menu',
            onTap: onMenu,
          ),
          if (store != null)
            Padding(
              padding: const EdgeInsets.only(left: 12),
              child: Tooltip(
                message: store!.museLabel,
                child: Semantics(
                  label: store!.museLabel,
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Container(
                        width: 7,
                        height: 7,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: store!.museState == 'ready'
                              ? const Color(0xFF66A577)
                              : Theme.of(context).colorScheme.onSurfaceVariant,
                        ),
                      ),
                      const SizedBox(width: 6),
                      Text(
                        'Muse',
                        style: TextStyle(
                          fontSize: 12,
                          color: Theme.of(context).colorScheme.onSurfaceVariant,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          const Spacer(),
          FloatingSurface(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 2),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  IconButton(
                    tooltip: 'Save a Place',
                    onPressed: onType,
                    icon: HeroIcon(
                      HeroIcons.pencilSquare,
                      size: 23,
                      color: Theme.of(context).colorScheme.onSurface,
                    ),
                  ),
                  IconButton(
                    tooltip: 'Search Pico',
                    onPressed: onSearch,
                    icon: HeroIcon(
                      HeroIcons.magnifyingGlass,
                      size: 23,
                      color: Theme.of(context).colorScheme.onSurface,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    ),
  );
}
