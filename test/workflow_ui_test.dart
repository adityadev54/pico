import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:pico/components/home_controls.dart';
import 'package:pico/components/task_bubble.dart';
import 'package:pico/services/pico_store.dart';
import 'package:pico/theme/app_theme.dart';

import 'helpers/capture_preview.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUpAll(() async {
    final font = FontLoader('DM Sans')
      ..addFont(rootBundle.load('assets/fonts/DMSans.ttf'));
    await font.load();
  });
  setUp(() => SharedPreferences.setMockInitialValues({}));
  testWidgets('Muse indicator reflects the reported status', (tester) async {
    final store = PicoStore(await SharedPreferences.getInstance())
      ..museState = 'ready'
      ..museLabel = 'Muse connected';
    await tester.pumpWidget(
      MaterialApp(
        theme: PicoTheme.light,
        home: Scaffold(
          body: HomeControls(
            store: store,
            onMenu: () {},
            onType: () {},
            onSearch: () {},
          ),
        ),
      ),
    );
    expect(find.byTooltip('Muse connected'), findsOneWidget);
    store.dispose();
  });
  for (final dark in [false, true]) {
    testWidgets(
      'File actions and opt-in summary fit ${dark ? 'dark' : 'light'} phone',
      (tester) async {
        tester.view.physicalSize = const Size(390, 844);
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);
        final store = PicoStore(await SharedPreferences.getInstance())
          ..museState = 'ready';
        final task = <String, dynamic>{
          'id': 'test',
          'kind': 'read_file',
          'status': 'completed',
          'device_id': 'device',
          'result': {
            'path': 'brief.txt',
            'content': 'A selected document excerpt. ' * 12,
            'digest': 'a' * 64,
          },
        };
        await tester.pumpWidget(
          RepaintBoundary(
            key: const ValueKey('interface-preview'),
            child: MaterialApp(
              theme: dark ? PicoTheme.dark : PicoTheme.light,
              home: Scaffold(
                body: SingleChildScrollView(
                  child: Padding(
                    padding: const EdgeInsets.only(
                      top: 70,
                      left: 12,
                      right: 12,
                    ),
                    child: TaskBubble(task: task, store: store),
                  ),
                ),
              ),
            ),
          ),
        );
        expect(find.text('Edit file'), findsOneWidget);
        expect(find.byTooltip('Summarize with Muse'), findsOneWidget);
        await capturePreview(tester, dark ? 'workflow-dark' : 'workflow-light');
        await tester.ensureVisible(find.byTooltip('Summarize with Muse'));
        await tester.tap(find.byTooltip('Summarize with Muse'));
        await tester.pumpAndSettle();
        expect(find.text('Summarize with Muse?'), findsOneWidget);
        expect(find.textContaining('1,500 characters'), findsOneWidget);
        await tester.tap(find.text('Cancel'));
        await tester.pumpAndSettle();
        expect(store.busy, isFalse);
        expect(tester.takeException(), isNull);
        await tester.pumpWidget(const SizedBox());
        store.dispose();
      },
    );
  }
}
