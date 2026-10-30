import 'place.dart';

class ChatEntry {
  ChatEntry.message(Place value)
    : place = value,
      task = null,
      created = value.created;
  ChatEntry.reply(Map<String, dynamic> value)
    : task = value,
      place = null,
      created =
          DateTime.tryParse(value['created_at'] as String? ?? '') ??
          DateTime.fromMillisecondsSinceEpoch(0);
  final Place? place;
  final Map<String, dynamic>? task;
  final DateTime created;
}
