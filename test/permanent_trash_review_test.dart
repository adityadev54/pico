import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pico/components/permanent_trash_review.dart';
import 'package:pico/theme/app_theme.dart';

void main() {
  testWidgets(
    'permanent trash action requires exactly EMPTY and can be cancelled',
    (tester) async {
      bool? result;
      await tester.pumpWidget(
        MaterialApp(
          theme: PicoTheme.light,
          home: Scaffold(
            body: Builder(
              builder: (context) => TextButton(
                onPressed: () async {
                  result = await confirmPermanentTrash(context);
                },
                child: const Text('Review'),
              ),
            ),
          ),
        ),
      );
      await tester.tap(find.text('Review'));
      await tester.pumpAndSettle();
      expect(find.text('Empty permanently'), findsNothing);
      await tester.enterText(find.byType(TextField), 'empty');
      await tester.pump();
      expect(find.text('Empty permanently'), findsNothing);
      await tester.enterText(find.byType(TextField), 'EMPTY');
      await tester.pump();
      expect(find.text('Empty permanently'), findsOneWidget);
      await tester.tap(find.text('Cancel'));
      await tester.pumpAndSettle();
      expect(result, isFalse);
    },
  );
}
