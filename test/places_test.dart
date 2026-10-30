import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:pico/services/pico_store.dart';
import 'package:pico/screens/home_screen.dart';
import 'package:pico/components/session_drawer.dart';
import 'package:pico/theme/app_theme.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() => SharedPreferences.setMockInitialValues({}));
  test('New chat hides old content without deleting it', () async {
    final store = PicoStore(await SharedPreferences.getInstance())
      ..loadPlaces();
    await store.savePlace('Existing thought');
    final old = store.places.single;
    store.tasks.add({'id': 'old-task'});
    store.selectPlace(old);
    store.newSession();
    expect(store.visiblePlaces, isEmpty);
    expect(store.visibleTasks, isEmpty);
    expect(store.places.single.id, old.id);
    await store.savePlace('A new thought');
    expect(store.visiblePlaces.single.sentence, 'A new thought');
    await store.savePlace('Another message');
    expect(store.visiblePlaces.map((p) => p.sentence), [
      'A new thought',
      'Another message',
    ]);
    store.tasks.insert(0, {'id': 'new-task'});
    expect(store.visibleTasks.single['id'], 'new-task');
    store.selectPlace(old);
    expect(store.visiblePlaces.single.id, old.id);
    await Future<void>.delayed(Duration.zero);
    store.dispose();
  });
  test('Places persist, park, finish, and clear without a backend', () async {
    final prefs = await SharedPreferences.getInstance();
    final store = PicoStore(prefs);
    await store.load();
    await store.savePlace('  Finish the email  ');
    await store.savePlace('   ');
    expect(store.places.single.sentence, 'Finish the email');
    await store.updatePlace(store.places.single, parked: true);
    final restored = PicoStore(prefs);
    await restored.load();
    expect(restored.places.single.parked, isTrue);
    await restored.updatePlace(restored.places.single, finished: true);
    final finalStore = PicoStore(prefs)..loadPlaces();
    expect(finalStore.places.single.finished, isTrue);
    await restored.clearHistory();
    finalStore.loadPlaces();
    expect(finalStore.places, isEmpty);
    store.dispose();
    restored.dispose();
    finalStore.dispose();
  });
  test(
    'Deleting a selected chat persists and removes its recent activity',
    () async {
      final prefs = await SharedPreferences.getInstance();
      final store = PicoStore(prefs)..loadPlaces();
      await store.savePlace('Keep this thought');
      await store.savePlace('Delete this thought');
      final chat = store.places.first;
      store.selectPlace(chat);
      await store.deleteChat(chat);
      expect(store.selectedPlaceId, isNull);
      final restored = PicoStore(prefs)..loadPlaces();
      expect(restored.places.single.sentence, 'Keep this thought');
      expect(
        restored.activities.any((a) => a.target == 'place:${chat.id}'),
        isFalse,
      );
      store.dispose();
      restored.dispose();
    },
  );
  testWidgets('Sidebar deletes individual chats without an archive entry', (
    tester,
  ) async {
    final store = PicoStore(await SharedPreferences.getInstance())
      ..loadPlaces();
    await store.savePlace('Review the draft');
    await tester.pumpWidget(
      MaterialApp(
        theme: PicoTheme.light,
        home: Scaffold(
          body: ListenableBuilder(
            listenable: store,
            builder: (context, _) => SessionDrawer(
              store: store,
              width: 300,
              onClose: () {},
              onSettings: () {},
            ),
          ),
        ),
      ),
    );
    expect(find.byTooltip('Archived activity'), findsNothing);
    await tester.tap(find.byTooltip('Delete chat'));
    await tester.pumpAndSettle();
    expect(find.text('Review the draft'), findsNothing);
    expect(find.text('No chats yet'), findsOneWidget);
    await store.rememberSearch('draft');
    await store.rememberSearch('draft');
    final restored = PicoStore(store.preferences)..loadPlaces();
    expect(
      restored.activities.where((a) => a.target == 'search:draft').length,
      1,
    );
    await tester.pumpWidget(const SizedBox());
    store.dispose();
    restored.dispose();
  });
  test(
    'Malformed saved data reports an error without inventing Places',
    () async {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('pico.places.local', 'broken');
      final store = PicoStore(prefs)..loadPlaces();
      expect(store.places, isEmpty);
      expect(store.error, isNotNull);
      expect(store.connection, 'Not connected');
      store.dispose();
    },
  );
  for (final size in [
    const Size(390, 844),
    const Size(844, 390),
    const Size(1440, 900),
  ]) {
    testWidgets('Home lays out at $size with large text', (tester) async {
      tester.view.physicalSize = size;
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final store = PicoStore(await SharedPreferences.getInstance());
      await store.load();
      await tester.pumpWidget(
        MaterialApp(
          theme: PicoTheme.light,
          home: MediaQuery(
            data: MediaQueryData(
              size: size,
              textScaler: TextScaler.linear(1.4),
              disableAnimations: true,
            ),
            child: HomeScreen(store: store),
          ),
        ),
      );
      await tester.pump(const Duration(milliseconds: 500));
      expect(find.text('Hold that thought.'), findsOneWidget);
      expect(tester.getTopLeft(find.byTooltip('Open menu')).dy, lessThan(90));
      expect(tester.takeException(), isNull);
      await tester.tap(find.byTooltip('Open menu'));
      await tester.pump(const Duration(milliseconds: 400));
      expect(tester.takeException(), isNull);
      await tester.tap(find.text('New chat'));
      await tester.pump(const Duration(milliseconds: 400));
      expect(store.composingNewChat, isTrue);
      expect(find.byType(TextField), findsOneWidget);
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
      store.dispose();
    });
  }
}
