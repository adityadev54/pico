import 'package:supabase_flutter/supabase_flutter.dart';

/// Reuses durable handoffs so installed helpers also receive picker changes.
class CharacterSync {
  CharacterSync(this.client);
  final SupabaseClient client;
  bool _running = false;

  Future<void> sync({
    required String user,
    required String character,
    required List<Map<String, dynamic>> devices,
  }) async {
    if (_running) return;
    if (!['tuck', 'mica'].contains(character)) return;
    _running = true;
    try {
      for (final device in devices) {
        final latest = await client
            .from('handoffs')
            .select('character')
            .eq('device_id', device['id'])
            .order('created_at', ascending: false)
            .limit(1);
        if (latest.isNotEmpty && latest.first['character'] == character) {
          continue;
        }
        await client.from('handoffs').insert({
          'user_id': user,
          'device_id': device['id'],
          'character': character,
        });
      }
    } finally {
      _running = false;
    }
  }
}
