import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../data/api.dart';
import '../data/models.dart';
import '../l10n/generated/app_localizations.dart';
import '../state/providers.dart';
import '../theme.dart';
import '../widgets/error_view.dart';
import '../widgets/feather_mark.dart';
import '../widgets/language_button.dart';
import '../widgets/rule_dots.dart';
import '../widgets/status.dart';

const _offline = ApiException('offline', isOffline: true);

class DiscoverScreen extends ConsumerWidget {
  const DiscoverScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final profile = ref.watch(profileProvider);
    return Scaffold(
      appBar: AppBar(
        titleSpacing: PankhSpace.gutter,
        title: Row(
          children: [
            const FeatherMark(size: 28),
            const SizedBox(width: PankhSpace.sm),
            Text(
              l10n.appName,
              style: Theme.of(
                context,
              ).textTheme.titleLarge?.copyWith(color: PankhColors.peacockDeep),
            ),
          ],
        ),
        actions: const [
          LanguageButton(),
          _AccountButton(),
          SizedBox(width: PankhSpace.xs),
        ],
      ),
      body: profile.when(
        data: (state) => state.eligibility == null
            ? ErrorView(error: _offline, onRetry: () => ref.invalidate(profileProvider))
            : _Results(state: state),
        error: (error, _) =>
            ErrorView(error: error, onRetry: () => ref.invalidate(profileProvider)),
        loading: () => const Center(child: CircularProgressIndicator()),
      ),
    );
  }
}

class _Results extends ConsumerWidget {
  const _Results({required this.state});

  final ProfileState state;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final text = Theme.of(context).textTheme;
    final eligibility = state.eligibility!;
    final remaining = eligibility.nextFacts.where((f) => !state.facts.containsKey(f)).length;
    final signedIn = ref.watch(sessionProvider) != null;
    final statuses = [for (final result in eligibility.schemes) result.status];
    final eligibleCount = statuses.where((s) => s == EligibilityStatus.eligible).length;
    final allRuledOut = statuses.every((s) => s == EligibilityStatus.notEligible);

    return RefreshIndicator(
      onRefresh: () => ref.read(profileProvider.notifier).refresh(),
      child: ListView(
        padding: const EdgeInsets.fromLTRB(
          PankhSpace.gutter,
          PankhSpace.sm,
          PankhSpace.gutter,
          PankhSpace.xl,
        ),
        children: [
          Text(l10n.discoverTitle, style: text.headlineMedium),
          const SizedBox(height: 2),
          Text(l10n.forAcademicYear(eligibility.academicYearLabel), style: text.bodyMedium),
          const SizedBox(height: PankhSpace.md),
          if (state.isStale) ...[
            _Notice(
              icon: Icons.cloud_off_rounded,
              color: PankhColors.inkSoft,
              background: PankhColors.line.withValues(alpha: 0.6),
              text: l10n.savedResults,
            ),
            const SizedBox(height: PankhSpace.md),
          ],
          if (eligibleCount > 0) ...[
            _Notice(
              icon: Icons.check_circle_rounded,
              color: PankhColors.leaf,
              background: PankhColors.leafMist,
              text: l10n.summaryEligible(eligibleCount),
            ),
            const SizedBox(height: PankhSpace.md),
          ] else if (allRuledOut) ...[
            _Prompt(
              background: PankhColors.card,
              title: l10n.summaryNone,
              body: l10n.summaryNoneBody,
              action: l10n.changeAnswers,
              onPressed: () => context.push('/answers'),
              outlined: true,
            ),
            const SizedBox(height: PankhSpace.md),
          ],
          if (remaining > 0) ...[
            _Prompt(
              background: PankhColors.turmericMist,
              title: l10n.answerMore(remaining),
              action: l10n.continueAnswering,
              onPressed: () => context.push('/questions'),
            ),
            const SizedBox(height: PankhSpace.md),
          ],
          for (final result in eligibility.schemes) ...[
            _SchemeCard(result: result),
            const SizedBox(height: PankhSpace.md - 4),
          ],
          if (!signedIn && state.facts.isNotEmpty) ...[
            const SizedBox(height: PankhSpace.sm),
            _Prompt(
              background: PankhColors.peacockMist,
              title: l10n.saveAnswersTitle,
              body: l10n.saveAnswersBody,
              action: l10n.signIn,
              onPressed: () => context.push('/sign-in'),
            ),
          ],
          const SizedBox(height: PankhSpace.sm),
          Center(
            child: TextButton.icon(
              onPressed: () => context.push('/answers'),
              icon: const Icon(Icons.edit_note_rounded),
              label: Text(l10n.changeAnswers),
            ),
          ),
        ],
      ),
    );
  }
}

