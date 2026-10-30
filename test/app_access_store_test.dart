import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:pico/services/pico_store.dart';
import 'package:pico/services/relay_client.dart';

class AppRelay extends RelayClient {
  static const appId = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
  final messages = <Map<String, dynamic>>[];
  final opened = <Map<String, dynamic>>[];
  bool confirm = false, online = true;
  String? pending;
  @override
  Future<Map<String, dynamic>> request(
    String path, {
    String? token,
    Map<String, dynamic>? body,
  }) async {
    if (path == '/devices') {
      return {
        'devices': [
          {
            'id': 'computer',
            'last_seen': online
                ? DateTime.now().toUtc().toIso8601String()
                : '2000-01-01T00:00:00Z',
          },
        ],
      };
    }
    if (path == '/mail') {
      if (body!['kind'] == 'apps_request') {
        messages.add({
          'id': 'catalog',
          'device_id': 'computer',
          'kind': 'app_catalog',
          'payload': {
            'catalog': jsonEncode([
              {'id': appId, 'name': 'Selected App'},
            ]),
          },
        });
      }
      if (body['kind'] == 'open_app') {
        opened.add(body);
        pending = (body['payload'] as Map)['request_id'] as String;
      }
      return {'id': 'message', 'status': 'queued'};
    }
    if (path == '/phone/mail') {
      if (confirm && pending != null) {
        messages.add({
          'id': 'result',
          'device_id': 'computer',
          'kind': 'app_result',
          'payload': {
            'app_id': appId,
            'request_id': pending,
            'result': 'opened',
            'message': 'Opened Selected App.',
          },
        });
        pending = null;
      }
      return {'mail': List<Map<String, dynamic>>.of(messages)};
    }
    if (path == '/phone/ack') {
      messages.removeWhere((m) => (body!['ids'] as List).contains(m['id']));
      return {'ok': true};
    }
    throw StateError(path);
  }
}

Future<SupabaseClient> account() async {
  final client = SupabaseClient(
    'https://example.supabase.co',
    'public-test-key',
    authOptions: const AuthClientOptions(autoRefreshToken: false),
  );
  await client.auth.setInitialSession(
    jsonEncode({
      'access_token': 'test-token',
      'token_type': 'bearer',
      'refresh_token': 'test-refresh',
      'expires_in': 3600,
      'user': {
        'id': 'app-owner',
        'app_metadata': {},
        'user_metadata': {},
        'aud': 'authenticated',
        'created_at': '2026-01-01T00:00:00Z',
      },
    }),
  );
  return client;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() => SharedPreferences.setMockInitialValues({}));
  test(
    'Only selected IDs are sent and success waits for desktop confirmation',
    () async {
      final client = await account(), relay = AppRelay();
      final store = PicoStore(
        await SharedPreferences.getInstance(),
        accountClient: client,
        relay: relay,
      );
      store.devices = [
        {'id': 'computer'},
      ];
      await store.loadApprovedApps();
      expect(store.approvedApps.single.name, 'Selected App');
      expect(store.appsLoading, false);
      await store.openApprovedApp(store.approvedApps.single);
      expect(store.openingAppId, AppRelay.appId);
      expect(store.appActionMessage, 'Waiting for your computer…');
      expect((relay.opened.single['payload'] as Map).keys.toSet(), {
        'app_id',
        'request_id',
      });
      relay.confirm = true;
      await store.sync();
      expect(store.openingAppId, isNull);
      expect(store.appActionMessage, 'Opened Selected App.');
      store.dispose();
      await client.dispose();
    },
  );
  test('Offline computers do not receive app opening requests', () async {
    final client = await account(), relay = AppRelay()..online = false;
    final store = PicoStore(
      await SharedPreferences.getInstance(),
      accountClient: client,
      relay: relay,
    );
    store.devices = [
      {'id': 'computer'},
    ];
    await store.loadApprovedApps();
    await store.openApprovedApp(store.approvedApps.single);
    expect(relay.opened, isEmpty);
    expect(store.appActionMessage, contains('offline'));
    store.dispose();
    await client.dispose();
  });
}
