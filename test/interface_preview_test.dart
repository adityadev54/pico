import 'dart:ui' as ui;

import 'package:flutter/rendering.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:pico/screens/home_screen.dart';
import 'package:pico/components/conversation_view.dart';
import 'package:pico/components/chat_bubble_shape.dart';
import 'package:pico/models/place.dart';
import 'package:pico/services/pico_store.dart';
import 'package:pico/theme/app_theme.dart';

import 'helpers/capture_preview.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUpAll(() async {
    final font = FontLoader('DM Sans')
      ..addFont(rootBundle.load('assets/fonts/DMSans.ttf'));
    await font.load();
  });
  testWidgets('Thoughts and replies fit content with aligned speaker corners', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    SharedPreferences.setMockInitialValues({});
    final store = PicoStore(await SharedPreferences.getInstance());
    addTearDown(store.dispose);
    await tester.pumpWidget(
      RepaintBoundary(
        key: const ValueKey('interface-preview'),
        child: MaterialApp(
          theme: PicoTheme.light,
          home: Scaffold(
            body: Padding(
              padding: const EdgeInsets.fromLTRB(12, 100, 12, 12),
              child: PlaceMessage(
                store: store,
                place: Place(
                  id: 'speaker-test',
                  sentence: 'Just work',
                  created: DateTime.now(),
                  headStart: 'Your draft is ready to review.',
                ),
              ),
            ),
          ),
        ),
      ),
    );
    final surfaces = tester
        .widgetList<Material>(find.byType(Material))
        .where((m) => m.shape is ChatBubbleShape)
        .toList();
    expect(surfaces.length, 2);
    expect((surfaces.first.shape! as ChatBubbleShape).mine, isTrue);
    expect((surfaces.last.shape! as ChatBubbleShape).mine, isFalse);
    final shapes = find.byWidgetPredicate(
      (w) => w is Material && w.shape is ChatBubbleShape,
    );
    expect(tester.getSize(shapes.first).width, lessThan(200));
    expect(
      tester.getSize(shapes.last).width,
      greaterThan(tester.getSize(shapes.first).width),
    );
    expect(tester.getTopRight(shapes.first).dx, 378);
    expect(tester.getTopLeft(shapes.last).dx, 12);
    expect(
      (surfaces.first.shape! as ChatBubbleShape).borderRadius
          .resolve(TextDirection.ltr)
          .topRight,
      Radius.zero,
    );
    expect(
      (surfaces.last.shape! as ChatBubbleShape).borderRadius
          .resolve(TextDirection.ltr)
          .topLeft,
      Radius.zero,
    );
    await capturePreview(tester, 'speaker-tails');
    expect(tester.takeException(), isNull);
  });
  testWidgets('Save, search, park and select a Place through the phone UI', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    SharedPreferences.setMockInitialValues({});
    final store = PicoStore(await SharedPreferences.getInstance());
    await store.load();
    await tester.pumpWidget(
      RepaintBoundary(
        key: const ValueKey('interface-preview'),
        child: MaterialApp(
          theme: PicoTheme.light,
          debugShowCheckedModeBanner: false,
          home: HomeScreen(store: store),
        ),
      ),
    );
    await capturePreview(tester, 'home');
    await tester.tap(find.text('Save a Place'));
    await tester.pump();
    await tester.enterText(find.byType(TextField), 'Finish the landlord email');
    tester.view.viewInsets = const FakeViewPadding(bottom: 330);
    await capturePreview(tester, 'composer-keyboard');
    // The platform keyboard is translucent/rounded. The underlying page must
    // stay light rather than revealing the dark drawer shell.
    final boundary = tester.renderObject<RenderRepaintBoundary>(
      find.byKey(const ValueKey('interface-preview')),
    );
    await tester.runAsync(() async {
      final image = await boundary.toImage();
      final bytes = await image.toByteData(format: ui.ImageByteFormat.rawRgba);
      final offset = (600 * image.width + 10) * 4;
      final pixel = bytes!.buffer.asUint8List();
      expect(pixel.sublist(offset, offset + 3), [245, 241, 238]);
      image.dispose();
    });
    expect(tester.getBottomRight(find.byTooltip('Send')).dy, lessThan(514));
    tester.view.resetViewInsets();
    await tester.pump();
    await tester.tap(find.byTooltip('Send'));
    await tester.pump();
    expect(store.places.single.sentence, 'Finish the landlord email');
    await tester.tap(find.byTooltip('Save a Place'));
    await tester.pump();
    await tester.longPress(
      find.descendant(
        of: find.byType(PlaceMessage),
        matching: find.text(store.places.single.sentence),
      ),
    );
    await tester.pumpAndSettle();
    await capturePreview(tester, 'place-actions');
    await tester.tap(find.text('Park'));
    await tester.pumpAndSettle();
    await tester.pump();
    expect(store.places.single.parked, isTrue);
    await capturePreview(tester, 'parked-place');
    await tester.tap(find.byTooltip('Search Pico'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), 'mica');
    await tester.pump();
    expect(find.text('Mica'), findsOneWidget);
    await tester.enterText(find.byType(TextField), 'unmatched');
    await tester.pump();
    expect(find.text('No chats or agents found.'), findsOneWidget);
    await tester.pageBack();
    await tester.pumpAndSettle();
    await tester.tap(find.byTooltip('Open menu'));
    await capturePreview(tester, 'drawer');
    await tester.tap(find.byTooltip('Settings'));
    await capturePreview(tester, 'settings');
    await tester.ensureVisible(find.text('Appearance'));
    await tester.tap(find.text('Appearance'));
    await tester.pumpAndSettle();
    await capturePreview(tester, 'appearance');
    await tester.tap(find.text('Agent'));
    await capturePreview(tester, 'characters');
    await tester.tap(find.bySemanticsLabel('Mica'));
    await tester.pumpAndSettle();
    expect(store.character, 'mica');
    await tester.tap(find.byTooltip('Close'));
    await tester.pumpAndSettle();
    await tester.pumpWidget(const SizedBox());
    store.dispose();
  });
}
