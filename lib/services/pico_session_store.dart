part of 'pico_store.dart';

extension PicoSessionStore on PicoStore {
  String get _chatStateKey => 'pico.chat_state.${userId ?? 'local'}';
  String get _chatsKey => 'pico.chats.${userId ?? 'local'}';
  String get _activeChatKey => 'pico.active_chat.${userId ?? 'local'}';
  String get _draftChatKey => 'pico.draft_chat.${userId ?? 'local'}';
  String get _deletedChatsKey => 'pico.deleted_chats.${userId ?? 'local'}';

  void loadChats() {
    sessions.clear();
    Map<String, dynamic> saved = {};
    try {
      saved = Map<String, dynamic>.from(
        jsonDecode(preferences.getString(_chatStateKey) ?? '{}'),
      );
    } catch (_) {
      /* Recover legacy state below. */
    }
    _deletedChats
      ..clear()
      ..addAll(
        (saved['deleted'] as List?)?.cast<String>() ??
            preferences.getStringList(_deletedChatsKey) ??
            [],
      );
    try {
      sessions.addAll(
        ((saved['sessions'] as List?) ??
                jsonDecode(preferences.getString(_chatsKey) ?? '[]') as List)
            .map((v) => Session.fromJson(Map<String, dynamic>.from(v))),
      );
    } catch (_) {
      /* Recover legacy messages below. */
    }
    // Older builds used each unscoped message as a drawer row. Preserve the
    // messages together instead of presenting them as separate conversations.
    final legacy =
        places
            .where((p) => p.chatId == null && !_deletedChats.contains(p.id))
            .toList()
          ..sort((a, b) => a.created.compareTo(b.created));
    if (legacy.isNotEmpty) {
      final ids = legacy.map((p) => p.id).toSet();
      final chat = Session(
        id: legacy.first.id,
        title: legacy.first.sentence,
        created: legacy.first.created,
      );
      sessions.removeWhere((s) => ids.contains(s.id));
      sessions.add(chat);
      for (var i = 0; i < places.length; i++) {
        if (ids.contains(places[i].id)) {
          places[i] = places[i].copyWith(chatId: chat.id);
        }
      }
      unawaited(_persist().catchError((_) {}));
    }
    for (final place in places) {
      final id = place.chatId ?? place.id;
      if (!_deletedChats.contains(id) && !sessions.any((s) => s.id == id)) {
        sessions.add(
          Session(id: id, title: place.sentence, created: place.created),
        );
      }
    }
    sessions.removeWhere((s) => _deletedChats.contains(s.id));
    if (saved.isEmpty) sessions.sort((a, b) => b.created.compareTo(a.created));
    composingNewChat =
        saved['draft'] as bool? ?? preferences.getBool(_draftChatKey) ?? false;
    final active =
        saved['active'] as String? ?? preferences.getString(_activeChatKey);
    current = composingNewChat
        ? null
        : sessions.where((s) => s.id == active).firstOrNull ??
              sessions.firstOrNull;
    if (legacy.isNotEmpty) unawaited(persistChats().catchError((_) {}));
  }

  Future<void> persistChats() async {
    // One account-scoped snapshot keeps selection and membership together.
    final key = _chatStateKey;
    final snapshot = jsonEncode({
      'sessions': sessions.map((s) => s.toJson()).toList(),
      'active': current?.id,
      'draft': composingNewChat,
      'deleted': _deletedChats.toList(),
    });
    await preferences.setString(key, snapshot);
  }

  Future<Session> ensureChat(String title) async {
    if (current != null) {
      final chat = current!;
      sessions.removeWhere((s) => s.id == chat.id);
      sessions.insert(0, chat);
      await persistChats();
      return chat;
    }
    final chat = Session(
      id: _uuid(),
      title: title.trim(),
      created: DateTime.now(),
    );
    sessions.insert(0, chat);
    current = chat;
    composingNewChat = false;
    await persistChats();
    return chat;
  }

  String requestTitle(String kind, Map<String, dynamic> input) =>
      switch (kind) {
        'create_note' => 'Create ${input['name'] ?? 'a file'}',
        'read_document' ||
        'read_file' => 'Read ${input['path'] ?? 'selected file'}',
        'send_file' => 'Send selected file',
        _ =>
          '${kind.replaceAll('_', ' ')} ${input['query'] ?? input['app'] ?? ''}'
              .trim(),
      };

  Future<Session> rememberRequest(String text) async {
    final owner = userId;
    final chat = await ensureChat(text);
    if (owner != userId) {
      throw StateError('Account changed. Send this request again.');
    }
    places.insert(
      0,
      Place(
        id: _uuid(),
        sentence: text,
        created: DateTime.now(),
        chatId: chat.id,
        delivery: 'request',
      ),
    );
    await _persist();
    _changed();
    return chat;
  }

  Future<void> rememberReply(String text, String chat) async {
    places.insert(
      0,
      Place(
        id: _uuid(),
        sentence: text,
        created: DateTime.now(),
        chatId: chat,
        delivery: 'reply',
        role: 'assistant',
      ),
    );
    await _persist();
    _changed();
  }

  Future<void> importTaskChats(List<Map<String, dynamic>> rows) async {
    for (final task in rows.reversed) {
      final id = task['session_id'] as String?;
      if (id == null ||
          _deletedChats.contains(id) ||
          sessions.any((s) => s.id == id)) {
        continue;
      }
      final input = Map<String, dynamic>.from(task['input'] ?? {});
      sessions.insert(
        0,
        Session(
          id: id,
          title: requestTitle(task['kind'] as String, input),
          created:
              DateTime.tryParse(task['created_at'] as String? ?? '') ??
              DateTime.now(),
        ),
      );
    }
    if (current == null && !composingNewChat) current = sessions.firstOrNull;
    await persistChats();
  }

  Future<void> deleteSession(Session chat) async {
    _deletedChats.add(chat.id);
    final ids = places
        .where((p) => (p.chatId ?? p.id) == chat.id)
        .map((p) => p.id)
        .toSet();
    places.removeWhere((p) => ids.contains(p.id));
    activities.removeWhere((a) => ids.any((id) => a.target == 'place:$id'));
    sessions.removeWhere((s) => s.id == chat.id);
    if (current?.id == chat.id) newSession();
    await _persist();
    await _persistActivities();
    await persistChats();
    _changed();
  }
}
