import 'package:flutter/material.dart';
import 'package:heroicons/heroicons.dart';
import 'package:kin_ui/kin_ui.dart';
import '../services/pico_store.dart';
import 'section_group.dart';
import 'character_picker.dart';

class AppearanceSettings extends StatelessWidget {
  const AppearanceSettings({super.key, required this.store});
  final PicoStore store;
  @override
  Widget build(BuildContext context) => SectionGroup(
    title: 'Theme and agent',
    children: [
      SettingsRow(
        icon: HeroIcons.moon,
        title: 'Dark theme',
        subtitle: store.darkMode ? 'Dark' : 'Light',
        trailing: Semantics(
          label: 'Dark theme',
          toggled: store.darkMode,
          child: SizedBox(
            width: 52,
            height: 48,
            child: Center(
              child: KinPremiumToggle(
                value: store.darkMode,
                size: KinToggleSize.small,
                onChanged: store.setDarkMode,
              ),
            ),
          ),
        ),
        onTap: () => store.setDarkMode(!store.darkMode),
      ),
      SettingsRow(
        icon: HeroIcons.faceSmile,
        title: 'Agent',
        subtitle:
            '${store.character[0].toUpperCase()}${store.character.substring(1)}',
        onTap: () => showCharacterPicker(context, store),
        trailing: Image.asset(
          'assets/characters/${store.character}/idle.png',
          width: 38,
          height: 38,
        ),
      ),
      Column(
        children: [
          const SettingsRow(
            icon: HeroIcons.arrowsPointingOut,
            title: 'Agent size',
          ),
          RadioGroup<String>(
            groupValue: store.characterSize,
            onChanged: (value) {
              if (value != null) store.setCharacterSize(value);
            },
            child: Column(
              children: [
                for (final value in ['small', 'medium', 'large'])
                  RadioListTile<String>(
                    value: value,
                    title: Text(
                      '${value[0].toUpperCase()}${value.substring(1)}',
                      style: const TextStyle(fontSize: 14),
                    ),
                    contentPadding: const EdgeInsets.symmetric(horizontal: 12),
                    dense: true,
                    visualDensity: VisualDensity.compact,
                    minTileHeight: 48,
                    controlAffinity: ListTileControlAffinity.leading,
                  ),
              ],
            ),
          ),
        ],
      ),
    ],
  );
}
