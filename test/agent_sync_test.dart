import 'dart:async';
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:pico/services/pico_store.dart';
import 'package:pico/services/relay_client.dart';

class DelayedRelay extends RelayClient {
  final sent = <Map<String, dynamic>>[];
  final first = Completer<void>();
  @override
  Future<Map<String, dynamic>> request(
    String path, {
    String? token,
    Map<String, dynamic>? body,
  }) async {
    sent.add(body!);
    if (sent.length == 1) await first.future;
    return {'id': 'mail-${sent.length}', 'status': 'queued'};
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test(
    'Rapid agent and size changes serialize and finish with latest choice',
    () async {
      SharedPreferences.setMockInitialValues({});
      final account = SupabaseClient(
        'https://example.supabase.co',
        'public-test-key',
        authOptions: const AuthClientOptions(autoRefreshToken: false),
      );
      await account.auth.setInitialSession(
        jsonEncode({
          'access_token': 'test-token',
          'token_type': 'bearer',
          'refresh_token': 'test-refresh',
          'expires_in': 3600,
          'user': {
            'id': 'test-owner',
            'app_metadata': {},
            'user_metadata': {},
            'aud': 'authenticated',
            'created_at': '2026-01-01T00:00:00Z',
          },
        }),
      );
      final relay = DelayedRelay();
      final store = PicoStore(
        await SharedPreferences.getInstance(),
        accountClient: account,
        relay: relay,
      );
      store.devices = [
        {'id': 'computer'},
      ];
      final initial = store.chooseCharacter('mica');
      await Future<void>.delayed(Duration.zero);
      final latest = store.chooseCharacter('tuck');
      final size = store.setCharacterSize('large');
      await Future<void>.delayed(Duration.zero);
      expect(relay.sent.length, 1);
      relay.first.complete();
      await Future.wait([initial, latest, size]);
      expect(relay.sent.length, 2);
      expect(relay.sent.last['payload'], containsPair('character', 'tuck'));
      expect(relay.sent.last['payload'], containsPair('size', 'large'));
      expect(relay.sent.last['payload'], containsPair('mood', 'idle'));
      store.setMood('listening');
      await store.syncCompanion();
      expect(relay.sent.last['payload'], containsPair('mood', 'listening'));
      final expiry = int.parse(
        (relay.sent.last['payload'] as Map)['mood_until'] as String,
      );
      expect(expiry, greaterThan(DateTime.now().millisecondsSinceEpoch));
      await store.syncCompanion();
      expect(relay.sent.length, 3);
      store.dispose();
      await account.dispose();
    },
  );
}
