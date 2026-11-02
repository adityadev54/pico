import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:pico/components/computer_actions.dart';
import 'package:pico/services/pico_store.dart';

class RecordingStore extends PicoStore {
  RecordingStore(super.preferences);
  int calls = 0;
  String? requestedText, workspace;
  @override
  Future<void> askPico(String device, String text, {String? grantId}) async {
    calls++;
    requestedText = text;
    workspace = grantId;
  }
}

class ReviewStore extends PicoStore {
  ReviewStore(super.preferences);
  final requests = <Map<String, dynamic>>[];
  @override
  Future<void> requestTask(
    String device,
    String kind,
    Map<String, dynamic> input, {
    String? utterance,
    bool confirmed = false,
  }) async {
    requests.add({
      'device': device,
      'kind': kind,
      'input': input,
      'confirmed': confirmed,
    });
  }
}

Future<(ReviewStore, BuildContext)> _reviewSetup(WidgetTester tester) async {
  SharedPreferences.setMockInitialValues({});
  tester.view.physicalSize = const Size(390, 844);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  final store = ReviewStore(await SharedPreferences.getInstance());
  store.devices = [
    {
      'id': 'mac',
      'name': 'Mac',
      'os': 'macos',
      'workspaces': [
        {'id': 'folder', 'name': 'Test folder', 'access': 'write'},
      ],
    },
  ];
  late BuildContext screen;
  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: Builder(
          builder: (context) {
            screen = context;
            return const SizedBox();
          },
        ),
      ),
    ),
  );
  return (store, screen);
}

