import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:pico/screens/home_screen.dart';
import 'package:pico/services/pico_store.dart';
import 'package:pico/theme/app_theme.dart';

Future<PicoStore> mountHome(WidgetTester tester) async {
  SharedPreferences.setMockInitialValues({});
  final store = PicoStore(await SharedPreferences.getInstance());
  await store.load();
  store.devices.add({
    'id': 'device-1',
    'name': 'Test Mac',
    'os': 'macos',
    'last_seen': DateTime.now().toUtc().toIso8601String(),
  });
  await tester.pumpWidget(
    MaterialApp(theme: PicoTheme.light, home: HomeScreen(store: store)),
  );
  await tester.pumpAndSettle();
  await tester.tap(find.byTooltip('Save a Place'));
  await tester.pumpAndSettle();
  return store;
}

Future<void> sendText(WidgetTester tester, String text) async {
  await tester.enterText(find.byType(TextField), text);
  await tester.tap(find.byTooltip('Send'));
  await tester.pump();
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  testWidgets('Unrecognized request explains itself instead of failing silent', (
    tester,
  ) async {
    final store = await mountHome(tester);
    addTearDown(store.dispose);
    await sendText(
      tester,
      'can you open my files and arrange all the photos in one folder',
    );
    expect(find.textContaining('Saved as a note'), findsOneWidget);
    expect(find.textContaining('find my brief'), findsOneWidget);
    expect(store.places.single.sentence, contains('photos'));
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('Typing dismisses a stale send error', (tester) async {
    final store = await mountHome(tester);
    addTearDown(store.dispose);
    store.error = 'Computer not found. Connect it again.';
    store.notifyListeners();
    await tester.pump();
    expect(find.textContaining('Computer not found'), findsOneWidget);
    await tester.enterText(find.byType(TextField), 'find my brief');
    await tester.pump();
    expect(find.textContaining('Computer not found'), findsNothing);
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('Plain note saves with no guidance banner', (tester) async {
    final store = await mountHome(tester);
    addTearDown(store.dispose);
    await sendText(tester, 'buy milk tomorrow');
    expect(find.textContaining('Saved as a note'), findsNothing);
    expect(store.places.single.sentence, 'buy milk tomorrow');
    await tester.pumpWidget(const SizedBox());
  });
}
