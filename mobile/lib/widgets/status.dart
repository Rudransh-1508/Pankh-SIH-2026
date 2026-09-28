import 'package:flutter/material.dart';

import '../data/models.dart';
import '../l10n/generated/app_localizations.dart';
import '../theme.dart';

/// A Scheme's status as an icon plus words, never colour alone.
class StatusLine extends StatelessWidget {
  const StatusLine({super.key, required this.result});

  final SchemeResult result;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final (icon, color, text) = switch (result.status) {
      EligibilityStatus.eligible => (
        Icons.check_circle_rounded,
        PankhColors.leaf,
        l10n.statusEligible,
      ),
      EligibilityStatus.needsInformation => (
        Icons.help_rounded,
        PankhColors.peacockDeep,
        l10n.statusNeedsInformation(result.missingFacts.length),
      ),
      EligibilityStatus.notEligible => (
        Icons.remove_circle_rounded,
        PankhColors.laterite,
        l10n.statusNotEligible,
      ),
    };
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, color: color, size: 20),
        const SizedBox(width: 6),
        Flexible(
          child: Text(text, style: Theme.of(context).textTheme.titleSmall?.copyWith(color: color)),
        ),
      ],
    );
  }
}

/// How one Rule stands, as an icon and a label.
(IconData, Color, String) outcomeLook(BuildContext context, Outcome outcome) {
  final l10n = AppLocalizations.of(context);
  return switch (outcome) {
    Outcome.pass => (Icons.check_circle_rounded, PankhColors.leaf, l10n.ruleMet),
    Outcome.waived => (Icons.do_not_disturb_on_outlined, PankhColors.leaf, l10n.ruleWaived),
    Outcome.unknown => (
      Icons.radio_button_unchecked_rounded,
      PankhColors.inkSoft,
      l10n.ruleUnknown,
    ),
    Outcome.fail => (Icons.cancel_rounded, PankhColors.laterite, l10n.ruleNotMet),
  };
}
