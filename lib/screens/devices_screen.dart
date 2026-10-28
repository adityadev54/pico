import 'package:flutter/material.dart';
import 'package:heroicons/heroicons.dart';

import '../components/screen_chrome.dart';
import '../components/section_group.dart';
import '../components/pico_dialog.dart';
import '../components/device_setup.dart';
import 'account_screen.dart';
import '../services/pico_store.dart';

class DevicesScreen extends StatefulWidget {
  const DevicesScreen({super.key, required this.store, this.handoff = false});
  final PicoStore store;
  final bool handoff;
  @override
  State<DevicesScreen> createState() => _DevicesScreenState();
}

class _DevicesScreenState extends State<DevicesScreen> {
  Map<String, dynamic>? _pairing;
  String? _error;
  bool _busy = false;
  Future<void> _pair() async {
    if (!widget.store.signedIn) {
      await Navigator.push(
        context,
        MaterialPageRoute<void>(
          builder: (_) => AccountScreen(store: widget.store),
        ),
      );
      if (!mounted || !widget.store.signedIn) return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final pairing = await widget.store.createPairing();
      if (mounted) setState(() => _pairing = pairing);
    } catch (_) {
      if (mounted) {
        setState(
          () => _error =
              'Couldn’t get a code. Check your connection and try again.',
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _handoff(Map<String, dynamic> device) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await widget.store.client!.from('handoffs').insert({
        'user_id': widget.store.userId,
        'device_id': device['id'],
        'character': widget.store.character,
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Pico is on the way. Waiting for your computer.'),
          ),
        );
      }
    } catch (_) {
      if (mounted) {
        setState(() => _error = 'Couldn’t send Pico. Please try again.');
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => ListenableBuilder(
    listenable: widget.store,
    builder: (context, _) => Scaffold(
      body: Stack(
        children: [
          Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 680),
              child: ListView(
                padding: EdgeInsets.fromLTRB(
                  12,
                  MediaQuery.paddingOf(context).top + 86,
                  12,
                  40,
                ),
                children: [
                  if (widget.store.devices.isNotEmpty)
                    SectionGroup(
                      title: 'Computers',
                      children: [
                        for (final device in widget.store.devices)
                          SettingsRow(
                            icon: HeroIcons.computerDesktop,
                            title: device['name'],
                            subtitle:
                                '${device['os']} · ${widget.store.isOnline(device) ? 'Connected' : 'Disconnected'}',
                            onTap: widget.handoff && !_busy
                                ? () => _handoff(device)
                                : null,
                            trailing: widget.handoff
                                ? null
                                : IconButton(
                                    tooltip: 'Disconnect ${device['name']}',
                                    icon: HeroIcon(
                                      HeroIcons.linkSlash,
                                      size: 20,
                                      color: Theme.of(context)
                                          .colorScheme
                                          .onSurfaceVariant,
                                    ),
                                    onPressed: () => _disconnect(device),
                                  ),
                          ),
                      ],
                    ),
                  DeviceSetup(
                    character: widget.store.character,
                    signedIn: widget.store.signedIn,
                    busy: _busy,
                    code: _pairing?['code'] as String?,
                    error: _error,
                    onPair: _pair,
                  ),
                ],
              ),
            ),
          ),
          ScreenToolbar(onBack: () => Navigator.pop(context)),
        ],
      ),
    ),
  );
  Future<void> _disconnect(Map<String, dynamic> device) async {
    final yes = await showPicoDialog<bool>(
      context: context,
      builder: (context) => PicoDialog(
        title: Text('Disconnect ${device['name']}?'),
        content: const Text('You can connect it again with a new code.'),
        actions: [
          PicoDialogAction(
            label: 'Keep connected',
            onPressed: () => Navigator.pop(context, false),
          ),
          PicoDialogAction(
            label: 'Disconnect',
            destructive: true,
            onPressed: () => Navigator.pop(context, true),
          ),
        ],
      ),
    );
    if (yes != true) return;
    try {
      await widget.store.disconnect(device['id']);
    } catch (_) {
      if (mounted) {
        setState(() => _error = 'Couldn’t disconnect. Please try again.');
      }
    }
  }
}
