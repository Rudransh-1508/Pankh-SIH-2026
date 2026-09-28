import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../data/api.dart';
import '../data/models.dart';
import '../l10n/generated/app_localizations.dart';
import '../state/providers.dart';
import '../theme.dart';
import '../widgets/error_view.dart';

/// Asks one Fact per screen, always the one that settles the most, until nothing is left.
///
/// With [fact] set, asks that Fact first (for example to change an earlier answer).
class QuestionsScreen extends ConsumerStatefulWidget {
  const QuestionsScreen({super.key, this.fact});

  final String? fact;

  @override
  ConsumerState<QuestionsScreen> createState() => _QuestionsScreenState();
}

class _QuestionsScreenState extends ConsumerState<QuestionsScreen> {
  final _skipped = <String>{};
  late String? _requested = widget.fact;
  int _answered = 0;
  bool _busy = false;

  String? _current(ProfileState profile) {
    if (_requested != null) return _requested;
    final remaining = profile.eligibility?.nextFacts ?? const <String>[];
    return remaining
        .where((name) => !_skipped.contains(name) && !profile.facts.containsKey(name))
        .firstOrNull;
  }

  int _remaining(ProfileState profile) => (profile.eligibility?.nextFacts ?? const [])
      .where((name) => !_skipped.contains(name) && !profile.facts.containsKey(name))
      .length;

  Future<void> _answer(String name, Object? value) async {
    setState(() => _busy = true);
    try {
      await ref.read(profileProvider.notifier).answer(name, value);
      setState(() {
        _answered++;
        if (_requested == name) _requested = null;
      });
    } on ApiException catch (error) {
      if (mounted) _showError(error);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _skip(String name) => setState(() {
    _skipped.add(name);
    if (_requested == name) _requested = null;
  });

  void _showError(ApiException error) {
    final l10n = AppLocalizations.of(context);
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(error.isOffline ? l10n.networkError : error.message)));
  }

  /// Leave with the Back button: return to wherever the Student came from.
  void _leave() {
    if (context.canPop()) {
      context.pop();
    } else {
      context.go('/discover');
    }
  }

  /// Nothing left to ask. Changing one answer returns to where it was changed; a full run of
  /// questions ends on the results.
  void _finish() {
    if (widget.fact != null && context.canPop()) {
      context.pop();
    } else {
      context.go('/discover');
    }
  }

  @override
  Widget build(BuildContext context) {
    final profile = ref.watch(profileProvider);
    final schema = ref.watch(factSchemaProvider);
    final l10n = AppLocalizations.of(context);

    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          tooltip: l10n.back,
          icon: const Icon(Icons.arrow_back_rounded),
          onPressed: _leave,
        ),
      ),
      body: SafeArea(
        child: switch ((profile, schema)) {
          (AsyncData(value: final p), AsyncData(value: final specs)) => _body(p, specs),
          (AsyncError(:final error), _) || (_, AsyncError(:final error)) => ErrorView(
            error: error,
            onRetry: () {
              ref.invalidate(profileProvider);
              ref.invalidate(factSchemaProvider);
            },
          ),
          _ => const Center(child: CircularProgressIndicator()),
        },
      ),
    );
  }

  Widget _body(ProfileState profile, Map<String, FactSpec> specs) {
    final name = _current(profile);
    if (name == null || specs[name] == null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _finish();
      });
      return const SizedBox.shrink();
    }
    final spec = specs[name]!;
    final language = Localizations.localeOf(context).languageCode;
    final text = Theme.of(context).textTheme;
    final l10n = AppLocalizations.of(context);
    final help = spec.help == null ? null : localised(spec.help!, language);

    return AnimatedSwitcher(
      duration: MediaQuery.disableAnimationsOf(context)
          ? Duration.zero
          : const Duration(milliseconds: 220),
      child: ListView(
        key: ValueKey(name),
        padding: const EdgeInsets.fromLTRB(
          PankhSpace.gutter,
          PankhSpace.xs,
          PankhSpace.gutter,
          PankhSpace.lg,
        ),
        children: [
          _ProgressDots(done: _answered, remaining: _remaining(profile)),
          const SizedBox(height: PankhSpace.lg),
          Text(localised(spec.question, language), style: text.headlineMedium),
          if (help != null) ...[
            const SizedBox(height: PankhSpace.sm),
            Text(help, style: text.bodyLarge?.copyWith(color: PankhColors.inkSoft)),
          ],
          const SizedBox(height: PankhSpace.lg),
          AbsorbPointer(
            absorbing: _busy,
            child: Opacity(
              opacity: _busy ? 0.5 : 1,
              child: _AnswerInput(
                spec: spec,
                current: profile.facts[name],
                language: language,
                onAnswer: (value) => _answer(name, value),
              ),
            ),
          ),
          const SizedBox(height: PankhSpace.md),
          Center(
            child: TextButton(
              onPressed: _busy ? null : () => _skip(name),
              child: Text(l10n.notSure),
            ),
          ),
        ],
      ),
    );
  }
}

