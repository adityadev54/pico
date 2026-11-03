import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pico/components/request_composer.dart';
import 'package:pico/theme/app_theme.dart';

void main() {
  testWidgets(
    'Plus menu routes camera and microphone without sending a message',
    (tester) async {
      final controller = TextEditingController();
      addTearDown(controller.dispose);
      var camera = 0, voice = 0, sent = 0;
      await tester.pumpWidget(
        MaterialApp(
          theme: PicoTheme.light,
          home: Scaffold(
            body: RequestComposer(
              controller: controller,
              listening: false,
              busy: false,
              autofocus: false,
              onVoice: () => voice++,
              onSend: () => sent++,
              onCamera: () => camera++,
            ),
          ),
        ),
      );
      await tester.tap(find.byTooltip('Add'));
      await tester.pumpAndSettle();
      expect(find.text('Camera'), findsOneWidget);
      expect(find.text('Companion mood'), findsNothing);
      await tester.tap(find.text('Camera'));
      await tester.pumpAndSettle();
      expect(camera, 1);
      expect(sent, 0);
      await tester.tap(find.byTooltip('Add'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Microphone'));
      await tester.pumpAndSettle();
      expect(voice, 1);
      expect(sent, 0);
    },
  );
}
