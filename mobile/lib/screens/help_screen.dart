import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/api.dart';
import '../data/models.dart';
import '../l10n/generated/app_localizations.dart';
import '../state/providers.dart';
import '../theme.dart';
import '../widgets/error_view.dart';
import 'sign_in_screens.dart' show DemoCodeNote;
import 'wallet_screen.dart' show showApiError;

/// For facilitators: register, add Students with their consent, and answer questions for them.
class HelpScreen extends ConsumerWidget {
  const HelpScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final text = Theme.of(context).textTheme;
    return Scaffold(
      appBar: AppBar(title: Text(l10n.helpTitle)),
      body: ref
          .watch(facilitatorProvider)
          .when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (error, _) =>
                ErrorView(error: error, onRetry: () => ref.invalidate(facilitatorProvider)),
            data: (data) {
              final me = data?.me;
              return ListView(
                padding: const EdgeInsets.fromLTRB(
                  PankhSpace.gutter,
                  PankhSpace.xs,
                  PankhSpace.gutter,
                  PankhSpace.xl,
                ),
                children: [
                  if (me == null) ...[
                    Text(l10n.helpIntro, style: text.bodyLarge),
                    const SizedBox(height: PankhSpace.lg),
                    const _Register(),
                  ] else if (me['status'] == 'pending')
                    _Notice(icon: Icons.hourglass_top_rounded, text: l10n.helpPending)
                  else if (me['status'] == 'rejected')
                    _Notice(icon: Icons.block_rounded, text: l10n.helpRejected)
                  else ...[
                    for (final student in data!.students.cast<Json>())
                      _StudentCard(student: student),
                    if (data.students.isEmpty)
                      Padding(
                        padding: const EdgeInsets.only(bottom: PankhSpace.md),
                        child: Text(l10n.helpNone, style: text.bodyLarge),
                      ),
                    const SizedBox(height: PankhSpace.md),
                    const _AddStudent(),
                  ],
                ],
              );
            },
          ),
    );
  }
}

class _Notice extends StatelessWidget {
  const _Notice({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(16),
    decoration: BoxDecoration(
      color: PankhColors.peacockMist,
      borderRadius: BorderRadius.circular(16),
    ),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, color: PankhColors.peacockDeep),
        const SizedBox(width: PankhSpace.sm),
        Expanded(child: Text(text, style: Theme.of(context).textTheme.bodyLarge)),
      ],
    ),
  );
}

class _Register extends ConsumerStatefulWidget {
  const _Register();

  @override
  ConsumerState<_Register> createState() => _RegisterState();
}

class _RegisterState extends ConsumerState<_Register> {
  final _fields = {
    'name': TextEditingController(),
    'organisation': TextEditingController(),
    'state': TextEditingController(),
    'district': TextEditingController(),
  };
  bool _busy = false;

  @override
  void dispose() {
    for (final field in _fields.values) {
      field.dispose();
    }
    super.dispose();
  }

  bool get _complete => _fields.values.every((f) => f.text.trim().length >= 2);

  Future<void> _submit() async {
    setState(() => _busy = true);
    try {
      await ref.read(apiProvider).registerFacilitator({
        for (final entry in _fields.entries) entry.key: entry.value.text.trim(),
      });
      ref.invalidate(facilitatorProvider);
    } on ApiException catch (error) {
      if (mounted) showApiError(context, error);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final labels = {
      'name': l10n.helpName,
      'organisation': l10n.helpOrganisation,
      'state': l10n.helpState,
      'district': l10n.helpDistrict,
    };
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (final entry in _fields.entries)
          Padding(
            padding: const EdgeInsets.only(bottom: PankhSpace.sm + 2),
            child: TextField(
              controller: entry.value,
              textCapitalization: TextCapitalization.words,
              decoration: InputDecoration(labelText: labels[entry.key]),
              onChanged: (_) => setState(() {}),
            ),
          ),
        const SizedBox(height: PankhSpace.sm),
        FilledButton(
          onPressed: _busy || !_complete ? null : _submit,
          child: Text(l10n.helpRegister),
        ),
      ],
    );
  }
}

class _AddStudent extends ConsumerStatefulWidget {
  const _AddStudent();

  @override
  ConsumerState<_AddStudent> createState() => _AddStudentState();
}

class _AddStudentState extends ConsumerState<_AddStudent> {
  final _phone = TextEditingController();
  final _code = TextEditingController();
  bool _sent = false;
  bool _busy = false;
  String? _demoCode;

  @override
  void dispose() {
    _phone.dispose();
    _code.dispose();
    super.dispose();
  }

