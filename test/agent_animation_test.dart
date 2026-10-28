import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pico/components/place_empty_state.dart';
import 'package:pico/theme/app_theme.dart';

void main() {
  testWidgets(
    'Empty home uses the selected Tuck state and double tap starts voice',
    (tester) async {
      var spoke = false;
      for (final mood in ['idle', 'listening', 'talking', 'working']) {
        await tester.pumpWidget(
          MaterialApp(
            theme: PicoTheme.light,
            home: Scaffold(
              body: PlaceEmptyState(
                character: 'tuck',
                mood: mood,
                typing: false,
                onCompose: () {},
                onVoice: () => spoke = true,
              ),
            ),
          ),
        );
        final picture = tester.widget<Image>(find.byType(Image));
        expect(
          (picture.image as AssetImage).assetName,
          'assets/characters/tuck/$mood.gif',
        );
      }
      await tester.tap(find.byType(Image));
      await tester.pump(const Duration(milliseconds: 80));
      await tester.tap(find.byType(Image));
      await tester.pump(const Duration(milliseconds: 60));
      expect(spoke, isTrue);
      await tester.pumpWidget(const SizedBox());
    },
  );
  testWidgets('Reduced motion uses a state-specific still', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: MediaQuery(
          data: const MediaQueryData(disableAnimations: true),
          child: Scaffold(
            body: PlaceEmptyState(
              character: 'tuck',
              mood: 'working',
              typing: false,
              onCompose: () {},
            ),
          ),
        ),
      ),
    );
    expect(
      (tester.widget<Image>(find.byType(Image)).image as AssetImage).assetName,
      'assets/characters/tuck/working.png',
    );
    await tester.pumpWidget(const SizedBox());
  });
}
