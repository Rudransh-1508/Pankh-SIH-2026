import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import '../data/models.dart';
import '../l10n/generated/app_localizations.dart';
import '../theme.dart';

/// Next year's application for a Scheme held now, and what to get ready for it.
class RenewalCard extends StatelessWidget {
  const RenewalCard({super.key, required this.plan});

  final RenewalPlan plan;

  String _label(AppLocalizations l10n, RenewalCheck check) => switch (check.id) {
    'promoted' => l10n.renewCheckPromoted,
    'income' => l10n.renewCheckIncome(plan.incomeYear),
    'bank' => l10n.renewCheckBank,
    _ => l10n.renewCheckInstitution,
  };

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final text = Theme.of(context).textTheme;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: PankhColors.card,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: PankhColors.line, width: 1.5),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            plan.continuing
                ? l10n.renewTitle(plan.scheme, plan.nextYear)
                : l10n.renewEnds(plan.scheme),
            style: text.titleMedium,
          ),
          if (!plan.continuing && plan.instead != null) ...[
            const SizedBox(height: PankhSpace.xs),
            Text(
              l10n.renewInstead(plan.nextYear, plan.instead!),
              style: text.bodyMedium?.copyWith(color: PankhColors.peacockDeep),
            ),
          ],
          const SizedBox(height: PankhSpace.sm + 2),
          Text(l10n.renewGetReady, style: text.labelLarge),
          for (final check in plan.checks)
            InkWell(
              borderRadius: BorderRadius.circular(8),
              // Income and bank checks are settled in the Documents tab.
              onTap: !check.done && (check.id == 'income' || check.id == 'bank')
                  ? () => context.go('/wallet')
                  : null,
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 6),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(
                      check.done ? Icons.check_circle_rounded : Icons.radio_button_unchecked,
                      size: 20,
                      color: check.done ? PankhColors.leaf : PankhColors.inkSoft,
                    ),
                    const SizedBox(width: PankhSpace.sm),
                    Expanded(child: Text(_label(l10n, check), style: text.bodyMedium)),
                    if (!check.done && (check.id == 'income' || check.id == 'bank'))
                      const Icon(Icons.chevron_right_rounded, color: PankhColors.inkSoft),
                  ],
                ),
              ),
            ),
          const SizedBox(height: PankhSpace.sm),
          OutlinedButton.icon(
            onPressed: () =>
                launchUrl(Uri.parse(plan.applyUrl), mode: LaunchMode.externalApplication),
            icon: const Icon(Icons.open_in_new_rounded, size: 18),
            label: Text(l10n.renewOpen(plan.applyOn), textAlign: TextAlign.center),
          ),
        ],
      ),
    );
  }
}
