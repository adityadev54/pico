import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:kin_ui/kin_ui.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:pico/components/appearance_settings.dart';
import 'package:pico/components/listening_wave.dart';
import 'package:pico/components/pico_dialog.dart';
import 'package:pico/components/section_group.dart';
import 'package:pico/screens/search_screen.dart';
import 'package:pico/screens/settings_screen.dart';
import 'package:pico/components/conversation_view.dart';
import 'package:pico/components/home_controls.dart';
import 'package:pico/components/place_empty_state.dart';
import 'package:heroicons/heroicons.dart';
import 'package:pico/services/pico_store.dart';
import 'package:pico/theme/app_theme.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() => SharedPreferences.setMockInitialValues({}));
  test('Appearance and character size survive a restart', () async {
    final preferences = await SharedPreferences.getInstance();
    final store = PicoStore(preferences);
    await store.load();
    await store.setDarkMode(true);
    await store.setCharacterSize('large');
    final restored = PicoStore(preferences);
    await restored.load();
    expect(restored.darkMode, isTrue);
    expect(restored.characterSize, 'large');
    expect(restored.characterScale, 1.2);
    store.dispose();
    restored.dispose();
  });
  testWidgets(
    'Search finds chats and agents, while relevant recents are capped at five',
    (tester) async {
      final store = PicoStore(await SharedPreferences.getInstance());
      await store.load();
      for (var i = 0; i < 8; i++) {
        await store.savePlace('Note $i');
      }
      await tester.pumpWidget(
        MaterialApp(
          theme: PicoTheme.light,
          home: SearchScreen(store: store),
        ),
      );
      await tester.pump();
      await tester.enterText(find.byType(TextField), 'no-matching-action');
      await tester.pump();
      expect(find.text('No chats or agents found.'), findsOneWidget);
      expect(find.byType(SettingsRow), findsNWidgets(5));
      await tester.enterText(find.byType(TextField), 'mica');
      await tester.pump();
      expect(find.text('Mica'), findsOneWidget);
      expect(find.text('Recent activity'), findsOneWidget);
      await tester.pumpWidget(const SizedBox());
      store.dispose();
    },
  );
  testWidgets('Compact Kin switch replaces the platform switch', (
    tester,
  ) async {
    final store = PicoStore(await SharedPreferences.getInstance());
    await store.load();
    await tester.pumpWidget(
      MaterialApp(
        theme: PicoTheme.light,
        home: Scaffold(body: AppearanceSettings(store: store)),
      ),
    );
    final toggle = tester.widget<KinPremiumToggle>(
      find.byType(KinPremiumToggle),
    );
    expect(toggle.size, KinToggleSize.small);
    expect(find.byType(Switch), findsNothing);
    expect(find.textContaining('Halloween'), findsNothing);
    await tester.pumpWidget(const SizedBox());
    store.dispose();
  });
  testWidgets('Appearance opens separately and character size uses radios', (
    tester,
  ) async {
    final store = PicoStore(await SharedPreferences.getInstance());
    await store.load();
    await tester.pumpWidget(
      MaterialApp(
        theme: PicoTheme.light,
        home: SettingsScreen(store: store),
      ),
    );
    expect(find.byType(KinPremiumToggle), findsNothing);
    await tester.ensureVisible(find.text('Appearance'));
    await tester.tap(find.text('Appearance'));
    await tester.pumpAndSettle();
    expect(find.byType(RadioListTile<String>), findsNWidgets(3));
    await tester.ensureVisible(find.text('Large'));
    await tester.tap(find.text('Large'));
    await tester.pump();
    expect(store.characterSize, 'large');
    expect(find.text('Large'), findsOneWidget);
    expect(
      find.descendant(
        of: find.byType(AppearanceSettings),
        matching: find.byType(Divider),
      ),
      findsNWidgets(2),
    );
    await tester.pumpWidget(const SizedBox());
    store.dispose();
  });
  testWidgets(
    'Paired home hides setup card and dark toolbar icons are legible',
    (tester) async {
      final store = PicoStore(await SharedPreferences.getInstance());
      await store.load();
      store.devices = [
        {'id': 'test'},
      ];
      await tester.pumpWidget(
        MaterialApp(
          theme: PicoTheme.dark,
          home: Scaffold(
            body: Column(
              children: [
                HomeControls(onMenu: () {}, onType: () {}, onSearch: () {}),
                Expanded(
                  child: ConversationView(
                    store: store,
                    controller: ScrollController(),
                    onDevices: () {},
                    onCompose: () {},
                  ),
                ),
              ],
            ),
          ),
        ),
      );
      expect(find.byType(ComputerConnectionRow), findsNothing);
      final icons = tester
          .widgetList<HeroIcon>(find.byType(HeroIcon))
          .where(
            (icon) => [
              HeroIcons.pencilSquare,
              HeroIcons.magnifyingGlass,
            ].contains(icon.icon),
          );
      for (final icon in icons) {
        expect(icon.color, PicoTheme.dark.colorScheme.onSurface);
      }
      await tester.pumpWidget(const SizedBox());
      store.dispose();
    },
  );
  testWidgets(
    'Thought entries expand newline-heavy text and hide actions until long press',
    (tester) async {
      final store = PicoStore(await SharedPreferences.getInstance());
      await store.load();
      await store.savePlace(List.generate(12, (i) => 'Line $i').join('\n'));
      await tester.pumpWidget(
        MaterialApp(
          theme: PicoTheme.light,
          home: Scaffold(
            body: ListView(
              children: [
                PlaceMessage(place: store.places.single, store: store),
              ],
            ),
          ),
        ),
      );
      expect(find.text('Copy'), findsNothing);
      expect(find.text('Show more'), findsOneWidget);
      await tester.tap(find.text('Show more'));
      await tester.pump();
      expect(find.text('Show less'), findsOneWidget);
      await tester.longPress(
        find.descendant(
          of: find.byType(PlaceMessage),
          matching: find.text(store.places.single.sentence),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.text('Copy'), findsOneWidget);
      expect(find.text('Park'), findsOneWidget);
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
      store.dispose();
    },
  );
  testWidgets(
    'About stays informational and agent size radios lead their labels',
    (tester) async {
      final store = PicoStore(await SharedPreferences.getInstance());
      await store.load();
      await tester.pumpWidget(
        MaterialApp(
          theme: PicoTheme.light,
          home: SettingsScreen(store: store),
        ),
      );
      await tester.scrollUntilVisible(
        find.text('Pico'),
        300,
        scrollable: find.byType(Scrollable).first,
      );
      await tester.tap(find.text('Pico'));
      await tester.pumpAndSettle();
      expect(find.byType(PicoDialog), findsNothing);
      await tester.scrollUntilVisible(
        find.text('Appearance'),
        -300,
        scrollable: find.byType(Scrollable).first,
      );
      await tester.tap(find.text('Appearance'));
      await tester.pumpAndSettle();
      expect(find.text('Agent'), findsOneWidget);
      for (final row in tester.widgetList<RadioListTile<String>>(
        find.byType(RadioListTile<String>),
      )) {
        expect(row.controlAffinity, ListTileControlAffinity.leading);
        expect(row.minTileHeight, 48);
      }
      await tester.pumpWidget(const SizedBox());
      store.dispose();
    },
  );
  testWidgets('Dialog actions have equal width and height with larger text', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: PicoTheme.light,
        home: MediaQuery(
          data: const MediaQueryData(textScaler: TextScaler.linear(1.5)),
          child: Scaffold(
            body: Center(
              child: PicoDialog(
                title: const Text('Clear your history?'),
                actions: [
                  PicoDialogAction(label: 'Keep', onPressed: () {}),
                  PicoDialogAction(
                    label: 'Clear history',
                    onPressed: () {},
                    destructive: true,
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
    final buttons = find.byType(TextButton);
    expect(buttons, findsNWidgets(2));
    expect(tester.getSize(buttons.at(0)), tester.getSize(buttons.at(1)));
    expect(tester.takeException(), isNull);
  });
  testWidgets('Listening wave respects reduced motion', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: MediaQuery(
          data: const MediaQueryData(disableAnimations: true),
          child: const ListeningWave(level: .7),
        ),
      ),
    );
    await tester.pump(const Duration(seconds: 2));
    expect(tester.binding.transientCallbackCount, 0);
    expect(tester.takeException(), isNull);
  });
}
