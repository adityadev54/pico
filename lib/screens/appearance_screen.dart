import 'package:flutter/material.dart';

import '../components/appearance_settings.dart';
import '../components/screen_chrome.dart';
import '../services/pico_store.dart';

class AppearanceScreen extends StatelessWidget {
  const AppearanceScreen({super.key, required this.store});
  final PicoStore store;
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
                  32,
                ),
                children: [
                  const Padding(
                    padding: EdgeInsets.all(12),
                    child: Text(
                      'Appearance',
                      style: TextStyle(
                        fontSize: 28,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                  AppearanceSettings(store: store),
                ],
              ),
            ),
          ),
          ScreenToolbar(onBack: () => Navigator.pop(context)),
        ],
      ),
    ),
  );
}
