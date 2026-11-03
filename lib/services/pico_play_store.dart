part of 'pico_store.dart';

/// Phone-local play: games, riddles, timers and reminders.
extension PicoPlayStore on PicoStore {
  /// Local games/timers never queue a Place on the computer or call Muse.
  Future<bool> handleLocalPlay(String value) async {
    final command = parseLocalPlay(value);
    String? reply;
    if (command == null) {
      if (pendingPrompt == null ||
          _playChatId != current?.id ||
          parseComputerCommand(value) != null ||
          looksLikeCommand(value)) {
        return false;
      }
      if (isLocalStop(value)) {
        reply =
            pendingPrompt!['kind'] == 'riddle' &&
                value.trim().toLowerCase() == 'give up'
            ? giveUpRiddle()
            : cancelPendingPrompt();
      } else {
        reply = switch (pendingPrompt!['kind']) {
          'guess' => guessTurn(value),
          'riddle' => riddleTurn(value),
          'reminder_time' => reminderTimeTurn(value),
          _ => null,
        };
      }
      if (reply == null) return false;
    }
    final owner = userId;
    final chat = await ensureChat(value);
    if (owner != userId) return true;
    _playChatId = chat.id;
    _playOwner = owner;
    places.insert(
      0,
      Place(
        id: _uuid(),
        sentence: value,
        created: DateTime.now(),
        chatId: chat.id,
        delivery: 'request',
      ),
    );
    reply ??= runLocalCommand(command!);
    await saveAssistantReply(reply, chatId: chat.id);
    error = null;
    if (busy ||
        routineRequest != null ||
        tasks.any(
          (t) => [
            'queued',
            'working',
            'verifying',
            'awaiting_approval',
          ].contains(t['status']),
        )) {
      resumeFlowMood();
    } else {
      previewMood(pendingPrompt == null ? 'happy' : 'curious');
    }
    return true;
  }

  Future<void> saveAssistantReply(
    String text, {
    bool force = false,
    String? chatId,
  }) async {
    final target = chatId ?? _playChatId;
    if (_playOwner != userId ||
        target == null ||
        !sessions.any((s) => s.id == target) ||
        _deletedChats.contains(target)) {
      return;
    }
    places.insert(
      0,
      Place(
        id: _uuid(),
        sentence: text,
        created: DateTime.now(),
        chatId: target,
        role: 'assistant',
        delivery: 'local',
      ),
    );
    await _persist();
    _changed();
  }

  void clearLocalPlay() {
    pendingPrompt = null;
    _playChatId = null;
    _playOwner = null;
    playTimer?.cancel();
    playTimer = null;
    timerEndsAt = null;
    for (final timer in _reminderTimers.values) {
      timer.cancel();
    }
    _reminderTimers.clear();
    _reminderChatIds.clear();
    reminders.clear();
  }

  String _describeDuration(Duration duration) {
    final seconds = duration.inSeconds;
    if (seconds < 60) return '$seconds second${seconds == 1 ? '' : 's'}';
    if (seconds < 3600) {
      final minutes = (seconds + 59) ~/ 60;
      return '$minutes minute${minutes == 1 ? '' : 's'}';
    }
    final hours = (seconds + 3599) ~/ 3600;
    return '$hours hour${hours == 1 ? '' : 's'}';
  }

  String runLocalCommand(LocalCommand command) {
    switch (command.kind) {
      case 'play_guess':
        return startGuessingGame();
      case 'ask_riddle':
        return startRiddle();
      case 'set_timer':
        return startTimer(Duration(seconds: command.args['seconds'] as int));
      case 'timer_status':
        return timerStatus();
      case 'cancel_timer':
        return cancelTimer();
      case 'set_reminder':
        return addReminder(
          Duration(seconds: command.args['seconds'] as int),
          command.args['text'] as String,
        );
      case 'ask_reminder_time':
        pendingPrompt = {
          'kind': 'reminder_time',
          'text': command.args['text'] as String,
        };
        return 'Sure — in how many minutes? (say like “10 minutes” or “2 hours”)';
      case 'list_reminders':
        return listReminders();
      case 'cancel_reminders':
        return cancelReminders();
      default:
        return 'I don’t know that one yet.';
    }
  }

  String startGuessingGame() {
    pendingPrompt = {
      'kind': 'guess',
      'target': Random().nextInt(20) + 1,
      'tries': 0,
    };
    return "I'm thinking of a number from 1 to 20. What's your guess?";
  }

