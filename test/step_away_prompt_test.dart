import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:pico/components/conversation_view.dart';
import 'package:pico/models/place.dart';
import 'package:pico/services/pico_store.dart';
import 'package:pico/theme/app_theme.dart';

void main() {
  testWidgets('step-away prompt is actionable in an existing conversation', (
    tester,
  ) async {
    SharedPreferences.setMockInitialValues({});
    final store = PicoStore(await SharedPreferences.getInstance());
    store.places.add(
      Place(
        id: 'earlier',
        sentence: 'An earlier saved thought',
        created: DateTime.now(),
      ),
    );
    store.pendingPlaceId = 'pending';
    final scroll = ScrollController();
    var composed = false;
    await tester.pumpWidget(
      MaterialApp(
        theme: PicoTheme.light,
        home: Scaffold(
          body: ConversationView(
            store: store,
            controller: scroll,
            onDevices: () {},
            onCompose: () {
              composed = true;
            },
          ),
        ),
      ),
    );
    await tester.ensureVisible(find.text('What were you about to do?'));
    await tester.tap(find.text('What were you about to do?'));
    expect(composed, isTrue);
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox());
    scroll.dispose();
    store.dispose();
  });
}
