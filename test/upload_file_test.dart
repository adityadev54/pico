import 'dart:typed_data';

import 'package:cross_file/cross_file.dart';
import 'package:file_picker_platform_interface/file_picker_platform_interface.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:pico/screens/devices_screen.dart';
import 'package:pico/services/pico_store.dart';
import 'package:pico/theme/app_theme.dart';

base class _PickedFile extends PlatformFile {
  _PickedFile(this._name, this._bytes);
  final String _name;
  final Uint8List _bytes;
  @override
  String get name => _name;
  @override
  Uri get uri => Uri.parse('file:///tmp/$_name');
  @override
  XFile get xFile => XFile.fromData(_bytes, name: _name);
  @override
  int? lengthSync() => _bytes.length;
  @override
  Future<int?> length() async => _bytes.length;
  @override
  Future<Uint8List> readAsBytes() async => _bytes;
  @override
  Stream<Uint8List> readAsByteStream() => Stream.value(_bytes);
}

class _FakePicker extends FilePickerPlatform {
  _FakePicker(this.file);
  final PlatformFile? file;
  @override
  Future<PlatformFile?> pickFile({
    String? dialogTitle,
    String? initialDirectory,
    FileType type = FileType.any,
    List<String>? allowedExtensions,
    Function(FilePickerStatus)? onFileLoading,
    int compressionQuality = 0,
    AndroidOptions androidOptions = const AndroidOptions(),
    DarwinOptions darwinOptions = const DarwinOptions(),
    WindowsOptions windowsOptions = const WindowsOptions(),
    LinuxOptions linuxOptions = const LinuxOptions(),
    WebOptions webOptions = const WebOptions(),
  }) async => file;
}

class TestUploadStore extends PicoStore {
  TestUploadStore(super.preferences);
  final List<Map<String, dynamic>> uploads = [];
  @override
  Future<Map<String, dynamic>?> uploadFile(
    String device,
    String name,
    Uint8List bytes, {
    String? grant,
  }) async {
    uploads.add({'device': device, 'name': name, 'bytes': bytes, 'grant': grant});
    return {'artifact_id': 'a' * 64, 'duplicate': false};
  }
}

Future<TestUploadStore> mountDevices(WidgetTester tester) async {
  SharedPreferences.setMockInitialValues({});
  final store = TestUploadStore(await SharedPreferences.getInstance());
  store.devices.add({
    'id': 'device-1',
    'name': 'Test Mac',
    'os': 'macos',
    'last_seen': DateTime.now().toUtc().toIso8601String(),
    'workspaces': [
      {'id': 'ws-1', 'name': 'Project', 'access': 'write'},
    ],
  });
  await tester.pumpWidget(
    MaterialApp(theme: PicoTheme.light, home: DevicesScreen(store: store)),
  );
  await tester.pumpAndSettle();
  return store;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  testWidgets('Upload button sends the picked file to that computer', (
    tester,
  ) async {
    FilePickerPlatform.instance = _FakePicker(
      _PickedFile('photo.jpg', Uint8List.fromList([1, 2, 3])),
    );
    final store = await mountDevices(tester);
    addTearDown(store.dispose);
    await tester.tap(find.byTooltip('Upload a file to Test Mac'));
    await tester.pumpAndSettle();
    expect(store.uploads.single['device'], 'device-1');
    expect(store.uploads.single['name'], 'photo.jpg');
    expect(store.uploads.single['bytes'], [1, 2, 3]);
    expect(store.uploads.single['grant'], 'ws-1');
    expect(find.textContaining('Uploading photo.jpg'), findsOneWidget);
  });

  testWidgets('Cancelled picks and oversize files upload nothing', (
    tester,
  ) async {
    FilePickerPlatform.instance = _FakePicker(null);
    final store = await mountDevices(tester);
    addTearDown(store.dispose);
    await tester.tap(find.byTooltip('Upload a file to Test Mac'));
    await tester.pumpAndSettle();
    expect(store.uploads, isEmpty);
    FilePickerPlatform.instance = _FakePicker(
      _PickedFile('big.bin', Uint8List(1024 * 1024 + 1)),
    );
    await tester.tap(find.byTooltip('Upload a file to Test Mac'));
    await tester.pumpAndSettle();
    expect(store.uploads, isEmpty);
  });
}
