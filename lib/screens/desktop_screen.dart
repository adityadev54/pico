import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../components/pico_brand.dart';
import '../components/floating_surface.dart';
import '../screens/permissions_screen.dart';
import '../services/pico_store.dart';
import '../services/desktop_connection.dart';

/// Desktop has device pairing only; account sign-in belongs to the phone.
class DesktopScreen extends StatefulWidget {
  const DesktopScreen({super.key, required this.store});
  final PicoStore store;
  @override
  State<DesktopScreen> createState() => _DesktopScreenState();
}

class _DesktopScreenState extends State<DesktopScreen> {
  final code = TextEditingController();
  late final connection = DesktopConnection(widget.store.preferences);
  @override
  void initState() {
    super.initState();
    connection.load();
  }

  @override
  void dispose() {
    code.dispose();
    connection.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => ListenableBuilder(
    listenable: connection,
    builder: (context, _) => Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: EdgeInsets.all(12),
            child: ConstrainedBox(
              constraints: BoxConstraints(maxWidth: 360),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  GestureDetector(
                    onSecondaryTap: () => Navigator.push(
                      context,
                      MaterialPageRoute<void>(
                        builder: (_) => PermissionsScreen(store: widget.store),
                      ),
                    ),
                    child: Image.asset(
                      'assets/characters/${connection.character}/${connection.mood}.${MediaQuery.disableAnimationsOf(context) ? 'png' : 'gif'}',
                      width: 144,
                      height: 144,
                      semanticLabel: 'Pico companion',
                    ),
                  ),
                  PicoWordmark(),
                  SizedBox(height: 24),
                  if (!connection.paired) ...[
                    const Text(
                      'Connect your phone',
                      style: TextStyle(fontSize: 22),
                    ),
                    const SizedBox(height: 12),
                    FloatingSurface(
                      child: TextField(
                        controller: code,
                        keyboardType: TextInputType.number,
                        inputFormatters: [
                          FilteringTextInputFormatter.digitsOnly,
                          LengthLimitingTextInputFormatter(6),
                        ],
                        decoration: const InputDecoration(
                          hintText: '6-digit code',
                        ),
                        textAlign: TextAlign.center,
                      ),
                    ),
                    const SizedBox(height: 12),
                    FilledButton(
                      onPressed: connection.busy
                          ? null
                          : () => connection.pair(code.text.trim()),
                      child: Text(connection.busy ? 'Connecting…' : 'Connect'),
                    ),
                  ] else ...[
                    Text(
                      connection.online
                          ? 'Connected to your phone'
                          : 'Waiting to reconnect',
                    ),
                    for (final place in connection.places.take(1))
                      Padding(
                        padding: const EdgeInsets.all(12),
                        child: Column(
                          children: [
                            const Text(
                              'Welcome back',
                              style: TextStyle(fontSize: 22),
                            ),
                            const SizedBox(height: 12),
                            Text(place['sentence'] as String),
                            const SizedBox(height: 12),
                            FilledButton(
                              onPressed: () async {
                                await Clipboard.setData(
                                  ClipboardData(
                                    text: place['sentence'] as String,
                                  ),
                                );
                                await connection.dismiss(
                                  place['place_id'] as String,
                                );
                              },
                              child: const Text('Copy note'),
                            ),
                          ],
                        ),
                      ),
                  ],
                  if (connection.error != null)
                    Padding(
                      padding: const EdgeInsets.all(12),
                      child: Text(connection.error!),
                    ),
                  TextButton(
                    onPressed: () => Navigator.push(
                      context,
                      MaterialPageRoute<void>(
                        builder: (_) => PermissionsScreen(store: widget.store),
                      ),
                    ),
                    child: Text('Pico permissions'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    ),
  );
}
