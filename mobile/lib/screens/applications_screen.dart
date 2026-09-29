import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../data/models.dart';
import '../l10n/generated/app_localizations.dart';
import '../state/providers.dart';
import '../theme.dart';
import '../widgets/answer_text.dart';
import '../widgets/error_view.dart';
import 'grievance_section.dart';
import 'renewal_card.dart';

String rupees(int amount) => '₹ ${indianDigits(amount)}';

String _who(AppLocalizations l10n, String who) => switch (who) {
  'institute' => l10n.whoInstitute,
  'district' => l10n.whoDistrict,
  'state' => l10n.whoState,
  'sanctioning authority' => l10n.whoSanctioning,
  'university' => l10n.whoUniversity,
  'ministry' => l10n.whoMinistry,
  _ => who,
};

/// Every application across the three systems of record, and where each one stands.
class ApplicationsScreen extends ConsumerWidget {
  const ApplicationsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final signedIn = ref.watch(sessionProvider) != null;
    final applications = ref.watch(applicationsProvider);
    return Scaffold(
      appBar: AppBar(
        titleSpacing: PankhSpace.gutter,
        title: Text(l10n.applicationsTitle, style: Theme.of(context).textTheme.titleLarge),
      ),
      body: !signedIn
          ? _Prompt(text: l10n.signInToLink, action: l10n.signIn, route: '/sign-in')
          : applications.when(
              data: (value) => _List(applications: value!),
              error: (error, _) =>
                  ErrorView(error: error, onRetry: () => ref.invalidate(applicationsProvider)),
              loading: () => const Center(child: CircularProgressIndicator()),
            ),
    );
  }
}

class _Prompt extends StatelessWidget {
  const _Prompt({required this.text, required this.action, required this.route});

  final String text;
  final String action;
  final String route;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.all(PankhSpace.gutter),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(text, style: Theme.of(context).textTheme.bodyLarge),
        const SizedBox(height: PankhSpace.lg),
        FilledButton(
          // Tabs are switched to; everything else opens on top.
          onPressed: () => route == '/wallet' ? context.go(route) : context.push(route),
          child: Text(action),
        ),
      ],
    ),
  );
}

class _List extends ConsumerWidget {
  const _List({required this.applications});

  final Applications applications;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final text = Theme.of(context).textTheme;
    if (!applications.linked) {
      return _Prompt(
        text: l10n.applicationsNeedLink,
        action: l10n.linkDigiLocker,
        route: '/wallet',
      );
    }
    final renewals = ref.watch(renewalsProvider).value ?? const [];
    return RefreshIndicator(
      onRefresh: () async {
        ref.invalidate(applicationsProvider);
        ref.invalidate(renewalsProvider);
        ref.invalidate(grievancesProvider);
      },
      child: ListView(
        padding: const EdgeInsets.fromLTRB(
          PankhSpace.gutter,
          PankhSpace.xs,
          PankhSpace.gutter,
          PankhSpace.xl,
        ),
        children: [
          if (applications.staleSources.isNotEmpty)
            _Note(
              icon: Icons.cloud_off_rounded,
              text: l10n.applicationsStale(applications.staleSources.join(', ')),
            ),
          if (applications.warning != null)
            _Note(icon: Icons.warning_amber_rounded, text: applications.warning!),
          if (applications.items.isEmpty)
            Padding(
              padding: const EdgeInsets.only(top: PankhSpace.xl),
              child: Text(l10n.applicationsNone, style: text.bodyLarge),
            ),
          for (final application in applications.items)
            Padding(
              padding: const EdgeInsets.only(bottom: PankhSpace.md - 4),
              child: _ApplicationCard(application: application),
            ),
          const GrievanceSection(),
          if (renewals.isNotEmpty) ...[
            Padding(
              padding: const EdgeInsets.only(top: PankhSpace.lg, bottom: PankhSpace.sm + 2),
              child: Text(l10n.renewHeading, style: text.titleLarge),
            ),
            for (final plan in renewals)
              Padding(
                padding: const EdgeInsets.only(bottom: PankhSpace.md - 4),
                child: RenewalCard(plan: plan),
              ),
          ],
        ],
      ),
    );
  }
}

