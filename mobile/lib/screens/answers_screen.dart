import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../data/models.dart';
import '../l10n/generated/app_localizations.dart';
import '../state/providers.dart';
import '../theme.dart';

/// Every answer given so far. Tapping one asks that question again.
class AnswersScreen extends ConsumerWidget {
  const AnswersScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final text = Theme.of(context).textTheme;
    final facts = ref.watch(profileProvider).value?.facts ?? const {};
    final specs = ref.watch(factSchemaProvider).value ?? const {};
    final language = Localizations.localeOf(context).languageCode;

    String display(FactSpec spec, Object value) => switch (spec.kind) {
      FactKind.boolean => value == true ? l10n.yes : l10n.no,
      FactKind.choice => localised(spec.choices.firstWhere((c) => c.key == value).labels, language),
      FactKind.number => spec.name == 'family_income' ? '₹ ${(value as num).round()}' : '$value%',
      FactKind.date => value.toString().split('-').reversed.join(' / '),
    };

    final answered = [
      for (final name in specs.keys)
        if (facts.containsKey(name)) specs[name]!,
    ];
    return Scaffold(
      appBar: AppBar(title: Text(l10n.changeAnswers)),
      body: ListView.separated(
        padding: const EdgeInsets.symmetric(vertical: PankhSpace.sm),
        itemCount: answered.length,
        separatorBuilder: (_, _) =>
            const Divider(indent: PankhSpace.gutter, endIndent: PankhSpace.gutter),
        itemBuilder: (context, index) {
          final spec = answered[index];
          return ListTile(
            contentPadding: const EdgeInsets.symmetric(horizontal: PankhSpace.gutter, vertical: 4),
            title: Text(localised(spec.question, language), style: text.bodyMedium),
            subtitle: Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text(display(spec, facts[spec.name] as Object), style: text.titleMedium),
            ),
            trailing: const Icon(Icons.edit_rounded, color: PankhColors.peacockDeep),
            onTap: () => context.push('/questions?fact=${spec.name}'),
          );
        },
      ),
    );
  }
}
