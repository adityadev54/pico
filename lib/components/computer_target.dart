import 'package:flutter/material.dart';

import '../services/pico_store.dart';
import 'pico_dialog.dart';

Future<String?> chooseComputer(
  BuildContext context,
  PicoStore store, {
  String? hint,
}) async {
  if (store.devices.isEmpty) {
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(const SnackBar(content: Text('connect a computer first')));
    return null;
  }
  if (hint != null) {
    final name = hint.toLowerCase();
    final matching = store.devices
        .where(
          (device) =>
              device['name'].toString().toLowerCase().contains(name) ||
              (RegExp(r'mac|macbook').hasMatch(name) &&
                  device['os'] == 'macos') ||
              (RegExp(r'windows|pc').hasMatch(name) &&
                  device['os'] == 'windows'),
        )
        .toList();
    if (matching.length == 1) return matching.single['id'];
  }
  if (store.devices.length == 1) return store.devices.single['id'];
  return showPicoDialog<String>(
    context: context,
    builder: (context) => Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        const Text(
          'which computer?',
          style: TextStyle(fontSize: 20, fontWeight: FontWeight.w600),
        ),
        for (final device in store.devices)
          ListTile(
            title: Text(device['name']),
            subtitle: Text(
              store.isOnline(device)
                  ? 'connected'
                  : 'offline · request will wait',
            ),
            onTap: () => Navigator.pop(context, device['id']),
          ),
      ],
    ),
  );
}
