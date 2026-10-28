import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'services/config.dart';
import 'screens/desktop_screen.dart';
import 'services/account_access.dart';
import 'screens/password_reset_screen.dart';
import 'services/pico_store.dart';
import 'screens/home_screen.dart';
import 'screens/account_screen.dart';
import 'theme/app_theme.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  LicenseRegistry.addLicense(() async* {
    yield LicenseEntryWithLineBreaks([
      'DM Sans',
    ], await rootBundle.loadString('assets/fonts/OFL.txt'));
  });
  final preferences = await SharedPreferences.getInstance();
  final desktop =
      !kIsWeb &&
      (defaultTargetPlatform == TargetPlatform.macOS ||
          defaultTargetPlatform == TargetPlatform.windows);
  if (Config.hasAccount && !desktop) {
    await Supabase.initialize(
      url: Config.supabaseUrl,
      publishableKey: Config.supabaseKey,
      authOptions: FlutterAuthClientOptions(
        localStorage: RememberedSessionStorage(preferences),
      ),
    );
  }
  final store = PicoStore(
    preferences,
    accountClient: Config.hasAccount && !desktop
        ? Supabase.instance.client
        : null,
  );
  await store.load();
  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      statusBarIconBrightness: Brightness.dark,
      statusBarBrightness: Brightness.light,
    ),
  );
  runApp(PicoApp(store: store));
}

class PicoApp extends StatelessWidget {
  const PicoApp({super.key, required this.store});
  final PicoStore store;
  @override
  Widget build(BuildContext context) => ListenableBuilder(
    listenable: store,
    builder: (context, _) => MaterialApp(
      title: 'Pico',
      debugShowCheckedModeBanner: false,
      theme: PicoTheme.light,
      darkTheme: PicoTheme.dark,
      themeMode: store.themeMode,
      builder: (context, child) => AnnotatedRegion<SystemUiOverlayStyle>(
        value: Theme.of(context).brightness == Brightness.dark
            ? SystemUiOverlayStyle.light
            : SystemUiOverlayStyle.dark,
        child: child!,
      ),
      home: ListenableBuilder(
        listenable: store,
        builder: (context, _) =>
            !kIsWeb &&
                (defaultTargetPlatform == TargetPlatform.macOS ||
                    defaultTargetPlatform == TargetPlatform.windows)
            ? DesktopScreen(store: store)
            : store.recoveringPassword
            ? PasswordResetScreen(store: store, recovery: true)
            : Config.hasAccount && !store.signedIn
            ? AccountScreen(store: store, firstRun: true)
            : HomeScreen(store: store),
      ),
    ),
  );
}
