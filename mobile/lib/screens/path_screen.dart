import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/models.dart';
import '../l10n/generated/app_localizations.dart';
import '../state/providers.dart';
import '../theme.dart';
import '../widgets/citation_link.dart';
import '../widgets/error_view.dart';

/// Which scholarship to hold at each stage ahead, drawn as a path of dots.
class PathScreen extends ConsumerWidget {
  const PathScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final text = Theme.of(context).textTheme;
    final specs = ref.watch(factSchemaProvider).value;
    final language = Localizations.localeOf(context).languageCode;
    String levelName(String level) {
      final choice = specs?['education_level']?.choices.where((c) => c.key == level).firstOrNull;
      return choice == null ? level : localised(choice.labels, language);
    }

    return Scaffold(
      appBar: AppBar(title: Text(l10n.pathTitle)),
      body: ref
          .watch(schemePathProvider)
          .when(
            error: (error, _) =>
                ErrorView(error: error, onRetry: () => ref.invalidate(schemePathProvider)),
            loading: () => const Center(child: CircularProgressIndicator()),
            data: (stages) => stages.isEmpty
                ? Padding(
                    padding: const EdgeInsets.all(PankhSpace.gutter),
                    child: Text(l10n.pathEmpty, style: text.bodyLarge),
                  )
                : ListView(
                    padding: const EdgeInsets.fromLTRB(
                      PankhSpace.gutter,
                      PankhSpace.xs,
                      PankhSpace.gutter,
                      PankhSpace.xl,
                    ),
                    children: [
                      Text(l10n.pathOneAtATime, style: text.bodyMedium),
                      const SizedBox(height: PankhSpace.lg),
                      for (final (index, stage) in stages.indexed)
                        _StageRow(
                          stage: stage,
                          levelName: levelName(stage.level),
                          last: index == stages.length - 1,
                        ),
                    ],
                  ),
          ),
    );
  }
}

class _StageRow extends StatelessWidget {
  const _StageRow({required this.stage, required this.levelName, required this.last});

  final PathStage stage;
  final String levelName;
  final bool last;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final text = Theme.of(context).textTheme;
    final recommended = stage.recommended;
    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SizedBox(
            width: 28,
            child: Column(
              children: [
                Container(
                  margin: const EdgeInsets.only(top: 4),
                  width: 16,
                  height: 16,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: recommended == null ? PankhColors.card : PankhColors.leaf,
                    border: Border.all(
                      color: recommended == null ? PankhColors.line : PankhColors.leaf,
                      width: 2.5,
                    ),
                  ),
                ),
                if (!last)
                  Expanded(
                    child: CustomPaint(painter: _DashPainter(), child: const SizedBox(width: 2)),
                  ),
              ],
            ),
          ),
          const SizedBox(width: PankhSpace.sm + 2),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.only(bottom: PankhSpace.lg),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(stage.label, style: text.labelMedium),
                  Text(levelName, style: text.titleLarge),
                  const SizedBox(height: PankhSpace.sm),
                  if (recommended != null) ...[
                    Text(
                      '${l10n.pathHold}: ${recommended.scheme}',
                      style: text.titleSmall?.copyWith(color: PankhColors.leaf),
                    ),
                    const SizedBox(height: 2),
                    Text(recommended.value, style: text.bodyMedium),
                    CitationLink(citation: recommended.citation),
                  ] else
                    Text(l10n.pathNone, style: text.bodyMedium),
                  if (stage.needsAnswers)
                    Padding(
                      padding: const EdgeInsets.only(top: PankhSpace.xs),
                      child: Text(l10n.pathNeedsAnswers, style: text.bodySmall),
                    ),
                  for (final option in stage.opportunities)
                    Container(
                      width: double.infinity,
                      margin: const EdgeInsets.only(top: PankhSpace.sm + 2),
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: PankhColors.turmericMist,
                        borderRadius: BorderRadius.circular(14),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('${l10n.pathAimFor}: ${option.scheme}', style: text.titleSmall),
                          const SizedBox(height: 2),
                          Text(
                            option.value,
                            style: text.bodyMedium?.copyWith(color: PankhColors.ink),
                          ),
                          if (option.condition != null) ...[
                            const SizedBox(height: PankhSpace.xs),
                            Text(
                              option.condition!,
                              style: text.bodyMedium?.copyWith(color: PankhColors.ink),
                            ),
                          ],
                        ],
                      ),
                    ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// The dashed line between stages, like the joins in a Gond border.
class _DashPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = PankhColors.line
      ..strokeWidth = 2
      ..strokeCap = StrokeCap.round;
    for (var y = 6.0; y < size.height - 4; y += 10) {
      canvas.drawLine(Offset(size.width / 2, y), Offset(size.width / 2, y + 4), paint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