/// Answered questions as filled dots, those still to come as hollow ones.
class _ProgressDots extends StatelessWidget {
  const _ProgressDots({required this.done, required this.remaining});

  final int done;
  final int remaining;

  @override
  Widget build(BuildContext context) {
    final total = done + remaining;
    return Semantics(
      label: '$done of $total',
      excludeSemantics: true,
      child: Wrap(
        spacing: 6,
        runSpacing: 6,
        children: [
          for (var i = 0; i < total; i++)
            Container(
              width: 10,
              height: 10,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: i < done ? PankhColors.peacock : null,
                border: i < done ? null : Border.all(color: PankhColors.line, width: 2),
              ),
            ),
        ],
      ),
    );
  }
}

class _AnswerInput extends StatelessWidget {
  const _AnswerInput({
    required this.spec,
    required this.current,
    required this.language,
    required this.onAnswer,
  });

  final FactSpec spec;
  final Object? current;
  final String language;
  final ValueChanged<Object?> onAnswer;

  @override
  Widget build(BuildContext context) {
    if (spec.name == 'admitted_to_top_class_institute') {
      return _TopClassInput(current: current as bool?, onAnswer: onAnswer);
    }
    return switch (spec.kind) {
      FactKind.boolean => _YesNo(current: current as bool?, onAnswer: onAnswer),
      FactKind.choice => _Choices(
        choices: spec.choices,
        current: current as String?,
        language: language,
        onAnswer: onAnswer,
      ),
      FactKind.number => _NumberInput(
        isMoney: spec.name == 'family_income',
        current: current as num?,
        onAnswer: onAnswer,
      ),
      FactKind.date => _DateInput(current: current as String?, onAnswer: onAnswer),
    };
  }
}

class _YesNo extends StatelessWidget {
  const _YesNo({required this.current, required this.onAnswer});

  final bool? current;
  final ValueChanged<Object?> onAnswer;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Row(
      children: [
        Expanded(
          child: _BigChoice(
            label: l10n.yes,
            icon: Icons.check_rounded,
            selected: current == true,
            onTap: () => onAnswer(true),
          ),
        ),
        const SizedBox(width: PankhSpace.md),
        Expanded(
          child: _BigChoice(
            label: l10n.no,
            icon: Icons.close_rounded,
            selected: current == false,
            onTap: () => onAnswer(false),
          ),
        ),
      ],
    );
  }
}

class _BigChoice extends StatelessWidget {
  const _BigChoice({required this.label, required this.selected, required this.onTap, this.icon});

