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

void main() {
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