  Future<void> _run(Future<void> Function() action) async {
    setState(() => _busy = true);
    try {
      await action();
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
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: PankhColors.card,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: PankhColors.line, width: 1.5),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(l10n.helpAddTitle, style: text.titleMedium),
          const SizedBox(height: PankhSpace.xs),
          Text(l10n.helpAddBody, style: text.bodySmall),
          const SizedBox(height: PankhSpace.md),
          TextField(
            controller: _phone,
            enabled: !_sent,
            keyboardType: TextInputType.phone,
            inputFormatters: [FilteringTextInputFormatter.digitsOnly],
            maxLength: 10,
            decoration: InputDecoration(labelText: l10n.helpPhone, counterText: ''),
            onChanged: (_) => setState(() {}),
          ),
          if (_sent) ...[
            if (_demoCode != null) ...[
              const SizedBox(height: PankhSpace.sm + 2),
              DemoCodeNote(code: _demoCode!),
            ],
            const SizedBox(height: PankhSpace.sm + 2),
            TextField(
              controller: _code,
              keyboardType: TextInputType.number,
              inputFormatters: [FilteringTextInputFormatter.digitsOnly],
              maxLength: 6,
              decoration: InputDecoration(labelText: l10n.helpCode, counterText: ''),
              onChanged: (_) => setState(() {}),
            ),
          ],
          const SizedBox(height: PankhSpace.sm + 2),
          if (!_sent)
            FilledButton(
              onPressed: _busy || _phone.text.length != 10
                  ? null
                  : () => _run(() async {
                      final demo = await ref.read(apiProvider).requestConsent(_phone.text);
                      setState(() {
                        _sent = true;
                        _demoCode = demo;
                      });
                    }),
              child: Text(l10n.helpSend),
            )
          else
            FilledButton(
              onPressed: _busy || _code.text.length != 6
                  ? null
                  : () => _run(() async {
                      await ref.read(apiProvider).confirmConsent(_phone.text, _code.text);
                      _phone.clear();
                      _code.clear();
                      setState(() => _sent = false);
                      ref.invalidate(facilitatorProvider);
                    }),
              child: Text(l10n.helpConfirm),
            ),
        ],
      ),
    );
  }
}

class _StudentCard extends ConsumerStatefulWidget {
  const _StudentCard({required this.student});

  final Json student;

  @override
  ConsumerState<_StudentCard> createState() => _StudentCardState();
}

class _StudentCardState extends ConsumerState<_StudentCard> {
  final _value = TextEditingController();
  bool _busy = false;

  @override
  void dispose() {
    _value.dispose();
    super.dispose();
  }

  Future<void> _answer(String fact, Object value) async {
    setState(() => _busy = true);
    try {
      final language = Localizations.localeOf(context).languageCode;
      await ref.read(apiProvider).answerFor(widget.student['student_id'] as String, {
        fact: value,
      }, language);
      _value.clear();
      ref.invalidate(facilitatorProvider);
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
    final student = widget.student;
    final eligible = [for (final s in student['eligible'] as List) s as String];
    final question = student['next_question'] as Json?;
    return Container(
      margin: const EdgeInsets.only(bottom: PankhSpace.sm + 2),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: PankhColors.card,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: PankhColors.line, width: 1.5),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text('${student['name']}', style: text.titleMedium),
          Text(l10n.helpAnswersNeeded(student['answers_needed'] as int), style: text.bodySmall),
          if (eligible.isNotEmpty) ...[
            const SizedBox(height: PankhSpace.xs),
            Text(
              l10n.helpQualifies(eligible.join(', ')),
              style: text.titleSmall?.copyWith(color: PankhColors.leaf),
            ),
          ],
          if (question != null) ...[
            const SizedBox(height: PankhSpace.md),
            Text(l10n.helpAsk, style: text.labelLarge),
            const SizedBox(height: 2),
            Text(question['question'] as String, style: text.bodyLarge),
            const SizedBox(height: PankhSpace.sm),
            _answerInput(l10n, question),
          ],
        ],
      ),
    );
  }

  Widget _answerInput(AppLocalizations l10n, Json question) {
    final fact = question['fact'] as String;
    switch (question['kind']) {
      case 'boolean':
        return Row(
          children: [
            Expanded(
              child: OutlinedButton(
                onPressed: _busy ? null : () => _answer(fact, true),
                child: Text(l10n.helpYes),
              ),
            ),
            const SizedBox(width: PankhSpace.sm),
            Expanded(
              child: OutlinedButton(
                onPressed: _busy ? null : () => _answer(fact, false),
                child: Text(l10n.helpNo),
              ),
            ),
          ],
        );
      case 'choice':
        return Wrap(
          spacing: PankhSpace.sm,
          runSpacing: PankhSpace.sm,
          children: [
            for (final choice in (question['choices'] as List).cast<Json>())
              ActionChip(
                label: Text(choice['label'] as String),
                onPressed: _busy ? null : () => _answer(fact, choice['key'] as String),
              ),
          ],
        );
      default:
        final isDate = question['kind'] == 'date';
        return Row(
          children: [
            Expanded(
              child: TextField(
                controller: _value,
                keyboardType: isDate ? TextInputType.datetime : TextInputType.number,
                decoration: InputDecoration(hintText: isDate ? 'YYYY-MM-DD' : null),
                onChanged: (_) => setState(() {}),
              ),
            ),
            const SizedBox(width: PankhSpace.sm),
            FilledButton(
              onPressed: _busy || _value.text.trim().isEmpty
                  ? null
                  : () => _answer(
                      fact,
                      isDate ? _value.text.trim() : num.tryParse(_value.text.trim()) ?? 0,
                    ),
              child: Text(l10n.helpSave),
            ),
          ],
        );
    }
  }
}
