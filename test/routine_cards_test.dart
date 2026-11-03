import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:pico/components/routine_cards.dart';
import 'package:kin_ui/kin_ui.dart';
import 'package:pico/components/conversation_view.dart';
import 'package:pico/services/pico_store.dart';
import 'package:pico/theme/app_theme.dart';

void main() {
  for (final size in [
    const Size(320, 700),
    const Size(844, 390),
    const Size(1100, 800),
  ]) {
    testWidgets('One inline card works at $size with larger text', (
      tester,
    ) async {
      tester.view.physicalSize = size;
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      SharedPreferences.setMockInitialValues({});
      final store = PicoStore(await SharedPreferences.getInstance());
      addTearDown(store.dispose);
      store.routinesVisible = true;
      store.routines.add({
        'id': 'brief',
        'name': 'Prepare my client brief',
        'runs': 0,
        'sources': ['Customer research and interview findings.md'],
      });
      final scroll = ScrollController();
      addTearDown(scroll.dispose);
      await tester.pumpWidget(
        MaterialApp(
          theme: PicoTheme.light,
          home: MediaQuery(
            data: MediaQueryData(
              size: size,
              textScaler: const TextScaler.linear(1.5),
              disableAnimations: true,
            ),
            child: Scaffold(
              body: ConversationView(
                store: store,
                controller: scroll,
                onDevices: () {},
                onCompose: () {},
                typing: true,
              ),
            ),
          ),
        ),
      );
      expect(find.byType(RoutineCards), findsOneWidget);
      await tester.ensureVisible(find.byType(KinListTile));
      await tester.pump();
      await tester.tap(find.byType(KinListTile));
      await tester.pump();
      expect(find.text('Run with these files'), findsOneWidget);
      expect(tester.takeException(), isNull);
      expect(
        store.reviewRoutineRequest('Could you prepare my client brief again?'),
        isTrue,
      );
      expect(store.routineReviewId, 'brief');
      await tester.pumpWidget(const SizedBox());
    });
  }
}