class _ApplicationCard extends StatelessWidget {
  const _ApplicationCard({required this.application});

  final TrackedApplication application;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    final l10n = AppLocalizations.of(context);
    final problem =
        application.deficiency ??
        application.instalments.map((i) => i.problem).whereType<Problem>().firstOrNull;
    return Material(
      color: PankhColors.card,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(20),
        side: BorderSide(
          color: application.needsAction ? PankhColors.turmeric : PankhColors.line,
          width: 1.5,
        ),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(20),
        onTap: () => Navigator.of(context).push(
          MaterialPageRoute<void>(builder: (_) => ApplicationScreen(application: application)),
        ),
        child: Padding(
          padding: const EdgeInsets.all(18),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(application.schemeName, style: text.titleMedium),
              Text(
                '${application.sourceSystem} · ${application.externalId} · ${application.academicYear}',
                style: text.bodySmall,
              ),
              const SizedBox(height: PankhSpace.md),
              StageSteps(stage: application.stage),
              const SizedBox(height: PankhSpace.md - 4),
              _WaitingLine(application: application),
              if (problem != null) ...[
                const SizedBox(height: PankhSpace.sm + 2),
                ProblemBox(problem: problem),
              ],
              if (application.received > 0) ...[
                const SizedBox(height: PankhSpace.sm + 2),
                Text(
                  l10n.received(rupees(application.received)),
                  style: text.titleSmall?.copyWith(color: PankhColors.leaf),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

/// Applied, verified, sanctioned, money: the four steps every scheme shares.
class StageSteps extends StatelessWidget {
  const StageSteps({super.key, required this.stage});

  final ApplicationStage stage;

  int get _reached => switch (stage) {
    ApplicationStage.submitted || ApplicationStage.rejected => 0,
    ApplicationStage.underVerification => 1,
    ApplicationStage.sanctioned => 2,
    ApplicationStage.disbursing => 3,
    ApplicationStage.closed => 4,
  };

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final text = Theme.of(context).textTheme;
    final labels = [l10n.stepApplied, l10n.stepVerified, l10n.stepSanctioned, l10n.stepPaid];
    return Row(
      children: [
        for (var i = 0; i < labels.length; i++)
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  height: 6,
                  margin: const EdgeInsets.only(right: 4),
                  decoration: BoxDecoration(
                    color: i < _reached
                        ? PankhColors.leaf
                        : i == _reached
                        ? PankhColors.peacock
                        : PankhColors.line,
                    borderRadius: BorderRadius.circular(3),
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  labels[i],
                  style: text.labelMedium?.copyWith(
                    color: i <= _reached ? PankhColors.ink : PankhColors.inkSoft,
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }
}

class _WaitingLine extends StatelessWidget {
  const _WaitingLine({required this.application});

  final TrackedApplication application;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final text = Theme.of(context).textTheme;
    final who = application.waitingOn;
    if (who == null) return Text(application.statusText, style: text.bodyMedium);
    if (who == 'you') {
      return Text(l10n.waitingOnYou, style: text.titleSmall?.copyWith(color: PankhColors.laterite));
    }
    final days = application.daysWaiting;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          days == null ? application.statusText : l10n.waitingOn(_who(l10n, who), days),
          style: text.titleSmall?.copyWith(
            color: application.stalled ? PankhColors.laterite : PankhColors.ink,
          ),
        ),
        if (application.stalled) Text(l10n.stalledNote, style: text.bodySmall),
      ],
    );
  }
}

class ProblemBox extends StatelessWidget {
  const ProblemBox({super.key, required this.problem});

  final Problem problem;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    final l10n = AppLocalizations.of(context);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: PankhColors.turmericMist,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(problem.reason, style: text.bodyMedium?.copyWith(color: PankhColors.ink)),
          const SizedBox(height: PankhSpace.sm),
          Text(l10n.whatYouCanDo, style: text.labelMedium?.copyWith(color: PankhColors.ink)),
          const SizedBox(height: 2),
          Text(problem.fix, style: text.bodyMedium?.copyWith(color: PankhColors.ink)),
        ],
      ),
    );
  }
}

