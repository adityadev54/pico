import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:pico/components/task_bubble.dart';
import 'package:pico/services/pico_store.dart';
import 'package:pico/theme/app_theme.dart';

class DocumentStore extends PicoStore {
  DocumentStore(super.preferences);
  final calls = <Map<String, dynamic>>[];
  @override
  Future<void> requestTask(
    String device,
    String kind,
    Map<String, dynamic> input, {
    String? utterance,
    bool confirmed = false,
  }) async {
    calls.add({'kind': kind, 'input': input, 'confirmed': confirmed});
  }
}

void main() {
  testWidgets(
    'saved camera photo offers one reviewed local PDF action using its folder',
    (tester) async {
      SharedPreferences.setMockInitialValues({});
      final store = DocumentStore(await SharedPreferences.getInstance());
      store.devices = [
        {
          'id': 'mac',
          'document_tools': ['convert_file', 'pdf_pages'],
        },
      ];
      final task = <String, dynamic>{
        'id': 'upload',
        'device_id': 'mac',
        'kind': 'receive_upload',
        'status': 'completed',
        'input': {'name': 'Homework photo.jpg', 'grant_id': 'approved-folder'},
        'result': {'path': 'Homework photo.jpg'},
      };
      await tester.pumpWidget(
        MaterialApp(
          theme: PicoTheme.light,
          home: Scaffold(
            body: TaskBubble(task: task, store: store),
          ),
        ),
      );
      await tester.tap(find.text('Make PDF'));
      await tester.pumpAndSettle();
      expect(find.text('Convert file?'), findsOneWidget);
      await tester.tap(find.text('Cancel'));
      await tester.pumpAndSettle();
      expect(store.calls, isEmpty);
      await tester.tap(find.text('Make PDF'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Approve'));
      await tester.pumpAndSettle();
      expect(store.calls.single, {
        'kind': 'convert_file',
        'input': {
          'path': 'Homework photo.jpg',
          'to': 'pdf',
          'grant_id': 'approved-folder',
        },
        'confirmed': true,
      });
      await tester.pumpWidget(const SizedBox());
      store.dispose();
    },
  );
  testWidgets('converted result reuses exact-file search before transfer', (
    tester,
  ) async {
    SharedPreferences.setMockInitialValues({});
    final store = DocumentStore(await SharedPreferences.getInstance());
    final task = <String, dynamic>{
      'id': 'pdf',
      'device_id': 'mac',
      'kind': 'convert_file',
      'status': 'completed',
      'input': {'grant_id': 'approved-folder'},
      'result': {'path': 'Homework photo.pdf'},
    };
    await tester.pumpWidget(
      MaterialApp(
        theme: PicoTheme.light,
        home: Scaffold(
          body: TaskBubble(task: task, store: store),
        ),
      ),
    );
    await tester.tap(find.text('Get file'));
    await tester.pump();
    expect(store.calls.single, {
      'kind': 'find_document',
      'input': {'query': 'Homework photo.pdf', 'grant_id': 'approved-folder'},
      'confirmed': false,
    });
    await tester.pumpWidget(const SizedBox());
    store.dispose();
  });
}
