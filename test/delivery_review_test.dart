import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:pico/services/pico_store.dart';
import 'package:pico/services/relay_client.dart';

import 'app_access_store_test.dart' show account;

class ReviewStore extends PicoStore {
  ReviewStore(super.preferences, {super.accountClient, super.relay});
  @override
  Future<void> refreshTasks() async {}
}

class DeliveryRelay extends RelayClient {
  DeliveryRelay(this.prefs);
  final SharedPreferences prefs;
  String device = 'first';
  bool failUpdates = false;
  final sent = <Map<String, dynamic>>[],
      incoming = <Map<String, dynamic>>[],
      acked = <String>[];
  final delivered = <String>{};
  void Function()? beforeAck;
  @override
  Future<Map<String, dynamic>> request(
    String path, {
    String? token,
    Map<String, dynamic>? body,
  }) async {
    switch (path) {
      case '/devices':
        return {
          'devices': [
            {
              'id': device,
              'last_seen': DateTime.now().toUtc().toIso8601String(),
            },
          ],
        };
      case '/ai/status':
        return {'state': 'restricted', 'label': 'Local test'};
      case '/mail':
        if (body!['kind'] == 'parked' && failUpdates) {
          throw const RelayException('offline', 503);
        }
        if (body['kind'] != 'companion') {
          sent.add(Map<String, dynamic>.from(body));
        }
        return {
          'id': 'mail-${body['device_id']}-${body['id']}',
          'status': 'queued',
        };
      case '/receipts':
        return {'delivered': delivered.toList()};
      case '/phone/mail':
        return {'mail': List<Map<String, dynamic>>.of(incoming)};
      case '/phone/ack':
        beforeAck?.call();
        acked.addAll((body!['ids'] as List).cast<String>());
        incoming.removeWhere((m) => acked.contains(m['id']));
        return {'ok': true};
      default:
        throw StateError(path);
    }
  }
}

class FailingPrefs implements SharedPreferences {
  FailingPrefs(this.real);
  final SharedPreferences real;
  bool fail = false;
  @override
  String? getString(String key) => real.getString(key);
  @override
  bool? getBool(String key) => real.getBool(key);
  @override
  List<String>? getStringList(String key) => real.getStringList(key);
  @override
  Future<bool> setString(String key, String value) {
    if (fail && key.startsWith('pico.places.')) {
      throw StateError('Simulated disk failure');
    }
    return real.setString(key, value);
  }

  @override
  Future<bool> setStringList(String key, List<String> value) =>
      real.setStringList(key, value);
  @override
  Future<bool> setBool(String key, bool value) => real.setBool(key, value);
  @override
  Future<bool> remove(String key) => real.remove(key);
  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnimplementedError(invocation.memberName.toString());
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() => SharedPreferences.setMockInitialValues({}));
  test('Phone persists replies and pending idle before ACK; failed persistence leaves mail retryable', () async {
    final client = await account(),
        real = await SharedPreferences.getInstance();
    final prefs = FailingPrefs(real), relay = DeliveryRelay(real);
    final store = ReviewStore(prefs, accountClient: client, relay: relay)
      ..loadPlaces();
    store.devices = [
      {'id': 'first'},
    ];
    await store.savePlace('Original');
    final id = store.places.single.id;
    relay.incoming.addAll([
      {
        'id': 'reply',
        'device_id': 'first',
        'kind': 'head_start',
        'payload': {'place_id': id, 'head_start': 'Saved reply'},
      },
      {
        'id': 'idle',
        'device_id': 'first',
        'kind': 'idle',
        'payload': {'place_id': 'pending'},
      },
    ]);
    prefs.fail = true;
    await store.sync();
    expect(relay.acked, isEmpty);
    expect(relay.incoming.length, 2);
    prefs.fail = false;
    store.loadPlaces();
    expect(store.places.single.headStart, isNull);
    relay.beforeAck = () {
      final saved = jsonDecode(real.getString('pico.places.app-owner')!) as Map;
      expect(saved['pending_place'], 'pending');
      expect((saved['places'] as List).single['head_start'], 'Saved reply');
    };
    await store.sync();
    expect(relay.acked, containsAll(['reply', 'idle']));
    final restored = ReviewStore(real, accountClient: client, relay: relay)
      ..loadPlaces();
    expect(restored.pendingPlaceId, 'pending');
    expect(restored.places.single.headStart, 'Saved reply');
    store.dispose();
    restored.dispose();
    await client.dispose();
  });
  test('Undelivered note follows a changed device and old receipts cannot claim delivery', () async {
    final client = await account(),
        prefs = await SharedPreferences.getInstance();
    final relay = DeliveryRelay(prefs);
    final store = ReviewStore(prefs, accountClient: client, relay: relay)
      ..loadPlaces();
    store.devices = [
      {'id': 'first'},
    ];
    await store.savePlace('Move only while queued');
    final oldMail = store.places.single.mailId!;
    expect(store.places.single.deliveryDeviceId, 'first');
    relay.device = 'second';
    relay.delivered.add(oldMail);
    await store.sync();
    expect(store.places.single.deliveryDeviceId, 'second');
    expect(store.places.single.delivery, 'queued');
    expect(
      relay.sent.where((m) => m['kind'] == 'place').map((m) => m['device_id']),
      ['first', 'second'],
    );
    relay.delivered.add(store.places.single.mailId!);
    await store.sync();
    expect(store.places.single.delivery, 'delivered');
    relay.device = 'third';
    await store.sync();
    expect(relay.sent.where((m) => m['kind'] == 'place').length, 2);
    store.dispose();
    await client.dispose();
  });
  test('Park and Done updates persist offline and retry only for their owned device', () async {
    final client = await account(),
        prefs = await SharedPreferences.getInstance();
    final relay = DeliveryRelay(prefs);
    final store = ReviewStore(prefs, accountClient: client, relay: relay)
      ..loadPlaces();
    store.devices = [
      {'id': 'first'},
    ];
    await store.savePlace('Remember this');
    relay.failUpdates = true;
    await store.updatePlace(store.places.single, parked: true);
    expect(store.places.single.parked, isTrue);
    final restored = ReviewStore(prefs, accountClient: client, relay: relay)
      ..loadPlaces();
    expect(restored.places.single.parked, isTrue);
    relay.failUpdates = false;
    await restored.sync();
    expect(
      relay.sent
          .where((m) => m['kind'] == 'parked')
          .single['payload']['status'],
      'parked',
    );
    await restored.updatePlace(restored.places.single, finished: true);
    expect(restored.places.single.parked, isFalse);
    expect(
      relay.sent.where((m) => m['kind'] == 'parked').last['payload']['status'],
      'finished',
    );
    expect(
      (jsonDecode(prefs.getString('pico.places.app-owner')!) as Map)['updates'],
      isEmpty,
    );
    store.dispose();
    restored.dispose();
    await client.dispose();
  });
}
