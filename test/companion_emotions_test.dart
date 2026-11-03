import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pico/components/companion_image.dart';
import 'package:pico/theme/app_theme.dart';

void main() {
  testWidgets('New moods keep the original animated GIF character', (
    tester,
  ) async {
    const activities = {
      'angry': 'stuck',
      'curious': 'thinking',
      'happy': 'done',
      'sleepy': 'idle',
      'surprised': 'needsYou',
    };
    for (final character in ['mica', 'tuck']) {
      for (final entry in activities.entries) {
        await tester.pumpWidget(
          MaterialApp(
            home: CompanionImage(
              character: character,
              mood: entry.key,
              size: 168,
            ),
          ),
        );
        final image = tester.widget<Image>(find.byType(Image));
        expect(
          (image.image as AssetImage).assetName,
          'assets/characters/$character/${entry.value}.gif',
        );
      }
    }
    await tester.pumpWidget(const SizedBox());
  });
  for (final character in ['mica', 'tuck']) {
    testWidgets('$character renders every new mood with reduced motion', (
      tester,
    ) async {
      for (final mood in companionEmotions) {
        await tester.pumpWidget(
          MaterialApp(
            theme: PicoTheme.light,
            home: MediaQuery(
              data: const MediaQueryData(disableAnimations: true),
              child: Scaffold(
                body: Center(
                  child: CompanionImage(
                    character: character,
                    mood: mood,
                    size: 168,
                  ),
                ),
              ),
            ),
          ),
        );
        await tester.runAsync(
          () => Future<void>.delayed(const Duration(milliseconds: 40)),
        );
        await tester.pump();
        expect(find.bySemanticsLabel('$character, $mood'), findsOneWidget);
        expect(tester.takeException(), isNull);
      }
      await tester.pumpWidget(const SizedBox());
    });
  }
}
