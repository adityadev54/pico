import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:pico/services/relay_client.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:pico/services/pico_store.dart';
import 'package:pico/components/conversation_view.dart';
import 'package:pico/components/request_composer.dart';
import 'package:pico/components/task_bubble.dart';
import 'package:pico/components/task_text.dart';
import 'package:pico/components/pico_dialog.dart';
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
  test(
    'Chats retain their messages, request replies and selection after restart',
    () async {
      final prefs = await SharedPreferences.getInstance();
      final store = PicoStore(prefs)..loadPlaces();
      await store.savePlace('First conversation');
      final first = store.current!;
      await store.savePlace('Follow-up in first');
      expect(store.sessions.length, 1);
      store.newSession();
      expect(store.visiblePlaces, isEmpty);
      expect(store.sessions.length, 1); // No empty drawer rows.
      await store.rememberRequest('Create checklist.txt');
      final second = store.current!;
      store.tasks.add({
        'id': 'reply',
        'session_id': second.id,
        'kind': 'create_note',
        'created_at': DateTime.now()
            .add(const Duration(seconds: 1))
            .toIso8601String(),
      });
      expect(store.conversation.first.place!.sentence, 'Create checklist.txt');
      expect(store.conversation.last.task!['id'], 'reply');
      store.select(first);
      expect(store.visibleTasks, isEmpty);
      expect(store.visiblePlaces.length, 2);
      await store.savePlace('Another follow-up');
      expect(store.sessions.length, 2);
      final restored = PicoStore(prefs)..loadPlaces();
      expect(restored.sessions.length, 2);
      restored.select(restored.sessions.firstWhere((s) => s.id == first.id));
      expect(restored.visiblePlaces.length, 3);
      await restored.deleteSession(restored.current!);
      await restored.importTaskChats([
        {'id': 'old', 'session_id': first.id, 'kind': 'create_note'},
      ]);
      expect(restored.sessions.any((s) => s.id == first.id), isFalse);
      store.dispose();
      restored.dispose();
    },
  );
  testWidgets('Review opens a bottom sheet and reuses the selected workspace', (
    tester,
  ) async {
    var approvals = 0;
    final store = PicoStore(
      await SharedPreferences.getInstance(),
      relay: RelayClient(
        client: MockClient((request) async {
          if (request.url.path == '/tasks/approve') approvals++;
          return http.Response('{}', 200);
        }),
      ),
    );
    store.devices = [
      {
        'id': 'mac',
        'workspaces': [
          {'id': 'one', 'name': 'Notes', 'access': 'write'},
          {'id': 'two', 'name': 'Drafts', 'access': 'write'},
        ],
      },
    ];
    final task = {
      'id': 'proposal',
      'device_id': 'mac',
      'kind': 'create_note',
      'status': 'awaiting_approval',
      'input': {
        'grant_id': 'one',
        'name': 'checklist.txt',
        'text': 'Three items',
      },
      'result': {
        'proposal': {'kind': 'create_note'},
      },
    };
    await tester.pumpWidget(
      MaterialApp(
        theme: PicoTheme.light,
        home: Scaffold(
          body: TaskBubble(task: task, store: store),
        ),
      ),
    );
    await tester.tap(find.text('Review action'));
    await tester.pumpAndSettle();
    expect(find.text('Review this action'), findsOneWidget);
    expect(find.text('Choose a folder'), findsNothing);
    expect(find.byType(PicoDialog), findsOneWidget);
    expect(
      tester.getBottomRight(find.byType(PicoDialog)).dy,
      closeTo(
        tester.view.physicalSize.height / tester.view.devicePixelRatio - 12,
        2,
      ),
    );
    await tester.tap(find.text('Approve'));
    await tester.pumpAndSettle();
    expect(approvals, 1);
    expect(find.byType(PicoDialog), findsNothing);
    await tester.pumpWidget(const SizedBox());
    store.dispose();
  });
  for (final sample in [
    (390.0, 844.0, false),
    (390.0, 844.0, true),
    (844.0, 390.0, false),
    (1100.0, 800.0, false),
  ]) {
    testWidgets(
      'Conversation grows without inner scrolling at ${sample.$1}x${sample.$2} dark ${sample.$3}',
      (tester) async {
        tester.view.physicalSize = Size(sample.$1, sample.$2);
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);
        final store = PicoStore(await SharedPreferences.getInstance())
          ..loadPlaces();
        await store.rememberRequest(
          'Draft a three-item checklist into checklist.txt',
        );
        store.tasks.add({
          'id': 'result',
          'session_id': store.current!.id,
          'kind': 'create_note',
          'status': 'completed',
          'created_at': DateTime.now().toIso8601String(),
          'input': {
            'name': 'checklist.txt',
            'text': '1. Install Pico.\n2. Pair your computer.\n3. Verify your first file.',
          },
          'result': {'message': 'Created checklist.txt in Notes.'},
        });
        await store.savePlace('Can we keep it short?');
        final scroll = ScrollController();
        final text = TextEditingController();
        await tester.pumpWidget(
          RepaintBoundary(
            key: const ValueKey('interface-preview'),
            child: MaterialApp(
              theme: sample.$3 ? PicoTheme.dark : PicoTheme.light,
              debugShowCheckedModeBanner: false,
              home: Scaffold(
                body: Column(
                  children: [
                    Expanded(
                      child: ConversationView(
                        store: store,
                        controller: scroll,
                        onDevices: () {},
                        onCompose: () {},
                      ),
                    ),
                    RequestComposer(
                      controller: text,
                      listening: false,
                      busy: false,
                      onVoice: () {},
                      onSend: () {},
                      autofocus: false,
                    ),
                  ],
                ),
              ),
            ),
          ),
        );
        await tester.pumpAndSettle();
        expect(
          find.descendant(
            of: find.byType(TaskText),
            matching: find.byType(Scrollable),
          ),
          findsNothing,
        );
        expect(find.text('Ask or save a thought…'), findsOneWidget);
        expect(tester.takeException(), isNull);
        await capturePreview(
          tester,
          'chat-${sample.$1.toInt()}-${sample.$2.toInt()}-${sample.$3 ? "dark" : "light"}',
        );
        await tester.pumpWidget(const SizedBox());
        scroll.dispose();
        text.dispose();
        store.dispose();
      },
    );
  }
}
