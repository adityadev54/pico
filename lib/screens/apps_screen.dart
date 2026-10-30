import 'package:flutter/material.dart';
import 'package:heroicons/heroicons.dart';

import '../components/screen_chrome.dart';
import '../components/section_group.dart';
import '../services/pico_store.dart';

class AppsScreen extends StatefulWidget {
  const AppsScreen({super.key, required this.store});
  final PicoStore store;
  @override
  State<AppsScreen> createState() => _AppsScreenState();
}

class _AppsScreenState extends State<AppsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) widget.store.loadApprovedApps();
    });
  }

  @override
  Widget build(BuildContext context) => ListenableBuilder(
    listenable: widget.store,
    builder: (context, _) {
      final store = widget.store;
      return Scaffold(
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
                    40,
                  ),
                  children: [
                    const Text(
                      'Open apps',
                      style: TextStyle(
                        fontSize: 28,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 12),
                    Text(
                      'Choose the apps Pico can open from your computer’s companion menu.',
                      style: TextStyle(
                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                      ),
                    ),
                    const SizedBox(height: 12),
                    SectionGroup(
                      title: 'Approved on your computer',
                      children: [
                        if (store.appsLoading)
                          const Padding(
                            padding: EdgeInsets.all(20),
                            child: Row(
                              children: [
                                SizedBox(
                                  width: 18,
                                  height: 18,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                  ),
                                ),
                                SizedBox(width: 12),
                                Text('Loading apps…'),
                              ],
                            ),
                          ),
                        if (!store.appsLoading && store.approvedApps.isEmpty)
                          Padding(
                            padding: const EdgeInsets.all(12),
                            child: Text(
                              store.linked
                                  ? 'No approved apps yet. Open “Open apps” on your computer and choose an app.'
                                  : 'Connect your computer first.',
                            ),
                          ),
                        for (final app in store.approvedApps)
                          SettingsRow(
                            icon: HeroIcons.window,
                            title: app.name,
                            trailing: store.openingAppId == app.id
                                ? const SizedBox(
                                    width: 18,
                                    height: 18,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                    ),
                                  )
                                : TextButton(
                                    onPressed:
                                        store.openingAppId != null ||
                                            !store.devices.any(store.isOnline)
                                        ? null
                                        : () => store.openApprovedApp(app),
                                    child: Text(
                                      'Open',
                                      semanticsLabel: 'Open ${app.name}',
                                    ),
                                  ),
                          ),
                      ],
                    ),
                    if (store.appActionMessage != null)
                      Semantics(
                        liveRegion: true,
                        child: Padding(
                          padding: const EdgeInsets.all(12),
                          child: Text(store.appActionMessage!),
                        ),
                      ),
                  ],
                ),
              ),
            ),
            ScreenToolbar(
              onBack: () => Navigator.pop(context),
              actions: [
                CircleControl(
                  icon: HeroIcons.arrowPath,
                  label: 'Refresh apps',
                  onTap: store.loadApprovedApps,
                ),
              ],
            ),
          ],
        ),
      );
    },
  );
}