class _SchemeCard extends StatelessWidget {
  const _SchemeCard({required this.result});

  final SchemeResult result;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    final dimmed = result.status == EligibilityStatus.notEligible;
    return Material(
      color: PankhColors.card,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(20),
        side: BorderSide(
          color: result.status == EligibilityStatus.eligible ? PankhColors.leaf : PankhColors.line,
          width: result.status == EligibilityStatus.eligible ? 2 : 1.5,
        ),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(20),
        onTap: () => context.push('/schemes/${result.scheme.id}'),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(18, 16, 12, 16),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      result.scheme.shortName,
                      style: text.titleLarge?.copyWith(
                        color: dimmed ? PankhColors.inkSoft : PankhColors.ink,
                      ),
                    ),
                    Text(
                      result.scheme.name,
                      style: text.bodySmall,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: PankhSpace.sm + 2),
                    StatusLine(result: result),
                    const SizedBox(height: PankhSpace.sm + 2),
                    RuleDots(rules: result.rules),
                    if (result.scheme.benefits.isNotEmpty && !dimmed) ...[
                      const SizedBox(height: PankhSpace.sm + 2),
                      Text(
                        result.scheme.benefits.first.text,
                        style: text.bodyMedium,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ],
                ),
              ),
              const Icon(Icons.chevron_right_rounded, color: PankhColors.inkSoft),
            ],
          ),
        ),
      ),
    );
  }
}

class _Prompt extends StatelessWidget {
  const _Prompt({
    required this.background,
    required this.title,
    required this.action,
    required this.onPressed,
    this.body,
    this.outlined = false,
  });

  final bool outlined;
  final Color background;
  final String title;
  final String? body;
  final String action;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(20),
        border: outlined ? Border.all(color: PankhColors.line, width: 1.5) : null,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(title, style: text.titleMedium),
          if (body != null) ...[
            const SizedBox(height: PankhSpace.xs),
            Text(body!, style: text.bodyMedium),
          ],
          const SizedBox(height: PankhSpace.md - 2),
          if (outlined)
            OutlinedButton(onPressed: onPressed, child: Text(action))
          else
            FilledButton(onPressed: onPressed, child: Text(action)),
        ],
      ),
    );
  }
}

class _Notice extends StatelessWidget {
  const _Notice({
    required this.icon,
    required this.color,
    required this.background,
    required this.text,
  });

  final IconData icon;
  final Color color;
  final Color background;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(color: background, borderRadius: BorderRadius.circular(14)),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 20, color: color),
          const SizedBox(width: PankhSpace.sm),
          Expanded(child: Text(text, style: Theme.of(context).textTheme.bodyMedium)),
        ],
      ),
    );
  }
}

class _AccountButton extends ConsumerWidget {
  const _AccountButton();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final phone = ref.watch(sessionProvider);
    if (phone == null) {
      return IconButton(
        tooltip: l10n.signIn,
        icon: const Icon(Icons.account_circle_outlined),
        onPressed: () => context.push('/sign-in'),
      );
    }
    return PopupMenuButton<void>(
      tooltip: l10n.signedInAs(phone),
      icon: const Icon(Icons.account_circle_rounded, color: PankhColors.peacockDeep),
      itemBuilder: (context) => [
        PopupMenuItem(enabled: false, child: Text(l10n.signedInAs(phone))),
        PopupMenuItem(
          onTap: () async {
            await ref.read(sessionProvider.notifier).signOut();
            if (context.mounted) context.go('/welcome');
          },
          child: Text(l10n.signOut),
        ),
      ],
    );
  }
}
