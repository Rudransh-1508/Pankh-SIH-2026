import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/api.dart';
import '../data/models.dart';
import '../l10n/generated/app_localizations.dart';
import '../state/providers.dart';
import '../theme.dart';
import '../widgets/answer_text.dart';
import '../widgets/error_view.dart';
import 'wallet_screen.dart' show showApiError;

/// A Guardian's view of each child's scholarships, and sharing one's own with a Guardian.
class FamilyScreen extends ConsumerWidget {
  const FamilyScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final text = Theme.of(context).textTheme;
    return Scaffold(
      appBar: AppBar(title: Text(l10n.familyTitle)),
      body: ref
          .watch(familyProvider)
          .when(
            error: (error, _) =>
                ErrorView(error: error, onRetry: () => ref.invalidate(familyProvider)),
            loading: () => const Center(child: CircularProgressIndicator()),
            data: (family) {
              final children = family['children'] as List;
              final guardians = family['guardians'] as List;
              return RefreshIndicator(
                onRefresh: () async => ref.invalidate(familyProvider),
                child: ListView(
                  padding: const EdgeInsets.fromLTRB(
                    PankhSpace.gutter,
                    PankhSpace.xs,
                    PankhSpace.gutter,
                    PankhSpace.xl,
                  ),
                  children: [
                    Text(l10n.familyChildren, style: text.titleLarge),
                    const SizedBox(height: PankhSpace.sm + 2),
                    if (children.isEmpty) Text(l10n.familyNoChildren, style: text.bodyMedium),
                    for (final child in children) _ChildCard(child: child as Json),
                    const SizedBox(height: PankhSpace.md),
                    const _AddChild(),
                    const SizedBox(height: PankhSpace.xl),
                    const _ShareCode(),
                    if (guardians.isNotEmpty) ...[
                      const SizedBox(height: PankhSpace.lg),
                      Text(l10n.familyFollowers, style: text.titleMedium),
                      for (final guardian in guardians)
                        ListTile(
                          contentPadding: EdgeInsets.zero,
                          leading: const Icon(Icons.person_rounded, color: PankhColors.peacock),
                          title: Text((guardian as Json)['phone'] as String),
                          trailing: TextButton(
                            onPressed: () async {
                              await ref
                                  .read(apiProvider)
                                  .endFamilyLink(guardian['link_id'] as String);
                              ref.invalidate(familyProvider);
                            },
                            child: Text(l10n.familyStop),
                          ),
                        ),
                    ],
                  ],
                ),
              );
            },
          ),
    );
  }
}

class _ChildCard extends ConsumerWidget {
  const _ChildCard({required this.child});

  final Json child;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final text = Theme.of(context).textTheme;
    final eligible = [for (final s in child['eligible'] as List) s as String];
    final applications = child['applications'] as List;
    final issues = child['issues'] as int;
    return Container(
      margin: const EdgeInsets.only(bottom: PankhSpace.sm + 2),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: PankhColors.card,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: issues > 0 ? PankhColors.turmeric : PankhColors.line, width: 1.5),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(child: Text(child['name'] as String, style: text.titleMedium)),
              IconButton(
                tooltip: l10n.familyStop,
                icon: const Icon(Icons.close_rounded, color: PankhColors.inkSoft),
                onPressed: () async {
                  await ref.read(apiProvider).endFamilyLink(child['link_id'] as String);
                  ref.invalidate(familyProvider);
                },
              ),
            ],
          ),
          if (eligible.isNotEmpty)
            Text(
              l10n.familyQualifies(eligible.join(', ')),
              style: text.titleSmall?.copyWith(color: PankhColors.leaf),
            ),
          if (child['answers_needed'] == true) Text(l10n.familyNeedsAnswers, style: text.bodySmall),
          for (final app in applications)
            Padding(
              padding: const EdgeInsets.only(top: PankhSpace.sm),
              child: Row(
                children: [
                  Icon(
                    (app as Json)['needs_action'] == true
                        ? Icons.error_outline_rounded
                        : Icons.assignment_turned_in_outlined,
                    size: 20,
                    color: app['needs_action'] == true ? PankhColors.laterite : PankhColors.peacock,
                  ),
                  const SizedBox(width: PankhSpace.sm),
                  Expanded(
                    child: Text(
                      [
                        app['scheme'] as String,
                        (app['stage'] as String).replaceAll('_', ' '),
                        if ((app['received'] as int) > 0)
                          '₹ ${indianDigits(app['received'] as int)}',
                      ].join(' · '),
                      style: text.bodyMedium,
                    ),
                  ),
                ],
              ),
            ),
          if (issues > 0)
            Padding(
              padding: const EdgeInsets.only(top: PankhSpace.sm),
              child: Text(
                l10n.familyIssues(issues),
                style: text.titleSmall?.copyWith(color: PankhColors.laterite),
              ),
            ),
        ],
      ),
    );
  }
}

class _AddChild extends ConsumerStatefulWidget {
  const _AddChild();

  @override
  ConsumerState<_AddChild> createState() => _AddChildState();
}

class _AddChildState extends ConsumerState<_AddChild> {
  final _code = TextEditingController();
  bool _busy = false;

  @override
  void dispose() {
    _code.dispose();
    super.dispose();
  }

  Future<void> _add() async {
    setState(() => _busy = true);
    try {
      await ref.read(apiProvider).acceptFamilyInvite(_code.text);
      _code.clear();
      ref.invalidate(familyProvider);
    } on ApiException catch (error) {
      if (mounted) showApiError(context, error);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Row(
      children: [
        Expanded(
          child: TextField(
            controller: _code,
            textCapitalization: TextCapitalization.characters,
            inputFormatters: [LengthLimitingTextInputFormatter(9)],
            decoration: InputDecoration(labelText: l10n.familyCodeLabel),
            onChanged: (_) => setState(() {}),
          ),
        ),
        const SizedBox(width: PankhSpace.sm),
        SizedBox(
          height: 58,
          child: FilledButton(
            style: FilledButton.styleFrom(minimumSize: const Size(96, 58)),
            onPressed: _busy || _code.text.replaceAll(' ', '').length < 8 ? null : _add,
            child: Text(l10n.familyAddButton),
          ),
        ),
      ],
    );
  }
}

class _ShareCode extends ConsumerStatefulWidget {
  const _ShareCode();

  @override
  ConsumerState<_ShareCode> createState() => _ShareCodeState();
}

class _ShareCodeState extends ConsumerState<_ShareCode> {
  String? _code;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final text = Theme.of(context).textTheme;
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: PankhColors.peacockMist,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(l10n.familyShareTitle, style: text.titleMedium),
          const SizedBox(height: PankhSpace.xs),
          Text(l10n.familyShareBody, style: text.bodyMedium),
          const SizedBox(height: PankhSpace.md),
          if (_code != null)
            SelectableText(
              _code!,
              textAlign: TextAlign.center,
              style: text.displaySmall?.copyWith(letterSpacing: 4, color: PankhColors.peacockDeep),
            )
          else
            OutlinedButton(
              onPressed: () async {
                try {
                  final code = await ref.read(apiProvider).familyInvite();
                  setState(() => _code = code);
                } on ApiException catch (error) {
                  if (context.mounted) showApiError(context, error);
                }
              },
              child: Text(l10n.familyShareButton),
            ),
        ],
      ),
    );
  }
}
