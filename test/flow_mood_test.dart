import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:pico/services/pico_store.dart';

void main() {
  testWidgets(
    'approval wins over ongoing work and historical success stays idle',
    (tester) async {
      SharedPreferences.setMockInitialValues({});
      final store = PicoStore(await SharedPreferences.getInstance());
      store.tasks.addAll([
        {'status': 'working'},
        {'status': 'awaiting_approval'},
      ]);
      store.resumeFlowMood();
      expect(store.mood, 'needsYou');
      store.tasks.removeLast();
      store.resumeFlowMood();
      expect(store.mood, 'working');
      store.tasks.single['status'] = 'completed';
      store.resumeFlowMood();
      expect(store.mood, 'idle');
      store.dispose();
    },
  );
  testWidgets('expression returns to original GIF state then current flow', (
    tester,
  ) async {
    SharedPreferences.setMockInitialValues({});
    final store = PicoStore(await SharedPreferences.getInstance());
    store.previewMood('happy');
    expect(store.mood, 'happy');
    await tester.pump(const Duration(milliseconds: 1200));
    expect(store.mood, 'done');
    store.tasks.add({'status': 'awaiting_approval'});
    await tester.pump(const Duration(seconds: 3));
    expect(store.mood, 'needsYou');
    store.dispose();
  });
  testWidgets(
    'idle becomes sleepy without refresh resetting the clock; approvals wake it',
    (tester) async {
      SharedPreferences.setMockInitialValues({});
      final store = PicoStore(await SharedPreferences.getInstance());
      store.resumeFlowMood();
      await tester.pump(const Duration(seconds: 40));
      store.resumeFlowMood();
      await tester.pump(const Duration(seconds: 21));
      expect(store.mood, 'sleepy');
      store.tasks.add({'status': 'awaiting_approval'});
      store.resumeFlowMood();
      expect(store.mood, 'needsYou');
      store.dispose();
    },
  );
}
