import 'package:flutter/material.dart';

/// Fade the scrolling content itself; header/footer surfaces stay fully solid.
class ScrollEdgeFade extends StatelessWidget {
  const ScrollEdgeFade({super.key, required this.child, this.extent = 18});
  final Widget child;
  final double extent;
  @override
  Widget build(BuildContext context) => ClipRect(
    child: ShaderMask(
      blendMode: BlendMode.dstIn,
      shaderCallback: (bounds) {
        final edge = (extent / bounds.height.clamp(1, double.infinity)).clamp(
          0.0,
          .5,
        );
        return LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: const [
            Colors.transparent,
            Colors.black,
            Colors.black,
            Colors.transparent,
          ],
          stops: [0, edge, 1 - edge, 1],
        ).createShader(bounds);
      },
      child: child,
    ),
  );
}