  final String label;
  final IconData? icon;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    return Semantics(
      button: true,
      selected: selected,
      child: Material(
        color: selected ? PankhColors.peacockMist : PankhColors.card,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: BorderSide(
            color: selected ? PankhColors.peacock : PankhColors.line,
            width: selected ? 2 : 1.5,
          ),
        ),
        child: InkWell(
          borderRadius: BorderRadius.circular(16),
          onTap: onTap,
          child: ConstrainedBox(
            constraints: const BoxConstraints(minHeight: 64),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
              child: Row(
                mainAxisAlignment: icon == null
                    ? MainAxisAlignment.start
                    : MainAxisAlignment.center,
                children: [
                  if (icon != null) ...[
                    Icon(icon, color: PankhColors.peacockDeep, size: 26),
                    const SizedBox(width: PankhSpace.sm),
                  ],
                  Flexible(child: Text(label, style: text.titleMedium)),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _Choices extends StatelessWidget {
  const _Choices({
    required this.choices,
    required this.current,
    required this.language,
    required this.onAnswer,
  });

  final List<Choice> choices;
  final String? current;
  final String language;
  final ValueChanged<Object?> onAnswer;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        for (final choice in choices)
          Padding(
            padding: const EdgeInsets.only(bottom: PankhSpace.sm + 2),
            child: _BigChoice(
              label: localised(choice.labels, language),
              selected: current == choice.key,
              onTap: () => onAnswer(choice.key),
            ),
          ),
      ],
    );
  }
}

class _NumberInput extends StatefulWidget {
  const _NumberInput({required this.isMoney, required this.current, required this.onAnswer});

  final bool isMoney;
  final num? current;
  final ValueChanged<Object?> onAnswer;

  @override
  State<_NumberInput> createState() => _NumberInputState();
}

class _NumberInputState extends State<_NumberInput> {
  late final _controller = TextEditingController(text: widget.current?.round().toString() ?? '');
  String? _error;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _submit() {
    final value = num.tryParse(_controller.text);
    final limit = widget.isMoney ? double.infinity : 100;
    if (value == null || value < 0 || value > limit) {
      setState(() => _error = AppLocalizations.of(context).invalidNumber);
      return;
    }
    widget.onAnswer(value);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        TextField(
          controller: _controller,
          autofocus: true,
          keyboardType: TextInputType.numberWithOptions(decimal: !widget.isMoney),
          inputFormatters: [
            FilteringTextInputFormatter.allow(RegExp(widget.isMoney ? r'[0-9]' : r'[0-9.]')),
            LengthLimitingTextInputFormatter(widget.isMoney ? 9 : 5),
          ],
          style: Theme.of(context).textTheme.headlineSmall,
          decoration: InputDecoration(
            prefixText: widget.isMoney ? '₹  ' : null,
            suffixText: widget.isMoney ? null : '%',
            hintText: widget.isMoney ? l10n.amountHint : l10n.percentHint,
            errorText: _error,
          ),
          onChanged: (_) => setState(() => _error = null),
          onSubmitted: (_) => _submit(),
        ),
        const SizedBox(height: PankhSpace.md),
        FilledButton(onPressed: _controller.text.isEmpty ? null : _submit, child: Text(l10n.next)),
      ],
    );
  }
}

/// Day, month and year as three number boxes: easier than a calendar for most people.
class _DateInput extends StatefulWidget {
  const _DateInput({required this.current, required this.onAnswer});

  final String? current;
  final ValueChanged<Object?> onAnswer;

  @override
  State<_DateInput> createState() => _DateInputState();
}

class _DateInputState extends State<_DateInput> {
  late final DateTime? _initial = widget.current == null
      ? null
      : DateTime.tryParse(widget.current!);
  late final _day = TextEditingController(text: _initial?.day.toString() ?? '');
  late final _month = TextEditingController(text: _initial?.month.toString() ?? '');
  late final _year = TextEditingController(text: _initial?.year.toString() ?? '');
  String? _error;

  @override
  void dispose() {
    _day.dispose();
    _month.dispose();
    _year.dispose();
    super.dispose();
  }

