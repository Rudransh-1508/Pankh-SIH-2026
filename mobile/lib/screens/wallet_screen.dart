import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import '../data/api.dart';
import '../data/models.dart';
import '../l10n/generated/app_localizations.dart';
import '../state/providers.dart';
import '../theme.dart';
import '../widgets/answer_text.dart';
import '../widgets/error_view.dart';
import 'wallet_uploads.dart';

/// Documents from DigiLocker and photographed ones, what they confirm, and what still needs
/// attention.
class WalletScreen extends ConsumerWidget {
  const WalletScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final signedIn = ref.watch(sessionProvider) != null;
    final verification = ref.watch(verificationProvider);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.walletTitle)),
      body: !signedIn
          ? _SignInFirst()
          : verification.when(
              data: (value) => _Wallet(verification: value!),
              error: (error, _) =>
                  ErrorView(error: error, onRetry: () => ref.invalidate(verificationProvider)),
              loading: () => const Center(child: CircularProgressIndicator()),
            ),
    );
  }
}

class _SignInFirst extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Padding(
      padding: const EdgeInsets.all(PankhSpace.gutter),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(l10n.signInToLink, style: Theme.of(context).textTheme.bodyLarge),
          const SizedBox(height: PankhSpace.lg),
          FilledButton(onPressed: () => context.push('/sign-in'), child: Text(l10n.signIn)),
        ],
      ),
    );
  }
}

class _Wallet extends ConsumerWidget {
  const _Wallet({required this.verification});

  final Verification verification;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final text = Theme.of(context).textTheme;
    final specs = ref.watch(factSchemaProvider).value ?? const {};
    final language = Localizations.localeOf(context).languageCode;
    final facts = ref.watch(profileProvider).value?.facts ?? const {};
    final confirmed = [
      for (final entry in verification.facts.entries)
        if (entry.value.verified && specs[entry.key] != null) (specs[entry.key]!, entry.value),
    ];

    return RefreshIndicator(
      onRefresh: () async {
        ref.invalidate(verificationProvider);
        ref.invalidate(uploadsProvider);
      },
      child: ListView(
        padding: const EdgeInsets.fromLTRB(
          PankhSpace.gutter,
          PankhSpace.xs,
          PankhSpace.gutter,
          PankhSpace.xl,
        ),
        children: [
          if (verification.linked)
            _Banner(
              icon: Icons.verified_rounded,
              color: PankhColors.leaf,
              background: PankhColors.leafMist,
              text: l10n.linkedAs(verification.identityName!),
            )
          else
            const _LinkCard(),
          if (verification.issues.isNotEmpty) ...[
            _Heading(l10n.needsAttention),
            for (final issue in verification.issues) _IssueCard(issue: issue),
          ],
          if (confirmed.isNotEmpty) ...[
            _Heading(l10n.confirmedTitle),
            for (final (spec, status) in confirmed)
              _ConfirmedRow(
                question: localised(spec.question, language),
                answer: facts[spec.name] == null
                    ? ''
                    : answerText(context, spec, facts[spec.name] as Object),
                source: l10n.confirmedBy(sourceName(status.source)),
              ),
          ],
          if (verification.documents.isNotEmpty) ...[
            _Heading(l10n.documentsTitle),
            for (final document in verification.documents)
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.description_rounded, color: PankhColors.peacock),
                title: Text(document.name, style: text.titleSmall),
                subtitle: Text(document.issuer, style: text.bodySmall),
              ),
          ],
          const PhotoSection(),
          _Heading(l10n.confirmMore),
          _CheckField(
            label: l10n.institutionCode,
            onCheck: (value) => ref.read(apiProvider).verifyInstitution(value),
          ),
          if (verification.linked) ...[
            const SizedBox(height: PankhSpace.md),
            _CheckField(
              label: l10n.netRollNumber,
              onCheck: (value) => ref.read(apiProvider).verifyNet(value),
            ),
            const SizedBox(height: PankhSpace.md),
            _CheckButton(label: l10n.checkBank, onCheck: () => ref.read(apiProvider).verifyBank()),
          ],
        ],
      ),
    );
  }
}

class _LinkCard extends ConsumerStatefulWidget {
  const _LinkCard();

  @override
  ConsumerState<_LinkCard> createState() => _LinkCardState();
}

class _LinkCardState extends ConsumerState<_LinkCard> {
  bool _busy = false;