  String guessTurn(String speech) {
    final prompt = pendingPrompt!;
    final guess = int.tryParse(speech.trim());
    if (guess == null || guess < 1 || guess > 20) {
      return 'Give me a number from 1 to 20.';
    }
    final tries = (prompt['tries'] as int) + 1;
    prompt['tries'] = tries;
    final target = prompt['target'] as int;
    if (guess == target) {
      pendingPrompt = null;
      return 'You got it in $tries ${tries == 1 ? 'try' : 'tries'}!! Say “play” for another round.';
    }
    return '${guess < target ? 'Too low' : 'Too high'} — try again! (tries: $tries)';
  }

  String startRiddle() {
    pendingPrompt = {
      'kind': 'riddle',
      'riddle': Random().nextInt(riddles.length),
      'tries': 0,
    };
    return 'Riddle: ${riddles[pendingPrompt!['riddle'] as int].question}';
  }

  String riddleTurn(String speech) {
    final prompt = pendingPrompt!;
    final riddle = riddles[prompt['riddle'] as int];
    if (riddleAnswerMatches(speech, riddle.answers)) {
      pendingPrompt = null;
      return 'Brilliant!! That’s right. Say “riddle” for another one.';
    }
    prompt['tries'] = (prompt['tries'] as int) + 1;
    return 'Not quite — try again! (or say “give up”)';
  }

  String giveUpRiddle() {
    final riddle = riddles[pendingPrompt!['riddle'] as int];
    pendingPrompt = null;
    return 'The answer was “${riddle.answers.first}”. Say “riddle” for another one.';
  }

  String cancelPendingPrompt() {
    pendingPrompt = null;
    return 'Okay, stopped. Say “play” or “riddle” anytime.';
  }

  String reminderTimeTurn(String speech) {
    var text = speech.trim();
    text = text.replaceFirst(RegExp(r'^in\s+', caseSensitive: false), '');
    final duration = parseDuration(text);
    if (duration == null) {
      return 'Tell me like “10 minutes” or “2 hours”.';
    }
    final what = pendingPrompt!['text'] as String;
    pendingPrompt = null;
    return addReminder(duration, what);
  }

  String startTimer(Duration duration) {
    playTimer?.cancel();
    timerEndsAt = DateTime.now().add(duration);
    timerLabel = _describeDuration(duration);
    _timerChatId = _playChatId;
    playTimer = Timer(duration, _fireTimer);
    return 'Timer set for $timerLabel. I’ll announce it here while Pico is open.';
  }

  String timerStatus() {
    final ends = timerEndsAt;
    if (playTimer == null || !playTimer!.isActive || ends == null) {
      return 'No timer is running. Say “set a timer for 5 minutes”.';
    }
    return '${_describeDuration(ends.difference(DateTime.now()))} left on your timer.';
  }

  void _fireTimer() {
    final label = timerLabel ?? 'timer';
    playTimer = null;
    timerEndsAt = null;
    timerLabel = null;
    unawaited(
      saveAssistantReply(
        "Time's up! Your $label finished.",
        force: true,
        chatId: _timerChatId,
      ),
    );
  }

  String cancelTimer() {
    if (playTimer == null || !playTimer!.isActive) {
      return 'No timer is running.';
    }
    playTimer?.cancel();
    playTimer = null;
    timerEndsAt = null;
    timerLabel = null;
    return 'Timer cancelled.';
  }

  String addReminder(Duration duration, String text) {
    final id = _uuid();
    reminders.add({
      'id': id,
      'text': text,
      'firesAt': DateTime.now().add(duration).toIso8601String(),
    });
    _reminderChatIds[id] = _playChatId;
    _reminderTimers[id] = Timer(duration, () => _fireReminder(id));
    _changed();
    return 'I’ll remind you here to $text in ${_describeDuration(duration)} while Pico is open.';
  }

  void _fireReminder(String id) {
    final index = reminders.indexWhere((item) => item['id'] == id);
    if (index < 0) return;
    final text = reminders.removeAt(index)['text'] as String;
    _reminderTimers.remove(id);
    final chat = _reminderChatIds.remove(id);
    _changed();
    unawaited(
      saveAssistantReply('Reminder: $text.', force: true, chatId: chat),
    );
  }

  String listReminders() {
    if (reminders.isEmpty) return 'You have no reminders.';
    final lines = reminders.map((item) {
      final firesAt = DateTime.parse(item['firesAt'] as String);
      final left = firesAt.difference(DateTime.now());
      return '• ${item['text']} (in ${_describeDuration(left.isNegative ? Duration.zero : left)})';
    });
    return 'Reminders:\n${lines.join('\n')}';
  }

  String cancelReminders() {
    if (reminders.isEmpty) return 'You have no reminders.';
    for (final timer in _reminderTimers.values) {
      timer.cancel();
    }
    _reminderTimers.clear();
    _reminderChatIds.clear();
    reminders.clear();
    _changed();
    return 'All reminders cleared.';
  }
}
