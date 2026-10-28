part of 'pico_store.dart';

extension PicoAgentStore on PicoStore {
  Future<void> chooseCharacter(String value) async {
    if (!['tuck', 'mica'].contains(value)) return;
    character = value;
    await preferences.setString('character', value);
    await recordActivity(
      'Agent changed',
      '${value[0].toUpperCase()}${value.substring(1)}',
      'character',
    );
    _changed();
    try {
      await syncCompanion();
    } catch (_) {
      _sentCompanion = null;
    }
  }

  Future<void> setCharacterSize(String value) async {
    if (!['small', 'medium', 'large'].contains(value)) return;
    characterSize = value;
    await preferences.setString('pico.character_size', value);
    await recordActivity(
      'Agent size changed',
      '${value[0].toUpperCase()}${value.substring(1)}',
      'appearance',
    );
    _changed();
    try {
      await syncCompanion();
    } catch (_) {
      _sentCompanion = null;
    }
  }

  Future<void> setDarkMode(bool value) async {
    darkMode = value;
    await preferences.setBool('pico.dark_mode', value);
    await recordActivity(
      'Appearance changed',
      value ? 'Dark' : 'Light',
      'appearance',
    );
    _changed();
  }
}
