import 'package:flutter/foundation.dart';

abstract final class Config {
  static const supabaseUrl = String.fromEnvironment(
    'SUPABASE_URL',
    defaultValue: 'https://melngaeuytjuvfolwabd.supabase.co',
  );
  static const supabaseKey = String.fromEnvironment(
    'SUPABASE_PUBLISHABLE_KEY',
    defaultValue: 'sb_publishable_lYtMmd7druDEUlcu5BQpiQ_5SvWb60R',
  );
  static const authRedirect = String.fromEnvironment(
    'AUTH_REDIRECT',
    defaultValue: 'pico://auth/callback',
  );
  static const relayUrl = String.fromEnvironment('RELAY_URL');
  static const setupUrl = String.fromEnvironment('SETUP_URL');
  static String get relayBase => relayUrl.isNotEmpty
      ? relayUrl
      // Production PWA is served by the relay itself, so same-origin is
      // right there. A local `flutter run` dev server has no API routes,
      // so debug builds use the production relay like native does.
      : kIsWeb && !kDebugMode && Uri.base.host.isNotEmpty
      ? Uri.base.origin
      : 'https://pico-companion.fly.dev';
  static String get downloadUrl =>
      setupUrl.isNotEmpty ? setupUrl : '$relayBase/setup';
  static bool get hasAccount =>
      supabaseUrl.isNotEmpty && supabaseKey.isNotEmpty;
}
