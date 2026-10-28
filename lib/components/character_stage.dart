import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter/services.dart';

import 'character_ground.dart';

class CharacterStage extends StatefulWidget {
  const CharacterStage({
    super.key,
    required this.character,
    required this.mood,
    required this.onVoice,
    required this.onReports,
    required this.onHandoff,
  });
  final String character;
  final String mood;
  final VoidCallback onVoice;
  final VoidCallback onReports;
  final VoidCallback onHandoff;
  @override
  State<CharacterStage> createState() => _CharacterStageState();
}

class _CharacterStageState extends State<CharacterStage> {
  Timer? _tapTimer;
  int _taps = 0;
  void _tap() {
    _taps++;
    _tapTimer?.cancel();
    if (_taps == 3) {
      _taps = 0;
      HapticFeedback.selectionClick();
      widget.onReports();
      return;
    }
    _tapTimer = Timer(const Duration(milliseconds: 330), () {
      if (_taps == 2) {
        HapticFeedback.lightImpact();
        widget.onVoice();
      }
      _taps = 0;
    });
  }

  @override
  void dispose() {
    _tapTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Semantics(
    label:
        '${widget.character}, ${widget.mood}. Double tap to talk. Triple tap to search activity. Swipe right for your computer.',
    customSemanticsActions: {
      const CustomSemanticsAction(label: 'Talk'): widget.onVoice,
      const CustomSemanticsAction(label: 'Search activity'): widget.onReports,
      const CustomSemanticsAction(label: 'Send to computer'): widget.onHandoff,
    },
    child: GestureDetector(
      onTap: _tap,
      onHorizontalDragEnd: (details) {
        if ((details.primaryVelocity ?? 0) > 180) widget.onHandoff();
      },
      child: SizedBox(
        width: 200,
        height: 188,
        child: Stack(
          alignment: Alignment.bottomCenter,
          children: [
            const Positioned.fill(child: CharacterGround()),
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Image.asset(
                'assets/characters/${widget.character}/${widget.mood}.${MediaQuery.disableAnimationsOf(context) ? 'png' : 'gif'}',
                width: 168,
                height: 168,
                gaplessPlayback: true,
                excludeFromSemantics: true,
              ),
            ),
          ],
        ),
      ),
    ),
  );
}