void main() {
  testWidgets('convert asks review once then sends confirmed', (tester) async {
    final (store, screen) = await _reviewSetup(tester);
    final pending = dispatchComputerAction(
      screen,
      store,
      'convert scan.jpg to pdf',
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.text('Review this action'), findsOneWidget);
    await tester.tap(find.text('Approve'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    expect(await pending, isTrue);
    expect(store.requests, hasLength(1));
    expect(store.requests.single['kind'], 'convert_file');
    expect(store.requests.single['confirmed'], isTrue);
    await tester.pumpWidget(const SizedBox());
    store.dispose();
  });

  testWidgets('refused review sends nothing', (tester) async {
    final (store, screen) = await _reviewSetup(tester);
    final pending = dispatchComputerAction(
      screen,
      store,
      'convert scan.jpg to pdf',
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    await tester.tap(find.text('Cancel'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    expect(await pending, isTrue);
    expect(store.requests, isEmpty);
    await tester.pumpWidget(const SizedBox());
    store.dispose();
  });

  testWidgets('pdf edit asks review once then sends confirmed', (tester) async {
    final (store, screen) = await _reviewSetup(tester);
    final pending = dispatchComputerAction(
      screen,
      store,
      'merge a.pdf and b.pdf',
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.text('Review this action'), findsOneWidget);
    await tester.tap(find.text('Approve'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    expect(await pending, isTrue);
    expect(store.requests, hasLength(1));
    expect(store.requests.single['kind'], 'pdf_pages');
    expect(store.requests.single['input']['action'], 'merge');
    expect(store.requests.single['confirmed'], isTrue);
    await tester.pumpWidget(const SizedBox());
    store.dispose();
  });

  testWidgets('delete asks review once then sends confirmed', (tester) async {
    final (store, screen) = await _reviewSetup(tester);
    final pending = dispatchComputerAction(screen, store, 'delete old.txt');
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.text('Review this action'), findsOneWidget);
    await tester.tap(find.text('Approve'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    expect(await pending, isTrue);
    expect(store.requests, hasLength(1));
    expect(store.requests.single['kind'], 'delete_files');
    expect(store.requests.single['input']['confirm'], 'DELETE');
    expect(store.requests.single['confirmed'], isTrue);
    await tester.pumpWidget(const SizedBox());
    store.dispose();
  });

  testWidgets('convert with no granted folders guides instead of queuing', (
    tester,
  ) async {
    SharedPreferences.setMockInitialValues({});
    final store = ReviewStore(await SharedPreferences.getInstance());
    store.devices = [
      {'id': 'mac', 'name': 'Mac', 'os': 'macos', 'workspaces': []},
    ];
    late BuildContext screen;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Builder(
            builder: (context) {
              screen = context;
              return const SizedBox();
            },
          ),
        ),
      ),
    );
    expect(
      await dispatchComputerAction(screen, store, 'convert scan.jpg to pdf'),
      isTrue,
    );
    await tester.pump();
    expect(store.requests, isEmpty);
    expect(
      find.text('Choose an approved folder on your computer first.'),
      findsOneWidget,
    );
    await tester.pumpWidget(const SizedBox());
    store.dispose();
  });

  testWidgets('find goes through so the computer can ask once', (tester) async {
    SharedPreferences.setMockInitialValues({});
    final store = ReviewStore(await SharedPreferences.getInstance());
    store.devices = [
      {'id': 'mac', 'name': 'Mac', 'os': 'macos', 'workspaces': []},
    ];
    late BuildContext screen;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Builder(
            builder: (context) {
              screen = context;
              return const SizedBox();
            },
          ),
        ),
      ),
    );
    expect(
      await dispatchComputerAction(screen, store, 'find my brief'),
      isTrue,
    );
    await tester.pump();
    expect(store.requests, hasLength(1));
    expect(
      find.text('Choose an approved folder on your computer first.'),
      findsNothing,
    );
    expect(
      find.text('Check your computer too — approve the folder request there.'),
      findsOneWidget,
    );
    await tester.pumpWidget(const SizedBox());
    store.dispose();
  });

  testWidgets('each deleted file asks its own popup', (tester) async {
    final (store, screen) = await _reviewSetup(tester);
    final pending = dispatchComputerAction(
      screen,
      store,
      'delete a.txt and b.txt',
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.text('Review this action'), findsOneWidget);
    await tester.tap(find.text('Approve'));
    await tester.pumpAndSettle();
    expect(store.requests, hasLength(1));
    expect(store.requests.single['input']['path'], 'a.txt');
    expect(find.text('Review this action'), findsOneWidget);
    await tester.tap(find.text('Approve'));
    await tester.pumpAndSettle();
    expect(await pending, isTrue);
    expect(store.requests, hasLength(2));
    expect(store.requests[1]['input']['path'], 'b.txt');
    expect(store.requests[1]['confirmed'], isTrue);
    await tester.pumpWidget(const SizedBox());
    store.dispose();
  });

  testWidgets('cancel stops the delete batch', (tester) async {
    final (store, screen) = await _reviewSetup(tester);
    final pending = dispatchComputerAction(
      screen,
      store,
      'delete a.txt and b.txt',
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    await tester.tap(find.text('Approve'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Cancel'));
    await tester.pumpAndSettle();
    expect(await pending, isTrue);
    expect(store.requests, hasLength(1));
    expect(store.requests.single['input']['path'], 'a.txt');
    await tester.pumpWidget(const SizedBox());
    store.dispose();
  });

  testWidgets('delete-ranked workspace counts as writable', (tester) async {
    SharedPreferences.setMockInitialValues({});
    final store = RecordingStore(await SharedPreferences.getInstance());
    store.devices = [
      {
        'id': 'mac',
        'workspaces': [
          {'id': 'folder', 'name': 'Test folder', 'access': 'delete'},
        ],
      },
    ];
    late BuildContext screen;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Builder(
            builder: (context) {
              screen = context;
              return const SizedBox();
            },
          ),
        ),
      ),
    );
    expect(
      await dispatchComputerAction(
        screen,
        store,
        'Ask picko: Draft a three-item checklist into checklist.txt',
      ),
      isTrue,
    );
    await tester.pump();
    expect(store.calls, 1);
    expect(store.workspace, 'folder');
    await tester.pumpWidget(const SizedBox());
    store.dispose();
  });

  for (final writable in [false, true]) {
    testWidgets('Muse draft requires write access: $writable', (tester) async {
      SharedPreferences.setMockInitialValues({});
      final store = RecordingStore(await SharedPreferences.getInstance());
      store.devices = [
        {
          'id': 'mac',
          'workspaces': [
            {
              'id': 'folder',
              'name': 'Test folder',
              'access': writable ? 'write' : 'read',
            },
          ],
        },
      ];
      late BuildContext screen;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Builder(
              builder: (context) {
                screen = context;
                return const SizedBox();
              },
            ),
          ),
        ),
      );
      expect(
        await dispatchComputerAction(
          screen,
          store,
          'Ask picko: Draft a three-item checklist into checklist.txt',
        ),
        isTrue,
      );
      await tester.pump();
      expect(store.calls, writable ? 1 : 0);
      if (writable) {
        expect(store.workspace, 'folder');
        expect(store.requestedText, startsWith('Draft a three-item'));
      } else {
        expect(find.textContaining('Choose a write workspace'), findsOneWidget);
      }
      expect(store.places, isEmpty);
      await tester.pumpWidget(const SizedBox());
      store.dispose();
    });
  }
}
