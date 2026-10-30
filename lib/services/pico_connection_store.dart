part of 'pico_store.dart';

extension PicoConnectionStore on PicoStore {
  Future<void> _deliverPlaces() async {
    if (_token == null || devices.isEmpty) return;
    final owner = userId;
    final token = _token;
    final target = devices.first['id'] as String;
    for (final place in List<Place>.of(
      places.where(
        (p) =>
            !p.finished &&
            p.role == 'user' &&
            (p.delivery == 'local' ||
                (p.delivery == 'queued' && p.deliveryDeviceId != target)),
      ),
    )) {
      try {
        final result = await relay.request(
          '/mail',
          token: token,
          body: {
            'device_id': target,
            'id': place.id,
            'kind': 'place',
            'payload': {'place_id': place.id, 'sentence': place.sentence},
          },
        );
        if (owner != userId || !devices.any((d) => d['id'] == target)) return;
        final i = places.indexWhere((p) => p.id == place.id);
        if (i >= 0) {
          places[i] = places[i].copyWith(
            delivery: result['status'] as String,
            mailId: result['id'] as String,
            deliveryDeviceId: target,
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

  Future<void> _flushPlaceUpdates() async {
    if (_token == null || devices.isEmpty) return;
    final owner = userId;
    final token = _token;
    for (final message in List<Map<String, dynamic>>.of(_placeUpdates)) {
      if (!devices.any((d) => d['id'] == message['device_id'])) {
        _placeUpdates.remove(message);
        await _persist();
        continue;
      }
      await relay.request('/mail', token: token, body: message);
      if (owner != userId) return;
      _placeUpdates.remove(message);
      await _persist();
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
      if (approvedAppsDeviceId != null &&
          (devices.isEmpty || approvedAppsDeviceId != devices.first['id'])) {
        _clearAppAccess();
      }
      await refreshMuseStatus();
      await syncCompanion();
      await _deliverPlaces();
      await _flushPlaceUpdates();
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
        if (owner != userId) return;
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
      final acknowledgements = <Map<String, dynamic>>[];
      for (final raw in incoming['mail'] as List) {
        final message = Map<String, dynamic>.from(raw);
        final data = Map<String, dynamic>.from(message['payload']);
        _receiveAppMessage(message);
        if (message['kind'] == 'idle') {
          pendingPlaceId = data['place_id'] as String?;
        }
        if (message['kind'] == 'parked') {
          final i = places.indexWhere((p) => p.id == data['place_id']);
          if (i >= 0) {
            final status = places[i].finished
                ? 'finished'
                : data['status'] as String? ?? 'parked';
            places[i] = places[i].copyWith(
              parked: status == 'parked',
              finished: status == 'finished',
            );
          }
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
        acknowledgements.add({
          'device_id': message['device_id'],
          'ids': [message['id']],
        });
      }
      if (tasksChanged) await refreshTasks();
      await _persist();
      if (owner != userId) return;
      for (final acknowledgement in acknowledgements) {
        await relay.request('/phone/ack', token: token, body: acknowledgement);
        if (owner != userId) return;
      }
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
    _clearAppAccess();
    await recordActivity('Computer unpaired', 'Connection revoked', 'devices');
    await refreshDevices();
  }
}
