import 'dart:math' as math;
import 'package:flutter/material.dart';

class ListeningWave extends StatefulWidget {
  const ListeningWave({super.key, this.level = 0});
  final double level;
  @override
  State<ListeningWave> createState() => _ListeningWaveState();
}

class _ListeningWaveState extends State<ListeningWave>
    with SingleTickerProviderStateMixin {
  late final AnimationController _motion = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 900),
  );
  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (MediaQuery.disableAnimationsOf(context)) {
      _motion.stop();
    } else {
      _motion.repeat();
    }
  }

  @override
  void dispose() {
    _motion.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => ExcludeSemantics(
    child: SizedBox(
      width: 28,
      height: 22,
      child: AnimatedBuilder(
        animation: _motion,
        builder: (context, _) => Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: List.generate(5, (i) {
            final phase = math.sin(_motion.value * math.pi * 2 + i * .8).abs();
            final height = MediaQuery.disableAnimationsOf(context)
                ? 5.0 + (i % 3) * 4
                : 4 + phase * (8 + widget.level.clamp(0, 1) * 10);
            return Container(
              width: 3,
              height: height.toDouble(),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.primary,
                borderRadius: BorderRadius.circular(2),
              ),
            );
          }),
        ),
      ),
    ),
  );
}
