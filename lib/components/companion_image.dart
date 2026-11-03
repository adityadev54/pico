import 'dart:math' as math;

import 'package:flutter/material.dart';

const companionEmotions = ['angry', 'curious', 'happy', 'sleepy', 'surprised'];

/// Every mood uses the original animated character, with restrained reaction motion.
class CompanionImage extends StatefulWidget {
  const CompanionImage({
    super.key,
    required this.character,
    required this.mood,
    required this.size,
  });
  final String character, mood;
  final double size;
  @override
  State<CompanionImage> createState() => _CompanionImageState();
}

class _CompanionImageState extends State<CompanionImage>
    with SingleTickerProviderStateMixin {
  late final AnimationController motion = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 2400),
  );
  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _animate();
  }

  @override
  void didUpdateWidget(covariant CompanionImage old) {
    super.didUpdateWidget(old);
    if (old.mood != widget.mood || old.character != widget.character) {
      motion.value = 0;
    }
    _animate();
  }

  void _animate() {
    if (MediaQuery.disableAnimationsOf(context) ||
        !companionEmotions.contains(widget.mood)) {
      motion.stop();
      motion.value = 0;
    } else if (!motion.isAnimating) {
      motion.repeat();
    }
  }

  @override
  void dispose() {
    motion.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    const activities = {
      'angry': 'stuck',
      'curious': 'thinking',
      'happy': 'done',
      'sleepy': 'idle',
      'surprised': 'needsYou',
    };
    final activity = activities[widget.mood] ?? widget.mood;
    final reduced = MediaQuery.disableAnimationsOf(context);
    final image = Image.asset(
      'assets/characters/${widget.character}/$activity.${reduced ? 'png' : 'gif'}',
      width: widget.size,
      height: widget.size,
      gaplessPlayback: true,
      excludeFromSemantics: true,
    );
    return Semantics(
      label: '${widget.character}, ${widget.mood}',
      image: true,
      child: AnimatedBuilder(
        animation: motion,
        child: image,
        builder: (context, child) {
          final wave = reduced ? 0.0 : math.sin(motion.value * 2 * math.pi);
          return Transform.translate(
            offset: Offset(0, widget.mood == 'happy' ? wave * 3 : 0),
            child: Transform.rotate(
              angle: widget.mood == 'angry'
                  ? wave * .025
                  : widget.mood == 'curious'
                  ? -.035 + wave * .01
                  : widget.mood == 'sleepy'
                  ? wave * .015
                  : 0,
              child: Transform.scale(
                scale: widget.mood == 'surprised'
                    ? 1 + math.max(0, wave) * .05
                    : 1,
                child: child,
              ),
            ),
          );
        },
      ),
    );
  }
}
