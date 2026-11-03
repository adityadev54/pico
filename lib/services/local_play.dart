/// Phone-local play: games, riddles, timers and reminders. No computer needed.
class Riddle {
  const Riddle(this.question, this.answers);
  final String question;
  final List<String> answers;
}

const riddles = [
  Riddle('What has keys but can’t open a single lock?', [
    'piano',
    'keyboard',
    'typewriter',
  ]),
  Riddle('What runs but never walks?', ['water', 'river', 'tap']),
  Riddle('What has a face and hands but no arms or legs?', ['clock', 'watch']),
  Riddle('The more you take, the more you leave behind. What am I?', [
    'footsteps',
    'steps',
  ]),
  Riddle('What gets wetter the more it dries?', ['towel']),
  Riddle('What has one eye but can’t see?', ['needle', 'hurricane']),
  Riddle('What can you catch but never throw?', ['cold']),
  Riddle('What goes up but never comes down?', ['age']),
];

String _normalizeAnswer(String text) => text
    .toLowerCase()
    .replaceAll(RegExp(r'[^a-z ]'), ' ')
    .replaceAll(RegExp(r'\s+'), ' ')
    .trim()
    .replaceFirst(RegExp(r'^(a|an|the) '), '');

bool riddleAnswerMatches(String attempt, List<String> answers) {
  final got = _normalizeAnswer(attempt);
  return got.isNotEmpty && answers.map(_normalizeAnswer).contains(got);
}

/// Parses "30 seconds", "5 minutes", "2 hrs". Null when unusable.
Duration? parseDuration(String text) {
  final match = RegExp(
    r'^\s*(\d+)\s*(seconds?|secs?|s|minutes?|mins?|m|hours?|hrs?|h)\s*$',
    caseSensitive: false,
  ).firstMatch(text);
  if (match == null) return null;
  final value = int.tryParse(match.group(1)!);
  if (value == null || value <= 0 || value > 86400) return null;
  switch (match.group(2)!.toLowerCase()) {
    case 's':
    case 'sec':
    case 'secs':
    case 'second':
    case 'seconds':
      return Duration(seconds: value);
    case 'm':
    case 'min':
    case 'mins':
    case 'minute':
    case 'minutes':
      return Duration(minutes: value);
    default:
      return Duration(hours: value);
  }
}

/// A local command Pico runs on the phone itself.
class LocalCommand {
  const LocalCommand(this.kind, [this.args = const {}]);
  final String kind;
  final Map<String, dynamic> args;
}

LocalCommand? parseLocalPlay(String speech) {
  final text = speech.trim().replaceAll(RegExp(r'[.!?]+$'), '');
  if (RegExp(
    r"^(play( a game| a guessing game| guessing game)?|guessing game|guess( a)? number|let's play( a game)?|lets play( a game)?)$",
    caseSensitive: false,
  ).hasMatch(text)) {
    return const LocalCommand('play_guess');
  }
  if (RegExp(
    r'^(tell me |give me |ask me )?(a |another )?(riddle|puzzle)s?$',
    caseSensitive: false,
  ).hasMatch(text)) {
    return const LocalCommand('ask_riddle');
  }
  var match = RegExp(
    r'^(?:set |start )?(?:a )?timer (?:for )?(\d+)\s*(seconds?|secs?|s|minutes?|mins?|m|hours?|hrs?|h)$',
    caseSensitive: false,
  ).firstMatch(text);
  match ??= RegExp(
    r'^(?:set |start )?a (\d+)\s*(seconds?|secs?|s|minutes?|mins?|m|hours?|hrs?|h) timer$',
    caseSensitive: false,
  ).firstMatch(text);
  if (match != null) {
    final duration = parseDuration('${match.group(1)} ${match.group(2)}');
    if (duration != null) {
      return LocalCommand('set_timer', {'seconds': duration.inSeconds});
    }
  }
  if (RegExp(
    r'^(check timer|timer status|how much time( is left| left)?|time left)$',
    caseSensitive: false,
  ).hasMatch(text)) {
    return const LocalCommand('timer_status');
  }
  if (RegExp(r'^cancel timer$', caseSensitive: false).hasMatch(text)) {
    return const LocalCommand('cancel_timer');
  }
  match = RegExp(
    r'^remind me in (\d+)\s*(seconds?|secs?|s|minutes?|mins?|m|hours?|hrs?|h) to (.+)$',
    caseSensitive: false,
  ).firstMatch(text);
  if (match != null) {
    final duration = parseDuration('${match.group(1)} ${match.group(2)}');
    final what = match.group(3)!.trim();
    if (duration != null && what.isNotEmpty) {
      return LocalCommand('set_reminder', {
        'seconds': duration.inSeconds,
        'text': what,
      });
    }
  }
  match = RegExp(r'^remind me to (.+)$', caseSensitive: false).firstMatch(text);
  if (match != null && match.group(1)!.trim().isNotEmpty) {
    return LocalCommand('ask_reminder_time', {'text': match.group(1)!.trim()});
  }
  if (RegExp(
    r'^(my |list )?reminders?$',
    caseSensitive: false,
  ).hasMatch(text)) {
    return const LocalCommand('list_reminders');
  }
  if (RegExp(
    r'^cancel (my |all )?reminders?$',
    caseSensitive: false,
  ).hasMatch(text)) {
    return const LocalCommand('cancel_reminders');
  }
  return null;
}

/// Backs out of whatever Pico was waiting on (game, riddle, question).
bool isLocalStop(String speech) {
  final text = speech.trim().replaceAll(RegExp(r'[.!?]+$'), '');
  return RegExp(
    r'^(stop|cancel|quit|never ?mind|give up)$',
    caseSensitive: false,
  ).hasMatch(text);
}
