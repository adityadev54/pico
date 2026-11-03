import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:pico/services/pico_store.dart';
import 'package:pico/services/local_play.dart';
import 'package:pico/services/command_parser.dart';

void main() {
  testWidgets(
    'offline guessing game stays local and real commands pass through',
    (tester) async {
      SharedPreferences.setMockInitialValues({});
      final store = PicoStore(await SharedPreferences.getInstance());
      expect(await store.handleLocalPlay('play a guessing game'), isTrue);
      store.pendingPrompt!['target'] = 7;
      expect(await store.handleLocalPlay('5'), isTrue);
      expect(store.places.first.sentence, contains('Too low'));
      expect(
        await store.handleLocalPlay('convert lecture.png to pdf'),
        isFalse,
      );
      expect(await store.handleLocalPlay('7'), isTrue);
      expect(store.pendingPrompt, isNull);
      expect(
        store.places
            .where((p) => p.role == 'user')
            .every((p) => p.delivery == 'request'),
        isTrue,
      );
      expect(store.tasks, isEmpty);
      store.dispose();
    },
  );
  testWidgets(
    'riddle cancellation and account reset stop pending games and timers',
    (tester) async {
      SharedPreferences.setMockInitialValues({});
      final store = PicoStore(await SharedPreferences.getInstance());
      await store.handleLocalPlay('riddle');
      expect(store.pendingPrompt?['kind'], 'riddle');
      await store.handleLocalPlay('give up');
      expect(store.pendingPrompt, isNull);
      await store.handleLocalPlay('set a timer for 2 seconds');
      expect(store.places.first.sentence, contains('while Pico is open'));
      final before = store.places.length;
      store.clearLocalPlay();
      await tester.pump(const Duration(seconds: 3));
      expect(store.places.length, before);
      store.dispose();
    },
  );
  testWidgets('timer completion is saved to the originating chat', (
    tester,
  ) async {
    SharedPreferences.setMockInitialValues({});
    final store = PicoStore(await SharedPreferences.getInstance());
    await store.handleLocalPlay('set a timer for 1 second');
    final first = store.current!.id;
    store.newSession();
    await store.handleLocalPlay('riddle');
    final second = store.current!.id;
    expect(second, isNot(first));
    await tester.pump(const Duration(seconds: 1));
    await tester.pump();
    final reply = store.places.firstWhere(
      (p) => p.sentence.contains("Time's up"),
    );
    expect(reply.chatId, first);
    store.dispose();
  });
  testWidgets('local game does not hide a computer approval state', (
    tester,
  ) async {
    SharedPreferences.setMockInitialValues({});
    final store = PicoStore(await SharedPreferences.getInstance());
    store.tasks.add({'status': 'awaiting_approval'});
    await store.handleLocalPlay('play');
    expect(store.mood, 'needsYou');
    store.dispose();
  });
  test('file management parser and local duration bounds', () {
    expect(parseComputerCommand('delete old draft.txt')?.input, {
      'path': 'old draft.txt',
      'confirm': 'DELETE',
    });
    expect(
      parseComputerCommand('restore old draft.txt')?.kind,
      'restore_deleted',
    );
    expect(
      parseComputerCommand('zip notes.txt and lecture.pdf as study.zip')?.input,
      {
        'action': 'create',
        'paths': ['notes.txt', 'lecture.pdf'],
        'output': 'study.zip',
      },
    );
    expect(parseComputerCommand('empty Pico trash')?.kind, 'empty_trash');
    expect(parseLocalPlay('set a timer for 0 seconds'), isNull);
    expect(parseDuration('999999999999999999999 seconds'), isNull);
  });
}