  Future<void> _link() async {
    setState(() => _busy = true);
    try {
      final url = await ref.read(apiProvider).startDigiLocker();
      await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
    } on ApiException catch (error) {
      if (mounted) showApiError(context, error);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

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
          Text(l10n.walletLinkTitle, style: text.titleMedium),
          const SizedBox(height: PankhSpace.xs),
          Text(l10n.walletLinkBody, style: text.bodyMedium),
          const SizedBox(height: PankhSpace.md),
          FilledButton.icon(
            onPressed: _busy ? null : _link,
            icon: const Icon(Icons.lock_open_rounded),
            label: Text(l10n.linkDigiLocker),
          ),
        ],
      ),
    );
  }
}

class _IssueCard extends StatelessWidget {
  const _IssueCard({required this.issue});

  final VerificationIssue issue;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    final l10n = AppLocalizations.of(context);
    return Container(
      margin: const EdgeInsets.only(bottom: PankhSpace.sm + 2),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: PankhColors.card,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: PankhColors.turmeric, width: 1.5),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Icon(Icons.error_outline_rounded, color: PankhColors.turmeric),
              const SizedBox(width: PankhSpace.sm + 2),
              Expanded(child: Text(issue.message, style: text.bodyLarge)),
            ],
          ),
          if (issue.remedy != null) ...[
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
                  Text(issue.remedy!, style: text.bodyMedium?.copyWith(color: PankhColors.ink)),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _ConfirmedRow extends StatelessWidget {
  const _ConfirmedRow({required this.question, required this.answer, required this.source});

  final String question;
  final String answer;
  final String source;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    return Padding(
      padding: const EdgeInsets.only(bottom: PankhSpace.md),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Padding(
            padding: EdgeInsets.only(top: 2),
            child: Icon(Icons.verified_rounded, color: PankhColors.leaf, size: 22),
          ),
          const SizedBox(width: PankhSpace.sm + 2),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(question, style: text.bodyMedium),
                const SizedBox(height: 2),
                Text(answer, style: text.titleMedium),
                Text(source, style: text.labelMedium?.copyWith(color: PankhColors.leaf)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _CheckField extends ConsumerStatefulWidget {
  const _CheckField({required this.label, required this.onCheck});

  final String label;
  final Future<void> Function(String value) onCheck;

  @override
  ConsumerState<_CheckField> createState() => _CheckFieldState();
}

class _CheckFieldState extends ConsumerState<_CheckField> {
  final _controller = TextEditingController();
  bool _busy = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _check() async {
    setState(() => _busy = true);
    try {
      await widget.onCheck(_controller.text.trim());
      _controller.clear();
      ref.invalidate(verificationProvider);
      await ref.read(profileProvider.notifier).refresh();
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
            controller: _controller,
            textCapitalization: TextCapitalization.characters,
            decoration: InputDecoration(labelText: widget.label),
            onChanged: (_) => setState(() {}),
          ),
        ),
        const SizedBox(width: PankhSpace.sm),
        SizedBox(
          height: 58,
          child: OutlinedButton(
            style: OutlinedButton.styleFrom(minimumSize: const Size(88, 58)),
            onPressed: _busy || _controller.text.trim().isEmpty ? null : _check,
            child: Text(l10n.check),
          ),
        ),
      ],
    );
  }
}

class _CheckButton extends ConsumerStatefulWidget {
  const _CheckButton({required this.label, required this.onCheck});

  final String label;
  final Future<void> Function() onCheck;

  @override
  ConsumerState<_CheckButton> createState() => _CheckButtonState();
}

class _CheckButtonState extends ConsumerState<_CheckButton> {
  bool _busy = false;

  Future<void> _check() async {
    setState(() => _busy = true);
    try {
      await widget.onCheck();
      ref.invalidate(verificationProvider);
      await ref.read(profileProvider.notifier).refresh();
    } on ApiException catch (error) {
      if (mounted) showApiError(context, error);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => OutlinedButton.icon(
    onPressed: _busy ? null : _check,
    icon: const Icon(Icons.account_balance_rounded),
    label: Text(widget.label),
  );
}

class _Heading extends StatelessWidget {
  const _Heading(this.title);

  final String title;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(top: PankhSpace.xl, bottom: PankhSpace.md - 4),
    child: Text(title, style: Theme.of(context).textTheme.titleLarge),
  );
}

class _Banner extends StatelessWidget {
  const _Banner({
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
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
    decoration: BoxDecoration(color: background, borderRadius: BorderRadius.circular(14)),
    child: Row(
      children: [
        Icon(icon, color: color),
        const SizedBox(width: PankhSpace.sm),
        Expanded(child: Text(text, style: Theme.of(context).textTheme.titleSmall)),
      ],
    ),
  );
}

/// Shows an API failure in words the Student can act on.
void showApiError(BuildContext context, ApiException error) {
  final l10n = AppLocalizations.of(context);
  ScaffoldMessenger.of(
    context,
  ).showSnackBar(SnackBar(content: Text(error.isOffline ? l10n.networkError : error.message)));
}
