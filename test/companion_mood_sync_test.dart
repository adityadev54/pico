import 'package:flutter_test/flutter_test.dart';
import 'package:pico/services/character_sync.dart';

void main() {
  test('live moods refresh before desktop lease expires; brief reactions do not replay', () {
    final sent = DateTime.utc(2026, 11, 3);
    for (final mood in [
      'working',
      'thinking',
      'needsYou',
      'sleepy',
      'curious',
    ]) {
      expect(
        shouldRefreshCompanionMood(
          mood,
          sent,
          sent.add(const Duration(seconds: 19)),
        ),
        isFalse,
      );
      expect(
        shouldRefreshCompanionMood(
          mood,
          sent,
          sent.add(const Duration(seconds: 20)),
        ),
        isTrue,
      );
    }
    for (final mood in [
      'happy',
      'angry',
      'surprised',
      'done',
      'stuck',
      'idle',
    ]) {
      expect(
        shouldRefreshCompanionMood(
          mood,
          sent,
          sent.add(const Duration(minutes: 2)),
        ),
        isFalse,
      );
    }
  });
}
