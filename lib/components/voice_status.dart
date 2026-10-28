import 'package:flutter/material.dart';
import 'package:heroicons/heroicons.dart';
import 'floating_surface.dart';
import 'listening_wave.dart';

class VoiceStatus extends StatelessWidget {
  const VoiceStatus({
    super.key,
    required this.text,
    required this.listening,
    required this.onStop,
    this.level = 0,
  });
  final String text;
  final double level;
  final bool listening;
  final VoidCallback onStop;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.fromLTRB(12, 4, 12, 12),
    child: Semantics(
      liveRegion: true,
      child: FloatingSurface(
        child: Padding(
          padding: const EdgeInsets.only(left: 18, right: 4),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (listening) ...[
                ListeningWave(level: level),
                const SizedBox(width: 12),
              ],
              Flexible(
                child: Text(
                  text.isEmpty
                      ? (listening ? 'Listening…' : 'One moment…')
                      : text,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 14),
                ),
              ),
              IconButton(
                tooltip: listening ? 'Stop listening' : 'Dismiss voice status',
                onPressed: onStop,
                icon: HeroIcon(
                  listening ? HeroIcons.stop : HeroIcons.xMark,
                  size: 19,
                ),
              ),
            ],
          ),
        ),
      ),
    ),
  );
}
