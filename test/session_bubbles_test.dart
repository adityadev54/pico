import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:pico/components/session_drawer.dart';
import 'package:pico/components/scroll_edge_fade.dart';
import 'package:pico/components/chat_bubble_shape.dart';
import 'package:pico/components/task_bubble.dart';
import 'package:pico/components/conversation_view.dart';
import 'package:pico/models/place.dart';
import 'package:pico/services/pico_store.dart';
import 'package:pico/theme/app_theme.dart';

import 'helpers/capture_preview.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() => SharedPreferences.setMockInitialValues({}));
  setUpAll(() async {
    final font = FontLoader('DM Sans')
      ..addFont(rootBundle.load('assets/fonts/DMSans.ttf'));
    await font.load();
  });
  test('Only New chat separates sessions; selection and blank draft survive reopening', () async {
    final prefs = await SharedPreferences.getInstance();
    final store = PicoStore(prefs)..loadPlaces();
    await store.savePlace('First topic');
    final first = store.current!;
    await store.savePlace('Follow up');
    await store.rememberReply('Here is the answer.', first.id);
    expect(store.sessions.length, 1);
    expect(store.visiblePlaces.length, 3);
    store.newSession();
    expect(store.sessions.length, 1);
    await store.savePlace('Second topic');
    final second = store.current!;
    await store.savePlace('Second follow up');
    await store.rememberReply('Second answer.', second.id);
    expect(store.sessions.length, 2);
    expect(store.visiblePlaces.length, 3);
    store.select(first);
    await store.persistChats();
    final restored = PicoStore(prefs)..loadPlaces();
    expect(restored.current!.id, first.id);
    await restored.savePlace('Continue first topic');
    expect(restored.sessions.length, 2);
    expect(restored.visiblePlaces.length, 4);
    expect(
      restored.visiblePlaces.any((p) => p.sentence == 'Second topic'),
      isFalse,
    );
    restored.newSession();
    await restored.persistChats();
    final draft = PicoStore(prefs)..loadPlaces();
    expect(draft.current, isNull);
    expect(draft.composingNewChat, isTrue);
    expect(draft.sessions.length, 2);
    expect(draft.visiblePlaces, isEmpty);
    await draft.savePlace('Third topic');
    expect(draft.sessions.length, 3);
    store.dispose();
    restored.dispose();
    draft.dispose();
  });
  test('Legacy individual message rows recover as one session without losing messages', () async {
    final now = DateTime.now();
    final old = List.generate(
      3,
      (i) => Place(
        id: 'legacy-$i',
        sentence: 'Message $i',
        created: now.add(Duration(seconds: i)),
      ),
    );
    SharedPreferences.setMockInitialValues({
      'pico.places.local': jsonEncode(old.map((p) => p.toJson()).toList()),
      'pico.chats.local': jsonEncode(
        old
            .map(
              (p) => {
                'id': p.id,
                'title': p.sentence,
                'created_at': p.created.toIso8601String(),
              },
            )
            .toList(),
      ),
    });
    final prefs = await SharedPreferences.getInstance();
    final store = PicoStore(prefs)..loadPlaces();
    expect(store.sessions.length, 1);
    expect(store.visiblePlaces.length, 3);
    await store.persistChats();
    await Future<void>.delayed(Duration.zero);
    final restored = PicoStore(prefs)..loadPlaces();
    expect(restored.sessions.length, 1);
    expect(restored.visiblePlaces.length, 3);
    store.dispose();
    restored.dispose();
  });
  testWidgets(
    'Task replies and assistant messages always have a bubble surface',
    (tester) async {
      final store = PicoStore(await SharedPreferences.getInstance());
      await store.savePlace('Create a file');
      await store.rememberReply('Which folder?', store.current!.id);
      store.tasks.add({
        'id': 'reply',
        'session_id': store.current!.id,
        'kind': 'create_note',
        'status': 'completed',
        'created_at': DateTime.now().toIso8601String(),
        'input': {'text': 'Created content'},
        'result': {'message': 'File created.'},
      });
      final scroll = ScrollController();
      await tester.pumpWidget(
        MaterialApp(
          theme: PicoTheme.light,
          home: Scaffold(
            body: ConversationView(
              store: store,
              controller: scroll,
              onDevices: () {},
              onCompose: () {},
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();
      final taskSurface = tester
          .widgetList<Material>(
            find.descendant(
              of: find.byType(TaskBubble),
              matching: find.byType(Material),
            ),
          )
          .where((m) => m.shape is ChatBubbleShape);
      expect(taskSurface.length, 1);
      expect((taskSurface.single.shape! as ChatBubbleShape).mine, isFalse);
      final bubbles = tester
          .widgetList<Material>(find.byType(Material))
          .where((m) => m.shape is ChatBubbleShape);
      expect(bubbles.length, 3);
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
      scroll.dispose();
      store.dispose();
    },
  );
  testWidgets(
    'Drawer fades only the clipped session list, not its header and footer',
    (tester) async {
      tester.view.physicalSize = const Size(390, 844);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final store = PicoStore(await SharedPreferences.getInstance());
      for (var i = 0; i < 18; i++) {
        store.newSession();
        await store.savePlace('Session ${i + 1}');
        await store.savePlace('Follow up ${i + 1}');
      }
      expect(store.sessions.length, 18);
      await tester.pumpWidget(
        RepaintBoundary(
          key: const ValueKey('interface-preview'),
          child: MaterialApp(
            theme: PicoTheme.dark,
            debugShowCheckedModeBanner: false,
            home: Scaffold(
              backgroundColor: PicoTheme.drawer,
              body: SessionDrawer(
                store: store,
                width: 300,
                onClose: () {},
                onSettings: () {},
              ),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();
      final mask = tester.widget<ShaderMask>(
        find.descendant(
          of: find.byType(ScrollEdgeFade),
          matching: find.byType(ShaderMask),
        ),
      );
      expect(mask.blendMode, BlendMode.dstIn);
      expect(
        find.descendant(
          of: find.byType(ScrollEdgeFade),
          matching: find.byTooltip('Settings'),
        ),
        findsNothing,
      );
      expect(find.textContaining('Follow up'), findsNothing);
      await tester.drag(find.byType(ListView), const Offset(0, -210));
      await tester.pumpAndSettle();
      await capturePreview(tester, 'drawer-session-fades');
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
      store.dispose();
    },
  );
}