  void _submit() {
    final day = int.tryParse(_day.text);
    final month = int.tryParse(_month.text);
    final year = int.tryParse(_year.text);
    final now = DateTime.now();
    if (day == null || month == null || year == null || year < now.year - 80) {
      setState(() => _error = AppLocalizations.of(context).invalidDate);
      return;
    }
    final date = DateTime(year, month, day);
    if (date.day != day || date.month != month || date.isAfter(now)) {
      setState(() => _error = AppLocalizations.of(context).invalidDate);
      return;
    }
    final iso =
        '${year.toString().padLeft(4, '0')}-${month.toString().padLeft(2, '0')}-${day.toString().padLeft(2, '0')}';
    widget.onAnswer(iso);
  }

  Widget _box(TextEditingController controller, String label, int length, {bool last = false}) {
    return TextField(
      controller: controller,
      keyboardType: TextInputType.number,
      textAlign: TextAlign.center,
      textInputAction: last ? TextInputAction.done : TextInputAction.next,
      inputFormatters: [
        FilteringTextInputFormatter.digitsOnly,
        LengthLimitingTextInputFormatter(length),
      ],
      style: Theme.of(context).textTheme.headlineSmall,
      decoration: InputDecoration(labelText: label),
      onChanged: (value) {
        setState(() => _error = null);
        if (value.length == length && !last) FocusScope.of(context).nextFocus();
      },
      onSubmitted: last ? (_) => _submit() : null,
    );
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final filled = _day.text.isNotEmpty && _month.text.isNotEmpty && _year.text.length == 4;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            Expanded(flex: 2, child: _box(_day, l10n.day, 2)),
            const SizedBox(width: PankhSpace.sm),
            Expanded(flex: 2, child: _box(_month, l10n.month, 2)),
            const SizedBox(width: PankhSpace.sm),
            Expanded(flex: 3, child: _box(_year, l10n.year, 4, last: true)),
          ],
        ),
        if (_error != null) ...[
          const SizedBox(height: PankhSpace.sm),
          Text(
            _error!,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: PankhColors.laterite),
          ),
        ],
        const SizedBox(height: PankhSpace.md),
        FilledButton(onPressed: filled ? _submit : null, child: Text(l10n.next)),
      ],
    );
  }
}

/// Yes or no, with the official list one tap away so the Student can check.
class _TopClassInput extends ConsumerStatefulWidget {
  const _TopClassInput({required this.current, required this.onAnswer});

  final bool? current;
  final ValueChanged<Object?> onAnswer;

  @override
  ConsumerState<_TopClassInput> createState() => _TopClassInputState();
}

class _TopClassInputState extends ConsumerState<_TopClassInput> {
  final _query = TextEditingController();
  List<Institute> _results = const [];
  Timer? _debounce;

  @override
  void dispose() {
    _debounce?.cancel();
    _query.dispose();
    super.dispose();
  }

  void _search(String value) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 250), () async {
      if (value.trim().length < 2) {
        setState(() => _results = const []);
        return;
      }
      try {
        final results = await ref.read(apiProvider).searchTopClass(value);
        if (mounted) setState(() => _results = results);
      } on ApiException {
        if (mounted) setState(() => _results = const []);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final text = Theme.of(context).textTheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        TextField(
          controller: _query,
          decoration: InputDecoration(
            labelText: l10n.topClassSearch,
            hintText: l10n.topClassSearchHint,
            prefixIcon: const Icon(Icons.search_rounded),
          ),
          onChanged: _search,
        ),
        for (final institute in _results.take(6))
          ListTile(
            contentPadding: const EdgeInsets.symmetric(horizontal: PankhSpace.xs),
            title: Text(institute.name, style: text.titleSmall),
            subtitle: Text(institute.location, style: text.bodySmall),
            trailing: const Icon(Icons.chevron_right_rounded),
            onTap: () => widget.onAnswer(true),
          ),
        const SizedBox(height: PankhSpace.md),
        _YesNo(current: widget.current, onAnswer: widget.onAnswer),
      ],
    );
  }
}
