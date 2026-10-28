import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:pico/services/pico_store.dart';
import 'package:pico/services/desktop_connection.dart';
import 'package:pico/components/character_picker.dart';
import 'package:pico/theme/app_theme.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  for (final retired in ['boo', 'pip']) {
    test('Retired $retired selection migrates on phone and desktop', () async {
      SharedPreferences.setMockInitialValues({
        'character': retired,
        'pico.desktop.character': retired,
      });
      final prefs = await SharedPreferences.getInstance();
      final phone = PicoStore(prefs);
      final desktop = DesktopConnection(prefs);
      await phone.load();
      await desktop.load();
      expect(phone.character, 'tuck');
      expect(desktop.character, 'tuck');
      expect(prefs.getString('character'), 'tuck');
      expect(prefs.getString('pico.desktop.character'), 'tuck');
      await phone.chooseCharacter(retired);
      expect(phone.character, 'tuck');
      await phone.chooseCharacter('mica');
      expect(phone.character, 'mica');
      phone.dispose();
      desktop.dispose();
    });
  }
  test('Existing Mica selection is preserved', () async {
    SharedPreferences.setMockInitialValues({
      'character': 'mica',
      'pico.desktop.character': 'mica',
    });
    final prefs = await SharedPreferences.getInstance();
    final phone = PicoStore(prefs);
    final desktop = DesktopConnection(prefs);
    await phone.load();
    await desktop.load();
    expect(phone.character, 'mica');
    expect(desktop.character, 'mica');
    phone.dispose();
    desktop.dispose();
  });
  testWidgets(
    'Agent carousel contains only Tuck and Mica, without duplicate neighbors',
    (tester) async {
      String? selected;
      await tester.pumpWidget(
        MaterialApp(
          theme: PicoTheme.light,
          home: Scaffold(
            body: CharacterPicker(
              initial: 'tuck',
              onSelect: (value) => selected = value,
            ),
          ),
        ),
      );
      expect(
        find.byWidgetPredicate(
          (widget) => widget is Semantics && widget.properties.label == 'Tuck',
        ),
        findsOneWidget,
      );
      expect(find.bySemanticsLabel('Mica'), findsOneWidget);
      expect(find.bySemanticsLabel('Boo'), findsNothing);
      expect(find.bySemanticsLabel('Pip'), findsNothing);
      await tester.tap(find.bySemanticsLabel('Mica'));
      await tester.pumpAndSettle();
      expect(selected, 'mica');
      await tester.pumpWidget(const SizedBox());
    },
  );
}
