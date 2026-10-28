import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

/// A held point marks where work can continue.
class PicoMark extends StatelessWidget {
  const PicoMark({super.key, this.size = 30, this.color});
  final double size;
  final Color? color;
  @override
  Widget build(BuildContext context) => SizedBox(
    width: size,
    height: size,
    child: CustomPaint(painter: PicoMarkPainter(color: color)),
  );
}

class PicoMarkPainter extends CustomPainter {
  const PicoMarkPainter({this.color});
  final Color? color;
  @override
  void paint(Canvas canvas, Size size) {
    canvas.save();
    canvas.scale(size.width / 100, size.height / 100);
    // Two anchors hold one precise point: the place to return to.
    final ink = Paint()
      ..color = color ?? PicoTheme.accent
      ..style = PaintingStyle.stroke
      ..strokeWidth = 12
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;
    final before = Path()
      ..moveTo(47, 20)
      ..lineTo(34, 20)
      ..quadraticBezierTo(20, 20, 20, 34)
      ..lineTo(20, 47);
    final after = Path()
      ..moveTo(53, 80)
      ..lineTo(66, 80)
      ..quadraticBezierTo(80, 80, 80, 66)
      ..lineTo(80, 53);
    canvas.drawPath(before, ink);
    canvas.drawPath(after, ink);
    canvas.drawCircle(
      const Offset(50, 50),
      9,
      Paint()..color = color ?? PicoTheme.signal,
    );
    canvas.restore();
  }

  @override
  bool shouldRepaint(PicoMarkPainter old) => old.color != color;
}

class PicoGradientText extends StatelessWidget {
  const PicoGradientText(this.text, {super.key, required this.style});
  final String text;
  final TextStyle style;
  @override
  Widget build(BuildContext context) {
    final child = Text(
      text,
      style: style.copyWith(color: PicoTheme.accentDeep),
    );
    if (MediaQuery.highContrastOf(context)) return child;
    return ShaderMask(
      blendMode: BlendMode.srcIn,
      shaderCallback: PicoTheme.brandGradient.createShader,
      child: child,
    );
  }
}

class PicoWordmark extends StatelessWidget {
  const PicoWordmark({super.key, this.light = false, this.size = 28});
  final bool light;
  final double size;
  @override
  Widget build(BuildContext context) => Semantics(
    label: 'Pico',
    excludeSemantics: true,
    child: Text(
      'pico',
      style: TextStyle(
        fontFamily: 'DM Sans',
        fontSize: size,
        fontWeight: FontWeight.w600,
        letterSpacing: -size * .055,
        height: 1.1,
        color: light ? PicoTheme.canvas : PicoTheme.ink,
      ),
    ),
  );
}

/// Pico's held point. No letterform or character reference.
class PicoEmblem extends StatelessWidget {
  const PicoEmblem({super.key, this.size = 160});
  final double size;
  @override
  Widget build(BuildContext context) => Semantics(
    label: 'Pico · your place, held',
    image: true,
    child: SizedBox(
      width: size,
      height: size,
      child: Center(child: PicoMark(size: size * .8)),
    ),
  );
}
