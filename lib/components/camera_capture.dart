import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../services/pico_store.dart';
import 'workflow_review.dart';

/// "camera", "open camera", "take a photo"… Short phrases only, so a sentence
/// that just mentions a camera still becomes a normal draft.
bool wantsCamera(String words) {
  final text = words.toLowerCase().replaceAll(RegExp(r'[^a-z ]'), ' ').trim();
  final count = text.split(RegExp(r'\s+')).where((w) => w.isNotEmpty).length;
  return count <= 4 &&
      RegExp(r'\b(camera|take a (photo|picture))\b').hasMatch(text);
}

/// Takes one photo and sends it to the computer's write workspace through the
/// normal upload, so the computer still approves the save.
Future<void> sendPhoto(BuildContext context, PicoStore store) async {
  final messenger = ScaffoldMessenger.of(context);
  void notice(String text) =>
      messenger.showSnackBar(SnackBar(content: Text(text)));
  final device = store.devices.firstOrNull?['id'] as String?;
  if (device == null) {
    notice('Connect your computer first.');
    return;
  }
  final grant = await chooseWorkspace(context, store, device, write: true);
  if (grant == null) return;
  XFile? photo;
  try {
    photo = await ImagePicker().pickImage(
      source: ImageSource.camera,
      maxWidth: 1600,
      imageQuality: 70,
    );
  } catch (_) {
    notice('Allow camera access in your device settings.');
    return;
  }
  if (photo == null) return;
  final bytes = await photo.readAsBytes();
  if (bytes.length > 1024 * 1024) {
    notice('That photo is over 1 MB. Try again a little farther away.');
    return;
  }
  final now = DateTime.now();
  String two(int value) => value.toString().padLeft(2, '0');
  final name =
      'Pico photo ${now.year}-${two(now.month)}-${two(now.day)} '
      '${two(now.hour)}.${two(now.minute)}.${two(now.second)}.jpg';
  final receipt = await store.uploadFile(device, name, bytes, grant: grant);
  notice(
    receipt == null
        ? store.error ?? 'Couldn’t send the photo.'
        : 'Photo sent. Approve it on your computer to save it.',
  );
}
