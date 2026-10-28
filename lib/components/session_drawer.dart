import 'package:flutter/material.dart';
import 'package:heroicons/heroicons.dart';
import '../services/pico_store.dart';
import '../theme/app_theme.dart';
import 'pico_brand.dart';
import 'drawer_empty_state.dart';

class SessionDrawer extends StatelessWidget {
  const SessionDrawer({
    super.key,
    required this.store,
    required this.width,
    required this.onClose,
    required this.onSettings,
  });
  final PicoStore store;
  final double width;
  final VoidCallback onClose;
  final VoidCallback onSettings;
  @override
  Widget build(BuildContext context) {
    final chats = store.places;
    return SizedBox(
      width: width,
      child: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 20, 16, 16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const PicoWordmark(light: true),
              const SizedBox(height: 26),
              TextButton.icon(
                style: TextButton.styleFrom(
                  foregroundColor: Colors.white,
                  backgroundColor: Colors.white.withValues(alpha: .09),
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 12,
                  ),
                  minimumSize: const Size(double.infinity, 48),
                  alignment: Alignment.centerLeft,
                  textStyle: const TextStyle(
                    fontFamily: 'DM Sans',
                    fontSize: 14,
                    fontWeight: FontWeight.w400,
                  ),
                ),
                onPressed: () {
                  store.newSession();
                  onClose();
                },
                icon: const HeroIcon(
                  HeroIcons.plus,
                  size: 20,
                  color: Colors.white,
                ),
                label: const Text('New chat'),
              ),
              const SizedBox(height: 18),
              const Text(
                'Chats',
                style: TextStyle(color: PicoTheme.drawerMuted, fontSize: 12),
              ),
              const SizedBox(height: 12),
              Expanded(
                child: chats.isEmpty
                    ? DrawerEmptyState(character: store.character)
                    : ListView.builder(
                        itemCount: chats.length,
                        itemBuilder: (context, i) => Padding(
                          padding: const EdgeInsets.only(bottom: 6),
                          child: ListTile(
                            contentPadding: const EdgeInsets.symmetric(
                              horizontal: 12,
                            ),
                            tileColor: Colors.white.withValues(alpha: .045),
                            selectedTileColor: Colors.white.withValues(
                              alpha: .09,
                            ),
                            selected: store.selectedPlaceId == chats[i].id,
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(18),
                            ),
                            title: Text(
                              chats[i].sentence,
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 14,
                              ),
                            ),
                            trailing: IconButton(
                              tooltip: 'Delete chat',
                              icon: const HeroIcon(
                                HeroIcons.trash,
                                size: 19,
                                color: PicoTheme.drawerMuted,
                              ),
                              onPressed: () => store.deleteChat(chats[i]),
                            ),
                            onTap: () {
                              store.selectPlace(chats[i]);
                              onClose();
                            },
                          ),
                        ),
                      ),
              ),
              Row(
                children: [
                  Container(
                    width: 6,
                    height: 6,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: store.connection == 'Connected'
                          ? PicoTheme.success
                          : PicoTheme.drawerMuted,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      store.connection,
                      style: const TextStyle(
                        fontSize: 12,
                        color: PicoTheme.drawerMuted,
                      ),
                    ),
                  ),
                  IconButton(
                    tooltip: 'Settings',
                    onPressed: () => onSettings(),
                    icon: const HeroIcon(
                      HeroIcons.cog6Tooth,
                      color: Colors.white,
                      size: 23,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
