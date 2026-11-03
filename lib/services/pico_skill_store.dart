part of 'pico_store.dart';

extension PicoSkillStore on PicoStore {
  void showRoutines() {
    routinesVisible = true;
    _changed();
    unawaited(requestRoutines());
  }

  bool reviewRoutineRequest(String words) {
    String normal(String text) => text
        .toLowerCase()
        .replaceAll(RegExp(r'[?!.,”“…,]'), '')
        .replaceAll(
          RegExp(r'\b(can you|could you|please|for me|again|run|do)\b'),
          '',
        )
        .replaceAll(RegExp(r'\s+'), ' ')
        .trim();
    final matches = routines
        .where((r) => normal(r['name'] as String) == normal(words))
        .toList();
    if (matches.length != 1) return false;
    routineReviewId = matches.single['id'] as String;
    routinesVisible = true;
    _changed();
    return true;
  }

  void hideRoutines() {
    routinesVisible = false;
    _changed();
  }

  void _appendRoutineReply(String text) {
    final chat = _routineChatId;
    if (chat == null) return;
    if (!sessions.any((s) => s.id == chat) || _deletedChats.contains(chat)) {
      _routineChatId = null;
      return;
    }
    places.insert(
      0,
      Place(
        id: _uuid(),
        sentence: text,
        created: DateTime.now(),
        chatId: chat,
        role: 'assistant',
        delivery: 'local',
      ),
    );
    _routineChatId = null;
  }

  void previewMood(String value) {
    _moodTimer?.cancel();
    setMood(value);
    _moodTimer?.cancel();
    const activity = {
      'angry': 'stuck',
      'curious': 'thinking',
      'happy': 'done',
      'sleepy': 'idle',
      'surprised': 'needsYou',
    };
    _moodTimer = Timer(const Duration(milliseconds: 1200), () {
      setMood(activity[value] ?? value);
      _moodTimer?.cancel();
      _moodTimer = Timer(const Duration(seconds: 3), resumeFlowMood);
    });
  }

  Future<void> requestRoutines({
    String? routine,
    bool teach = false,
    bool quiet = false,
  }) async {
    if (!signedIn || devices.isEmpty) return;
    if (routineRequest != null) return;
    final device = devices.first;
    if (!isOnline(device)) {
      routineMessage = 'Your computer is offline. Nothing was queued.';
      _changed();
      return;
    }
    final owner = userId;
    final id = _uuid();
    routineRequest = id;
    _routineQuiet = quiet;
    if (!quiet) setMood(routine == null ? 'thinking' : 'working');
    routineMessage = routine == null
        ? 'Asking your computer…'
        : 'Preparing your result…';
    _changed();
    try {
      if (routine != null) {
        final name =
            routines.where((r) => r['id'] == routine).firstOrNull?['name']
                as String? ??
            'Run my routine';
        final chat = await ensureChat(name);
        if (owner != userId) return;
        _routineChatId = chat.id;
        places.insert(
          0,
          Place(
            id: id,
            sentence: name,
            created: DateTime.now(),
            chatId: chat.id,
            delivery: 'request',
          ),
        );
        await _persist();
      }
      await relay.request(
        '/mail',
        token: _token,
        body: {
          'device_id': device['id'],
          'id': id,
          'kind': 'skill_request',
          'payload': {
            'query': teach
                ? 'teach'
                : routine == null
                ? 'catalog'
                : 'run:$routine',
            'request_id': id,
            'expires_at': DateTime.now()
                .add(const Duration(seconds: 60))
                .millisecondsSinceEpoch
                .toString(),
          },
        },
      );
      if (owner != userId) return;
      _routineTimer?.cancel();
      if (routineRequest == id) {
        _routineTimer = Timer(const Duration(seconds: 65), () {
          if (routineRequest != id) return;
          routineRequest = null;
          routineMessage = 'No result received. Check your computer before retrying; an accepted run may still finish.';
          _appendRoutineReply(routineMessage!);
          unawaited(_persist());
          if (!quiet) previewMood('stuck');
          _changed();
        });
      }
      await refreshDevices();
    } catch (e) {
      if (owner != userId) return;
      routineRequest = null;
      routineMessage = 'Couldn’t reach your computer. No automatic retry.';
      if (!quiet) previewMood('stuck');
      _appendRoutineReply(routineMessage!);
      await _persist();
      _changed();
    }
  }

  void _receiveRoutine(Map<String, dynamic> message) {
    if (message['kind'] != 'skill_result' ||
        devices.isEmpty ||
        message['device_id'] != devices.first['id']) {
      return;
    }
    final data = Map<String, dynamic>.from(message['payload']);
    if (data['request_id'] != routineRequest) return;
    try {
      final rows = jsonDecode(data['catalog'] as String) as List;
      routines
        ..clear()
        ..addAll(rows.map((e) => Map<String, dynamic>.from(e)));
      routineMessage = (data['message'] as String).isEmpty
          ? null
          : data['message'] as String;
      if (data['status'] == 'completed' || data['status'] == 'failed') {
        _appendRoutineReply(
          routineMessage ?? 'Your computer returned no result.',
        );
      }
      routineRequest = null;
      _routineTimer?.cancel();
      if (!_routineQuiet) {
        previewMood(
          data['status'] == 'completed'
              ? 'happy'
              : data['status'] == 'failed'
              ? 'angry'
              : 'idle',
        );
      }
    } catch (_) {
      routineMessage = 'Couldn’t read the routine list. Check your computer.';
      routineRequest = null;
    }
  }
}
