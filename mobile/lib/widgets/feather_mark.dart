import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../theme.dart';

/// Pankh's mark: a feather drawn the way Gond painters fill a shape, with rows of short
/// dashes and a line of dots along the quill.
class FeatherMark extends StatelessWidget {
  const FeatherMark({super.key, this.size = 48, this.semanticLabel});

  final double size;
  final String? semanticLabel;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: semanticLabel,
      image: semanticLabel != null,
      excludeSemantics: true,
      child: CustomPaint(size: Size(size * 0.62, size), painter: const _FeatherPainter()),
    );
  }
}

class _FeatherPainter extends CustomPainter {
  const _FeatherPainter();

  static const _bands = [PankhColors.peacock, PankhColors.leaf, PankhColors.turmeric];

  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width;
    final h = size.height;
    final start = Offset(w * 0.30, h * 0.98);
    final control = Offset(w * 0.18, h * 0.42);
    final end = Offset(w * 0.78, h * 0.03);

    Offset point(double t) {
      final u = 1 - t;
      return start * (u * u) + control * (2 * u * t) + end * (t * t);
    }

    Offset tangent(double t) {
      final d = (control - start) * (2 * (1 - t)) + (end - control) * (2 * t);
      return d / d.distance;
    }

    final stroke = Paint()
      ..strokeCap = StrokeCap.round
      ..style = PaintingStyle.stroke;

    // Barbs: rows of dashes sweeping up towards the tip on both sides of the quill.
    const barbs = 26;
    for (var i = 0; i < barbs; i++) {
      final t = 0.16 + 0.80 * i / (barbs - 1);
      final envelope = math.sin(math.pi * math.pow((t - 0.12) / 0.86, 0.8).clamp(0.0, 1.0));
      final length = w * 0.52 * envelope;
      final p = point(t);
      final along = tangent(t);
      final normal = Offset(-along.dy, along.dx);
      stroke
        ..color = _bands[math.min(2, ((t - 0.16) / 0.27).floor())]
        ..strokeWidth = math.max(1.2, w * 0.035);
      for (final side in const [-1.0, 1.0]) {
        final direction = normal * side * 0.82 + along * 0.57;
        final dir = direction / direction.distance;
        const dashes = 3;
        for (var d = 0; d < dashes; d++) {
          final a = p + dir * (length * (0.12 + d * 0.30));
          final b = p + dir * (length * (0.12 + d * 0.30 + 0.20));
          canvas.drawLine(a, b, stroke);
        }
      }
    }

    // Quill.
    final quill = Path()
      ..moveTo(start.dx, start.dy)
      ..quadraticBezierTo(control.dx, control.dy, end.dx, end.dy);
    canvas.drawPath(
      quill,
      stroke
        ..color = PankhColors.ink
        ..strokeWidth = math.max(1.4, w * 0.045),
    );

    // Dots along the quill.
    final dot = Paint()..color = PankhColors.paper;
    for (var i = 1; i < 9; i++) {
      canvas.drawCircle(point(0.18 + i * 0.085), math.max(0.8, w * 0.016), dot);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
