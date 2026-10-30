import 'package:flutter/material.dart';
import 'package:heroicons/heroicons.dart';

import '../components/screen_chrome.dart';
import '../components/section_group.dart';
import '../components/pico_dialog.dart';
import 'appearance_screen.dart';
import '../services/pico_store.dart';
import 'account_screen.dart';
import 'devices_screen.dart';
import 'apps_screen.dart';

import 'permissions_screen.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key, required this.store});
  final PicoStore store;
  void _open(BuildContext context, Widget child) =>
      Navigator.push(context, MaterialPageRoute<void>(builder: (_) => child));
  @override
  Widget build(BuildContext context) => ListenableBuilder(
    listenable: store,
    builder: (context, _) => Scaffold(
      body: Stack(
        children: [
          Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 680),
              child: ListView(
                padding: EdgeInsets.fromLTRB(
                  12,
                  MediaQuery.paddingOf(context).top + 100,
                  12,
                  50,
                ),
                children: [
                  const Padding(
                    padding: EdgeInsets.fromLTRB(12, 8, 12, 24),
                    child: Text(
                      'Settings',
                      style: TextStyle(
                        fontSize: 28,
                        fontWeight: FontWeight.w600,
                        letterSpacing: -.7,
                      ),
                    ),
                  ),
                  SectionGroup(
                    title: 'You & Pico',
                    children: [
                      SettingsRow(
                        icon: HeroIcons.userCircle,
                        title: store.signedIn
                            ? 'Your account'
                            : 'Create an account',
                        subtitle:
                            store.client?.auth.currentUser?.email ??
                            'Keep your devices together',
                        onTap: () {
                          if (store.signedIn) {
                            showPicoDialog<void>(
                              context: context,
                              builder: (context) => PicoDialog(
                                title: const Text('Your account'),
                                content: Text(
                                  store.client!.auth.currentUser!.email ?? '',
                                ),
                                actions: [
                                  PicoDialogAction(
                                    label: 'Done',
                                    primary: true,
                                    onPressed: () => Navigator.pop(context),
                                  ),
                                ],
                              ),
                            );
                          } else {
                            _open(context, AccountScreen(store: store));
                          }
                        },
                      ),
                      SettingsRow(
                        icon: HeroIcons.window,
                        title: 'Open apps',
                        subtitle: 'Approved on your computer',
                        onTap: () => _open(context, AppsScreen(store: store)),
                      ),
                      SettingsRow(
                        icon: HeroIcons.shieldCheck,
                        title: 'Permissions',
                        subtitle: 'Snapshots and Head Start',
                        onTap: () =>
                            _open(context, PermissionsScreen(store: store)),
                      ),
                      SettingsRow(
                        icon: HeroIcons.computerDesktop,
                        title: 'Connected devices',
                        subtitle: store.connection,
                        onTap: () =>
                            _open(context, DevicesScreen(store: store)),
                      ),
                    ],
                  ),
                  SectionGroup(
                    title: 'Preferences',
                    children: [
                      SettingsRow(
                        icon: HeroIcons.paintBrush,
                        title: 'Appearance',
                        subtitle: 'Theme, agent and size',
                        onTap: () =>
                            _open(context, AppearanceScreen(store: store)),
                      ),
                    ],
                  ),
                  SectionGroup(
                    title: 'Activity',
                    children: [
                      SettingsRow(
                        icon: HeroIcons.trash,
                        title: 'Clear chats and history',
                        subtitle: 'Remove chats saved on this device',
                        onTap: () => _clear(context),
                      ),
                    ],
                  ),
                  const SectionGroup(
                    title: 'Intelligence',
                    children: [
                      SettingsRow(
                        icon: HeroIcons.cpuChip,
                        title: 'Muse Spark',
                        subtitle: 'Head Start · not connected',
                      ),
                      SettingsRow(
                        icon: HeroIcons.shieldCheck,
                        title: 'You stay in control',
                        subtitle:
                            'Computer actions require a connected helper.',
                      ),
                    ],
                  ),
                  SectionGroup(
                    title: 'About',
                    children: [
                      SettingsRow(
                        icon: HeroIcons.informationCircle,
                        title: 'Pico',
                        subtitle: 'Version 0.5.0',
                      ),
                    ],
                  ),
                  if (store.signedIn)
                    TextButton(
                      onPressed: () async {
                        await store.client!.auth.signOut();
                        if (context.mounted) {
                          Navigator.popUntil(context, (r) => r.isFirst);
                        }
                      },
                      child: const Text('Sign out'),
                    ),
                ],
              ),
            ),
          ),
          ScreenToolbar(onBack: () => Navigator.pop(context)),
        ],
      ),
    ),
  );
  Future<void> _clear(BuildContext context) async {
    final confirmed = await showPicoDialog<bool>(
      context: context,
      builder: (context) => PicoDialog(
        title: const Text('Clear your history?'),
        content: const Text(
          'This removes chats saved on this device. Queued computer messages are kept until delivered.',
        ),
        actions: [
          PicoDialogAction(
            label: 'Keep',
            onPressed: () => Navigator.pop(context, false),
          ),
          PicoDialogAction(
            label: 'Clear history',
            destructive: true,
            onPressed: () => Navigator.pop(context, true),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await store.clearHistory();
    } catch (_) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Couldn’t clear history. Please try again.'),
          ),
        );
      }
    }
  }
}
