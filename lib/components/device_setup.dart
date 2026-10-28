import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:heroicons/heroicons.dart';
import '../services/config.dart';
import '../theme/app_theme.dart';
import 'account_submit.dart';
import 'character_ground.dart';
import 'floating_surface.dart';

/// The same chosen companion anchors setup and the computer handoff.
class DeviceSetup extends StatelessWidget {
  const DeviceSetup({
    super.key,
    required this.character,
    required this.busy,
    required this.signedIn,
    required this.onPair,
    this.code,
    this.error,
  });
  final String character;
  final bool busy, signedIn;
  final VoidCallback onPair;
  final String? code, error;

  Future<void> _copy(BuildContext context, String text, String label) async {
    await Clipboard.setData(ClipboardData(text: text));
    if (context.mounted) {
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(label)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final address = Config.downloadUrl;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        SizedBox(
          height: 188,
          child: Stack(
            alignment: Alignment.center,
            children: [
              Positioned(
                left: 0,
                right: 0,
                bottom: 12,
                child: Container(
                  height: 100,
                  margin: EdgeInsets.symmetric(horizontal: 30),
                  decoration: BoxDecoration(
                    border: Border.all(
                      color: Theme.of(context).colorScheme.outlineVariant,
                    ),
                    borderRadius: BorderRadius.circular(24),
                  ),
                ),
              ),
              Positioned.fill(child: CharacterGround()),
              Image.asset(
                'assets/characters/$character/idle.${MediaQuery.disableAnimationsOf(context) ? 'png' : 'gif'}',
                width: 168,
                height: 168,
                gaplessPlayback: true,
                semanticLabel: 'Your chosen companion, $character',
              ),
              Positioned(
                right: 16,
                bottom: 12,
                child: FloatingSurface(
                  child: Padding(
                    padding: EdgeInsets.all(14),
                    child: HeroIcon(
                      HeroIcons.computerDesktop,
                      size: 25,
                      color: PicoTheme.accent,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
        SizedBox(height: 12),
        Text(
          'Bring your companion over',
          style: TextStyle(
            fontSize: 27,
            fontWeight: FontWeight.w600,
            letterSpacing: -.8,
          ),
        ),
        SizedBox(height: 12),
        Text(
          'Use the code from your phone.',
          style: TextStyle(
            color: Theme.of(context).colorScheme.onSurfaceVariant,
            fontSize: 14,
          ),
        ),
        SizedBox(height: 12),
        Text(
          '1  Open on your computer',
          style: TextStyle(
            fontSize: 13,
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
        ),
        SizedBox(height: 12),
        FloatingSurface(
          child: Padding(
            padding: EdgeInsets.only(left: 18, right: 4),
            child: Row(
              children: [
                Expanded(
                  child: SelectableText(
                    address.replaceFirst('https://', ''),
                    style: TextStyle(fontSize: 15, fontWeight: FontWeight.w500),
                  ),
                ),
                IconButton(
                  tooltip: 'Copy setup address',
                  onPressed: () =>
                      _copy(context, address, 'Setup address copied'),
                  icon: HeroIcon(
                    HeroIcons.documentDuplicate,
                    size: 20,
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
                ),
              ],
            ),
          ),
        ),
        SizedBox(height: 12),
        Text(
          'Download Pico, then open it.',
          style: TextStyle(
            fontSize: 13,
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
        ),
        SizedBox(height: 12),
        Text(
          code == null
              ? '2  Get a code for Pico'
              : '2  Enter this code in Pico',
          style: TextStyle(
            fontSize: 13,
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
        ),
        SizedBox(height: 12),
        if (code != null) ...[
          FloatingSurface(
            child: Padding(
              padding: EdgeInsets.fromLTRB(18, 14, 6, 14),
              child: Row(
                children: [
                  Expanded(
                    child: SelectableText(
                      code!,
                      style: TextStyle(
                        fontSize: 25,
                        fontWeight: FontWeight.w600,
                        letterSpacing: 2,
                      ),
                    ),
                  ),
                  IconButton(
                    tooltip: 'Copy connection code',
                    onPressed: () =>
                        _copy(context, code!, 'Connection code copied'),
                    icon: HeroIcon(
                      HeroIcons.documentDuplicate,
                      size: 20,
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
            ),
          ),
          SizedBox(height: 12),
          Text(
            'One use · expires in 5 minutes',
            style: TextStyle(
              fontSize: 12,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ),
          SizedBox(height: 12),
        ],
        AccountSubmit(
          label: !signedIn
              ? 'Sign in to connect'
              : code == null
              ? 'Get connection code'
              : 'Get a new code',
          busy: busy,
          onSubmit: onPair,
        ),
        if (error != null)
          Padding(
            padding: EdgeInsets.only(top: 12),
            child: Text(
              error!,
              style: TextStyle(color: PicoTheme.accentDeep, fontSize: 13),
            ),
          ),
      ],
    );
  }
}
