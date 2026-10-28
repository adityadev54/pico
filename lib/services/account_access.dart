import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'config.dart';

/// Honors the user's session persistence choice on every token refresh.
class RememberedSessionStorage extends LocalStorage {
  const RememberedSessionStorage(this.preferences);
  final SharedPreferences preferences;
  static const sessionKey = 'pico.auth.session';
  @override
  Future<void> initialize() async {}
  @override
  Future<bool> hasAccessToken() async => (await accessToken()) != null;
  @override
  Future<String?> accessToken() async =>
      preferences.getBool('remember_me') == false
      ? null
      : preferences.getString(sessionKey);
  @override
  Future<void> removePersistedSession() async {
    await preferences.remove(sessionKey);
  }

  @override
  Future<void> persistSession(String value) async {
    if (preferences.getBool('remember_me') == false) {
      await removePersistedSession();
    } else {
      await preferences.setString(sessionKey, value);
    }
  }
}

Future<Map<String, bool>> loadAuthProviders() async {
  if (!Config.hasAccount) return {};
  try {
    final response = await http
        .get(
          Uri.parse('${Config.supabaseUrl}/auth/v1/settings'),
          headers: {'apikey': Config.supabaseKey},
        )
        .timeout(const Duration(seconds: 10));
    if (response.statusCode != 200) return {};
    final external = jsonDecode(response.body)['external'] as Map;
    return {
      'google': external['google'] == true,
      'apple': external['apple'] == true,
    };
  } catch (_) {
    return {};
  }
}
