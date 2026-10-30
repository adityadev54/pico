import 'package:flutter/material.dart';
import 'package:heroicons/heroicons.dart';

import '../components/screen_chrome.dart';
import '../components/section_group.dart';
import '../components/pico_dialog.dart';
import '../services/pico_store.dart';
import 'apps_screen.dart';

class PermissionsScreen extends StatefulWidget {
  const PermissionsScreen({super.key, required this.store});
  final PicoStore store;
  @override
  State<PermissionsScreen> createState() => _PermissionsScreenState();
}

class _PermissionsScreenState extends State<PermissionsScreen> {
  @override
  Widget build(BuildContext context) => Scaffold(
    body: Stack(
      children: [
        Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 680),
            child: ListView(
              padding: EdgeInsets.fromLTRB(
                12,
                MediaQuery.paddingOf(context).top + 90,
                12,
                40,
              ),
              children: [
                const Padding(
                  padding: EdgeInsets.all(12),
                  child: Text(
                    'Pico permissions',
                    style: TextStyle(fontSize: 28, fontWeight: FontWeight.w600),
                  ),
                ),
                SectionGroup(
                  title: 'App access',
                  children: [
                    SettingsRow(
                      icon: HeroIcons.window,
                      title: 'Open approved apps',
                      subtitle: 'Choose allowed apps on your computer',
                      onTap: () => Navigator.push(
                        context,
                        MaterialPageRoute<void>(
                          builder: (_) => AppsScreen(store: widget.store),
                        ),
                      ),
                    ),
                  ],
                ),
                const SectionGroup(
                  title: 'Hold my place',
                  children: [
                    SettingsRow(
                      icon: HeroIcons.clock,
                      title: 'Notice when I step away',
                      subtitle:
                          'Change the idle interval in Pico on your computer',
                    ),
                    SettingsRow(
                      icon: HeroIcons.photo,
                      title: 'Snapshot the active window',
                      subtitle: 'Manage snapshots in Pico on your computer',
                    ),
                    SettingsRow(
                      icon: HeroIcons.shieldCheck,
                      title: 'Screen access',
                      subtitle: 'Not verified on this computer',
                    ),
                  ],
                ),
                SectionGroup(
                  title: 'Muse',
                  children: [
                    SettingsRow(
                      icon: HeroIcons.pencilSquare,
                      title: 'Connection',
                      subtitle: widget.store.museLabel,
                    ),
                    SettingsRow(
                      icon: HeroIcons.photo,
                      title: 'Selected summaries only',
                      subtitle: 'No automatic summaries or snapshot uploads',
                    ),
                    SettingsRow(
                      icon: HeroIcons.arrowTopRightOnSquare,
                      title: 'Reopen my page',
                      subtitle: 'Requires your approval on return',
                    ),
                  ],
                ),
                const SectionGroup(
                  title: 'Never snapshot these apps',
                  children: [
                    SettingsRow(
                      icon: HeroIcons.lockClosed,
                      title: 'Manage on your computer',
                      subtitle: 'Choose exclusions on your computer. Opening an app does not grant snapshot access.',
                    ),
                  ],
                ),
                const SectionGroup(
                  title: 'Snapshots folder',
                  children: [
                    SettingsRow(
                      icon: HeroIcons.folder,
                      title: 'Pictures/PICO Places',
                      subtitle: 'Desktop only · default retention: 7 days after finishing',
                    ),
                  ],
                ),
                const SectionGroup(
                  title: 'Your control',
                  children: [
                    SettingsRow(
                      icon: HeroIcons.lockClosed,
                      title: 'Pico always asks first',
                      subtitle: 'Always on',
                    ),
                    SettingsRow(
                      icon: HeroIcons.devicePhoneMobile,
                      title: 'Connected phone',
                      subtitle: 'No desktop connection verified',
                    ),
                  ],
                ),
                TextButton(
                  onPressed: () => showPicoDialog<void>(
                    context: context,
                    builder: (context) => PicoDialog(
                      title: const Text('Pico is not running on this computer'),
                      content: const Text(
                        'Pause Pico from its menu on your computer.',
                      ),
                      actions: [
                        PicoDialogAction(
                          label: 'Done',
                          primary: true,
                          onPressed: () => Navigator.pop(context),
                        ),
                      ],
                    ),
                  ),
                  child: const Text('Pause Pico for 1 hour'),
                ),
                TextButton(
                  onPressed: () => Navigator.pop(context),
                  child: const Text('Done'),
                ),
              ],
            ),
          ),
        ),
        ScreenToolbar(onBack: () => Navigator.pop(context)),
      ],
    ),
  );
}
