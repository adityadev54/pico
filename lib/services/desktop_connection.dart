import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'relay_client.dart';

class DesktopConnection extends ChangeNotifier {
  DesktopConnection(this.preferences, {RelayClient? relay})
    : relay = relay ?? RelayClient();
  final SharedPreferences preferences;
  final RelayClient relay;
  String? token, deviceId, error;
  String character = 'tuck', size = 'medium', mood = 'idle';
  final List<Map<String, dynamic>> places = [];
  bool busy = false, online = false, _polling = false;
  Timer? _timer, _moodTimer;
  bool get paired => token != null;
  Future<void> load() async {
    token = preferences.getString('pico.desktop.token');
    deviceId = preferences.getString('pico.desktop.id');
    final savedCharacter = preferences.getString('pico.desktop.character');
    character = ['tuck', 'mica'].contains(savedCharacter)
        ? savedCharacter!
        : 'tuck';
    if (savedCharacter != character) {
      await preferences.setString('pico.desktop.character', character);
    }
    size = preferences.getString('pico.desktop.size') ?? 'medium';
    try {
      places.addAll(
        (jsonDecode(
          preferences.getString('pico.desktop.places') ?? '[]',
        ) as List).map((e) => Map<String, dynamic>.from(e)),
      );
    } catch (_) {
      error = 'Saved desktop Places could not be read.';
    }
    if (paired) {
      await poll();
      _start();
    }
    notifyListeners();
  }

  void _start() {
    _timer?.cancel();
    _timer = Timer.periodic(const Duration(seconds: 3), (_) => poll());
  }

  Future<void> pair(String code) async {
    if (busy) return;
    busy = true;
    error = null;
    notifyListeners();
    try {
      final result = await relay.request(
        '/claim',
        body: {
          'code': code,
          'os': defaultTargetPlatform == TargetPlatform.macOS
              ? 'macos'
              : 'windows',
          'name': 'Desktop companion',
        },
      );
      token = result['token'] as String;
      deviceId = result['device_id'] as String;
      await preferences.setString('pico.desktop.token', token!);
      await preferences.setString('pico.desktop.id', deviceId!);
      await poll();
      _start();
    } on RelayException catch (e) {
      error = e.message;
    } catch (_) {
      error = 'Couldn’t reach Pico. Start the relay and try again.';
    } finally {
      busy = false;
      notifyListeners();
    }
  }

  Future<void> poll() async {
    if (!paired || _polling) return;
    _polling = true;
    try {
      final result = await relay.request('/agent/poll', token: token, body: {});
      online = true;
      error = null;
      final acknowledged = <String>[];
      for (final raw in result['mail'] as List) {
        final message = Map<String, dynamic>.from(raw);
        final data = Map<String, dynamic>.from(message['payload']);
        if (message['kind'] == 'companion') {
          final selected = data['character'] as String?;
          character = ['tuck', 'mica'].contains(selected) ? selected! : 'tuck';
          size = data['size'] as String? ?? size;
          _moodTimer?.cancel();
          final until = int.tryParse(data['mood_until'] as String? ?? '') ?? 0;
          final remaining = until - DateTime.now().millisecondsSinceEpoch;
          mood = remaining > 0 ? data['mood'] as String? ?? 'idle' : 'idle';
          if (mood != 'idle') {
            _moodTimer = Timer(
              Duration(milliseconds: remaining.clamp(0, 60000)),
              () {
                mood = 'idle';
                notifyListeners();
              },
            );
          }
          await preferences.setString('pico.desktop.character', character);
          await preferences.setString('pico.desktop.size', size);
        }
        if (message['kind'] == 'place' &&
            !places.any((p) => p['place_id'] == data['place_id'])) {
          places.insert(0, data);
        }
        acknowledged.add(message['id'] as String);
      }
      await preferences.setString('pico.desktop.places', jsonEncode(places));
      if (acknowledged.isNotEmpty) {
        await relay.request(
          '/agent/ack',
          token: token,
          body: {'ids': acknowledged},
        );
      }
    } on RelayException catch (e) {
      online = false;
      error = e.message;
      if (e.status == 401) {
        token = null;
        deviceId = null;
        _timer?.cancel();
        await preferences.remove('pico.desktop.token');
        await preferences.remove('pico.desktop.id');
        places.clear();
        await preferences.remove('pico.desktop.places');
      }
    } catch (_) {
      online = false;
      error = 'Offline. Waiting to reconnect.';
    } finally {
      _polling = false;
      notifyListeners();
    }
  }

  Future<void> dismiss(String id) async {
    places.removeWhere((p) => p['place_id'] == id);
    await preferences.setString('pico.desktop.places', jsonEncode(places));
    notifyListeners();
  }

  @override
  void dispose() {
    _timer?.cancel();
    _moodTimer?.cancel();
    relay.close();
    super.dispose();
  }
}
