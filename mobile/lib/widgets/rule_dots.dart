import 'package:flutter/material.dart';

import '../data/models.dart';
import '../theme.dart';

/// One dot per Rule of a Scheme, joined by dashes as in a Gond border.
///
/// Filled: met. Ringed: waived. Hollow: not known yet. Struck through: not met.
class RuleDots extends StatelessWidget {
  const RuleDots({super.key, required this.rules, this.dotSize = 12});

  final List<RuleResult> rules;
  final double dotSize;

  @override
  Widget build(BuildContext context) {
    final met = rules.where((r) => r.outcome == Outcome.pass || r.outcome == Outcome.waived).length;
    final notMet = rules.where((r) => r.outcome == Outcome.fail).length;
    final unknown = rules.where((r) => r.outcome == Outcome.unknown).length;
    return Semantics(
      label: '$met met, $notMet not met, $unknown not known, of ${rules.length} conditions',
      excludeSemantics: true,
      child: CustomPaint(
        size: Size(rules.length * dotSize * 2 - dotSize, dotSize),
        painter: _RuleDotsPainter([for (final r in rules) r.outcome], dotSize),
      ),
    );
  }
}

class _RuleDotsPainter extends CustomPainter {
  _RuleDotsPainter(this.outcomes, this.dotSize);

  final List<Outcome> outcomes;
  final double dotSize;

  @override
  void paint(Canvas canvas, Size size) {
    final r = dotSize / 2;
    final dash = Paint()
      ..color = PankhColors.line
      ..strokeWidth = 1.5
      ..strokeCap = StrokeCap.round;
    for (var i = 0; i < outcomes.length; i++) {
      final center = Offset(r + i * dotSize * 2, r);
      if (i > 0) {
        canvas.drawLine(center - Offset(dotSize * 1.3, 0), center - Offset(dotSize * 0.7, 0), dash);
      }
      _dot(canvas, center, r, outcomes[i]);
    }
  }

  void _dot(Canvas canvas, Offset c, double r, Outcome outcome) {
    final fill = Paint()..style = PaintingStyle.fill;
    final ring = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = r * 0.34;
    switch (outcome) {
      case Outcome.pass:
        canvas.drawCircle(c, r, fill..color = PankhColors.leaf);
      case Outcome.waived:
        canvas.drawCircle(c, r * 0.83, ring..color = PankhColors.leaf);
        canvas.drawCircle(c, r * 0.34, fill..color = PankhColors.leaf);
      case Outcome.unknown:
        canvas.drawCircle(c, r * 0.83, ring..color = PankhColors.inkSoft.withValues(alpha: 0.45));
      case Outcome.fail:
        canvas.drawCircle(c, r * 0.83, ring..color = PankhColors.laterite);
        canvas.drawLine(
          c + Offset(-r * 0.55, r * 0.55),
          c + Offset(r * 0.55, -r * 0.55),
          ring..strokeCap = StrokeCap.round,
        );
    }
  }

  @override
  bool shouldRepaint(_RuleDotsPainter old) => old.outcomes != outcomes || old.dotSize != dotSize;
}
