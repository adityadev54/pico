part of 'pico_store.dart';

extension PicoConnectionStore on PicoStore {
  Future<void> _deliverPlaces() async {
    if (_token == null || devices.isEmpty) return;
    for (final place in List<Place>.of(
      places.where((p) => !p.finished && p.delivery == 'local'),
    )) {
      try {
        final result = await relay.request(
          '/mail',
          token: _token,
          body: {
            'device_id': devices.first['id'],
            'id': place.id,
            'kind': 'place',
            'payload': {'place_id': place.id, 'sentence': place.sentence},
          },
        );
        final i = places.indexWhere((p) => p.id == place.id);
        if (i >= 0) {
          places[i] = places[i].copyWith(
            delivery: result['status'] as String,
            mailId: result['id'] as String,
          );
        }
        await _persist();
      } on RelayException catch (e) {
        error = 'Saved here. ${e.message}';
        return;
      } catch (_) {
        error = 'Saved here. Computer delivery will retry when connected.';
        return;
      }
    }
  }

  Future<void> sync() => refreshDevices();
  Future<void> refreshDevices() async {
    if (!signedIn || _refreshing) return;
    _refreshing = true;
    final owner = userId;
    final token = _token;
    try {
      final result = await relay.request('/devices', token: token);
      if (userId != owner) return;
      devices = (result['devices'] as List)
          .map((e) => Map<String, dynamic>.from(e))
          .toList();
      await syncCompanion();
      await _deliverPlaces();
      await refreshTasks();
      final ids = places
          .map((p) => p.mailId)
          .whereType<String>()
          .take(100)
          .toList();
      if (ids.isNotEmpty) {
        final receipts = await relay.request(
          '/receipts',
          token: _token,
          body: {'ids': ids},
        );
        final delivered = (receipts['delivered'] as List)
            .cast<String>()
            .toSet();
        for (var i = 0; i < places.length; i++) {
          if (delivered.contains(places[i].mailId)) {
            places[i] = places[i].copyWith(delivery: 'delivered');
          }
        }
      }
      if (userId != owner) return;
      final incoming = await relay.request('/phone/mail', token: token);
      if (userId != owner) return;
      var tasksChanged = false;
      for (final raw in incoming['mail'] as List) {
        final message = Map<String, dynamic>.from(raw);
        final data = Map<String, dynamic>.from(message['payload']);
        if (message['kind'] == 'idle') {
          pendingPlaceId = data['place_id'] as String?;
        }
        if (message['kind'] == 'parked') {
          final i = places.indexWhere((p) => p.id == data['place_id']);
          if (i >= 0) places[i] = places[i].copyWith(parked: true);
        }
        if (message['kind'] == 'head_start') {
          final i = places.indexWhere((p) => p.id == data['place_id']);
          if (i >= 0) {
            places[i] = places[i].copyWith(
              headStart: data['head_start'] as String?,
            );
            setMood('talking');
            _moodTimer = Timer(
              const Duration(seconds: 8),
              () => setMood('idle'),
            );
          }
        }
        if (message['kind'] == 'tool_result') {
          tasksChanged = true;
        }
        await relay.request(
          '/phone/ack',
          token: _token,
          body: {
            'device_id': message['device_id'],
            'ids': [message['id']],
          },
        );
      }
      if (tasksChanged) await refreshTasks();
      await _persist();
    } catch (_) {
      // Preserve the last real heartbeat. It ages into Offline, never Connected.
    } finally {
      _refreshing = false;
      _changed();
    }
  }

  Future<void> syncCompanion() {
    return _companionSync ??= _syncCompanion().whenComplete(() {
      _companionSync = null;
    });
  }

  Future<void> _syncCompanion() async {
    // Serialize carousel changes so a slower, older request cannot win.
    while (_token != null && devices.isNotEmpty) {
      final owner = userId;
      final selected = character;
      final size = characterSize;
      final device = devices.first['id'];
      final activity = mood;
      final key = '$device:$selected:$size:$activity';
      if (_sentCompanion == key) return;
      await relay.request(
        '/mail',
        token: _token,
        body: {
          'device_id': device,
          'id': _uuid(),
          'kind': 'companion',
          'payload': {
            'character': selected,
            'size': size,
            'mood': activity,
            'mood_until': DateTime.now()
                .toUtc()
                .add(const Duration(seconds: 60))
                .millisecondsSinceEpoch
                .toString(),
          },
        },
      );
      if (owner != userId) return;
      _sentCompanion = key;
      // A newer selection may have arrived while the request was in flight.
    }
  }

  Future<Map<String, dynamic>> createPairing() async {
    if (!signedIn) {
      throw const RelayException('Sign in on your phone first.', 401);
    }
    return relay.request('/pairing', token: _token, body: {});
  }

  Future<void> disconnect(String id) async {
    await relay.request('/unpair', token: _token, body: {'device_id': id});
    _sentCompanion = null;
    await recordActivity('Computer unpaired', 'Connection revoked', 'devices');
    await refreshDevices();
  }
}
