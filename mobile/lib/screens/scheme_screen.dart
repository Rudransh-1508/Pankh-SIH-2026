import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import '../data/models.dart';
import '../l10n/generated/app_localizations.dart';
import '../state/providers.dart';
import '../theme.dart';
import '../widgets/citation_link.dart';
import '../widgets/rule_dots.dart';
import '../widgets/status.dart';

class SchemeScreen extends ConsumerWidget {
  const SchemeScreen({super.key, required this.schemeId});

  final String schemeId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final result = ref.watch(profileProvider).value?.eligibility?.byId(schemeId);
    if (result == null) {
      return Scaffold(
        appBar: AppBar(),
        body: const Center(child: CircularProgressIndicator()),
      );
    }
    final l10n = AppLocalizations.of(context);
    final text = Theme.of(context).textTheme;
    final scheme = result.scheme;
    final english = Localizations.localeOf(context).languageCode == 'en';

    return Scaffold(
      appBar: AppBar(title: Text(scheme.shortName)),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(
          PankhSpace.gutter,
          PankhSpace.xs,
          PankhSpace.gutter,
          PankhSpace.xl,
        ),
        children: [
          Text(scheme.name, style: text.headlineSmall),
          const SizedBox(height: PankhSpace.sm),
          Text(scheme.summary, style: text.bodyLarge?.copyWith(color: PankhColors.inkSoft)),
          const SizedBox(height: PankhSpace.md),
          StatusLine(result: result),
          const SizedBox(height: PankhSpace.sm + 2),
          RuleDots(rules: result.rules, dotSize: 14),
          if (!english) ...[
            const SizedBox(height: PankhSpace.md),
            Text(l10n.rulesInEnglish, style: text.bodySmall),
          ],
          _Section(title: l10n.whyTitle),
          for (final rule in result.rules) _RuleTile(rule: rule),
          _Section(title: l10n.benefitsTitle),
          for (final benefit in scheme.benefits)
            Padding(
              padding: const EdgeInsets.only(bottom: PankhSpace.md),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Padding(
                        padding: EdgeInsets.only(top: 3),
                        child: Icon(Icons.brightness_1, size: 8, color: PankhColors.turmeric),
                      ),
                      const SizedBox(width: PankhSpace.sm + 2),
                      Expanded(child: Text(benefit.text, style: text.bodyLarge)),
                    ],
                  ),
                  Padding(
                    padding: const EdgeInsets.only(left: 18),
                    child: CitationLink(citation: benefit.citation),
                  ),
                ],
              ),
            ),
          _Section(title: l10n.howToApply),
          Text(scheme.systemOfRecord, style: text.bodyLarge),
          if (scheme.applicationWindow != null) ...[
            const SizedBox(height: PankhSpace.xs),
            Text(scheme.applicationWindow!, style: text.bodyMedium),
          ],
          const SizedBox(height: PankhSpace.md),
          OutlinedButton.icon(
            onPressed: () =>
                launchUrl(Uri.parse(scheme.applyUrl), mode: LaunchMode.externalApplication),
            icon: const Icon(Icons.open_in_new_rounded),
            label: Text(l10n.openApplicationSite),
          ),
        ],
      ),
    );
  }
}

class _Section extends StatelessWidget {
  const _Section({required this.title});

  final String title;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(top: PankhSpace.xl, bottom: PankhSpace.md - 4),
    child: Text(title, style: Theme.of(context).textTheme.titleLarge),
  );
}

class _RuleTile extends StatelessWidget {
  const _RuleTile({required this.rule});

  final RuleResult rule;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final text = Theme.of(context).textTheme;
    final (icon, color, label) = outcomeLook(context, rule.outcome);
    return Container(
      margin: const EdgeInsets.only(bottom: PankhSpace.sm + 2),
      padding: const EdgeInsets.fromLTRB(14, 14, 14, 8),
      decoration: BoxDecoration(
        color: PankhColors.card,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: PankhColors.line, width: 1.5),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(icon, color: color, size: 24),
              const SizedBox(width: PankhSpace.sm + 2),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(rule.title, style: text.titleSmall),
                    const SizedBox(height: 2),
                    Text(label, style: text.labelMedium?.copyWith(color: color)),
                  ],
                ),
              ),
            ],
          ),
          if (rule.reason != null) ...[
            const SizedBox(height: PankhSpace.sm + 2),
            Text(rule.reason!, style: text.bodyMedium),
          ],
          if (rule.remedy != null) ...[
            const SizedBox(height: PankhSpace.sm + 2),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: PankhColors.turmericMist,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    l10n.whatYouCanDo,
                    style: text.labelMedium?.copyWith(color: PankhColors.ink),
                  ),
                  const SizedBox(height: 4),
                  Text(rule.remedy!, style: text.bodyMedium?.copyWith(color: PankhColors.ink)),
                ],
              ),
            ),
          ],
          if (rule.outcome == Outcome.unknown && rule.missingFacts.isNotEmpty) ...[
            const SizedBox(height: PankhSpace.xs),
            Align(
              alignment: Alignment.centerLeft,
              child: TextButton(
                onPressed: () => context.push('/questions?fact=${rule.missingFacts.first}'),
                child: Text(l10n.answerThis),
              ),
            ),
          ],
          CitationLink(citation: rule.citation),
        ],
      ),
    );
  }
}
