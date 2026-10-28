import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:pico/screens/account_screen.dart';
import 'package:pico/services/pico_store.dart';
import 'package:pico/theme/app_theme.dart';
import 'package:pico/services/account_access.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUpAll(() async {
    final loader = FontLoader('DM Sans')
      ..addFont(rootBundle.load('assets/fonts/DMSans.ttf'));
    await loader.load();
    final icons = FontLoader('MaterialIcons')
      ..addFont(rootBundle.load('fonts/MaterialIcons-Regular.otf'));
    await icons.load();
  });
  Future<void> mount(WidgetTester tester) async {
    SharedPreferences.setMockInitialValues({});
    final store = PicoStore(await SharedPreferences.getInstance());
    addTearDown(store.dispose);
    await tester.pumpWidget(
      RepaintBoundary(
        key: const ValueKey('auth-preview'),
        child: MaterialApp(
          debugShowCheckedModeBanner: false,
          theme: PicoTheme.light,
          home: AccountScreen(store: store, firstRun: true),
        ),
      ),
    );
    await tester.pump();
  }

  test('Remember me controls session persistence', () async {
    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();
    final storage = RememberedSessionStorage(prefs);
    await storage.persistSession('session');
    expect(await storage.hasAccessToken(), true);
    await prefs.setBool('remember_me', false);
    await storage.persistSession('refreshed');
    expect(await storage.accessToken(), isNull);
    expect(prefs.getString(RememberedSessionStorage.sessionKey), isNull);
  });
  testWidgets(
    'Auth validates, remembers, switches mode and opens password recovery',
    (tester) async {
      await mount(tester);
      expect(find.text('Google'), findsNothing);
      expect(find.text('Apple'), findsNothing);
      expect(find.text('or continue with'), findsNothing);
      expect(find.byType(Image), findsNothing);
      expect(find.text('Enter a valid email'), findsNothing);
      await tester.ensureVisible(find.widgetWithText(FilledButton, 'Sign in'));
      await tester.tap(find.widgetWithText(FilledButton, 'Sign in'));
      await tester.pump();
      expect(find.text('Enter a valid email'), findsOneWidget);
      await tester.enterText(
        find.byKey(const ValueKey('account-email')),
        'hello@example.com',
      );
      await tester.enterText(
        find.byKey(const ValueKey('account-password')),
        'my-password',
      );
      await tester.ensureVisible(find.byTooltip('Show password'));
      await tester.tap(find.byTooltip('Show password'));
      await tester.pump();
      expect(find.byTooltip('Hide password'), findsOneWidget);
      await tester.ensureVisible(find.text('Remember me'));
      await tester.tap(find.text('Remember me'));
      await tester.pump();
      expect(
        (await SharedPreferences.getInstance()).getBool('remember_me'),
        false,
      );
      await tester.tap(find.text('Forgot password?'));
      await tester.pumpAndSettle();
      expect(find.text('Reset password'), findsOneWidget);
      expect(
        find.widgetWithText(FilledButton, 'Send reset link'),
        findsOneWidget,
      );
      await tester.pageBack();
      await tester.pumpAndSettle();
      await tester.ensureVisible(find.text('Create an account'));
      await tester.tap(find.text('Create an account'));
      await tester.pump();
      expect(
        find.widgetWithText(FilledButton, 'Create account'),
        findsOneWidget,
      );
    },
  );
  testWidgets('Auth fits phone, keyboard, landscape and larger type', (
    tester,
  ) async {
    tester.view.devicePixelRatio = 1;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetViewInsets();
      tester.platformDispatcher.clearTextScaleFactorTestValue();
    });
    for (final size in [
      const Size(390, 844),
      const Size(844, 390),
      const Size(320, 700),
    ]) {
      tester.view.physicalSize = size;
      tester.platformDispatcher.textScaleFactorTestValue = size.width == 320
          ? 1.6
          : 1;
      await mount(tester);
      await tester.runAsync(
        () async => Future<void>.delayed(const Duration(milliseconds: 180)),
      );
      await tester.pump(const Duration(milliseconds: 200));
      expect(tester.takeException(), isNull);
      if (size.width == 390) {
        final boundary = tester.renderObject<RenderRepaintBoundary>(
          find.byKey(const ValueKey('auth-preview')),
        );
        await tester.runAsync(() async {
          final image = await boundary.toImage();
          final bytes = await image.toByteData(format: ui.ImageByteFormat.png);
          Directory('build/previews').createSync(recursive: true);
          File('build/previews/auth.png')
              .writeAsBytesSync(bytes!.buffer.asUint8List());
          image.dispose();
        });
        tester.view.viewInsets = const FakeViewPadding(bottom: 330);
        await tester.tap(find.byKey(const ValueKey('account-email')));
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 250));
        await tester.ensureVisible(
          find.widgetWithText(FilledButton, 'Sign in'),
        );
        expect(tester.takeException(), isNull);
        tester.view.resetViewInsets();
      }
      await tester.pumpWidget(const SizedBox());
      await tester.pump();
    }
  });
}