class _Note extends StatelessWidget {
  const _Note({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) => Container(
    margin: const EdgeInsets.only(bottom: PankhSpace.md),
    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
    decoration: BoxDecoration(
      color: PankhColors.turmericMist,
      borderRadius: BorderRadius.circular(14),
    ),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 20, color: PankhColors.ink),
        const SizedBox(width: PankhSpace.sm),
        Expanded(child: Text(text, style: Theme.of(context).textTheme.bodyMedium)),
      ],
    ),
  );
}

/// One application in full: its history and every payment, traced.
class ApplicationScreen extends StatelessWidget {
  const ApplicationScreen({super.key, required this.application});

  final TrackedApplication application;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final text = Theme.of(context).textTheme;
    return Scaffold(
      appBar: AppBar(title: Text(application.sourceSystem)),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(
          PankhSpace.gutter,
          PankhSpace.xs,
          PankhSpace.gutter,
          PankhSpace.xl,
        ),
        children: [
          Text(application.schemeName, style: text.headlineSmall),
          Text('${application.externalId} · ${application.academicYear}', style: text.bodySmall),
          const SizedBox(height: PankhSpace.lg),
          StageSteps(stage: application.stage),
          const SizedBox(height: PankhSpace.md),
          _WaitingLine(application: application),
          if (application.deficiency != null) ...[
            const SizedBox(height: PankhSpace.md),
            ProblemBox(problem: application.deficiency!),
          ],
          if (application.instalments.isNotEmpty) ...[
            _Section(l10n.paymentsTitle),
            for (final instalment in application.instalments) _InstalmentRow(instalment),
          ],
          if (application.timeline.isNotEmpty) ...[
            _Section(l10n.historyTitle),
            for (final (label, on) in application.timeline.reversed)
              Padding(
                padding: const EdgeInsets.only(bottom: PankhSpace.sm + 2),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Padding(
                      padding: EdgeInsets.only(top: 6),
                      child: Icon(Icons.circle, size: 8, color: PankhColors.peacock),
                    ),
                    const SizedBox(width: PankhSpace.sm + 2),
                    Expanded(child: Text(label, style: text.bodyLarge)),
                    Text(on.split('-').reversed.join('/'), style: text.bodySmall),
                  ],
                ),
              ),
          ],
        ],
      ),
    );
  }
}

class _Section extends StatelessWidget {
  const _Section(this.title);

  final String title;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(top: PankhSpace.xl, bottom: PankhSpace.md - 4),
    child: Text(title, style: Theme.of(context).textTheme.titleLarge),
  );
}

class _InstalmentRow extends StatelessWidget {
  const _InstalmentRow(this.instalment);

  final Instalment instalment;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final text = Theme.of(context).textTheme;
    final (icon, color, label) = switch (instalment.status) {
      InstalmentStatus.credited => (
        Icons.check_circle_rounded,
        PankhColors.leaf,
        l10n.paymentCredited,
      ),
      InstalmentStatus.pending => (
        Icons.schedule_rounded,
        PankhColors.peacock,
        l10n.paymentPending,
      ),
      InstalmentStatus.onHold => (
        Icons.pause_circle_rounded,
        PankhColors.turmeric,
        l10n.paymentOnHold,
      ),
      InstalmentStatus.failed => (Icons.cancel_rounded, PankhColors.laterite, l10n.paymentFailed),
    };
    return Container(
      margin: const EdgeInsets.only(bottom: PankhSpace.sm + 2),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: PankhColors.card,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: PankhColors.line, width: 1.5),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: color),
              const SizedBox(width: PankhSpace.sm + 2),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '${l10n.instalment(instalment.number)} · ${rupees(instalment.amount)}',
                      style: text.titleSmall,
                    ),
                    Text(
                      [
                        label,
                        if (instalment.date != null) instalment.date!.split('-').reversed.join('/'),
                      ].join(' · '),
                      style: text.labelMedium?.copyWith(color: color),
                    ),
                  ],
                ),
              ),
            ],
          ),
          if (instalment.problem != null) ...[
            const SizedBox(height: PankhSpace.sm + 2),
            ProblemBox(problem: instalment.problem!),
          ],
        ],
      ),
    );
  }
}
