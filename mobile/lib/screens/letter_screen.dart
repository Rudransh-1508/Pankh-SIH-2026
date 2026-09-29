import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/models.dart';
import '../l10n/generated/app_localizations.dart';
import '../state/providers.dart';
import '../theme.dart';
import '../widgets/error_view.dart';

typedef _LetterRequest = ({String kind, String language, Map<String, String> context});

final _letterProvider = FutureProvider.autoDispose.family<Json, _LetterRequest>(
  (ref, request) => ref.read(apiProvider).letter(request.kind, request.language, request.context),
);

/// A request letter written from the Student's records, to copy, print or read out at an office.
class LetterScreen extends ConsumerStatefulWidget {
  const LetterScreen({super.key, required this.kind, required this.context});

  final String kind;
  final Map<String, String> context;

  @override
  ConsumerState<LetterScreen> createState() => _LetterScreenState();
}

class _LetterScreenState extends ConsumerState<LetterScreen> {
  String? _language;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final text = Theme.of(context).textTheme;
    final language = _language ?? Localizations.localeOf(context).languageCode;
    final request = (kind: widget.kind, language: language, context: widget.context);
    final letter = ref.watch(_letterProvider(request));
    return Scaffold(
      appBar: AppBar(title: Text(l10n.letterTitle)),
      body: letter.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) =>
            ErrorView(error: error, onRetry: () => ref.invalidate(_letterProvider(request))),
        data: (letter) {
          final full = [
            letter['to'],
            l10n.letterSubject(letter['subject'] as String),
            letter['body'],
            letter['closing'],
          ].join('\n\n');
          return ListView(
            padding: const EdgeInsets.fromLTRB(
              PankhSpace.gutter,
              PankhSpace.xs,
              PankhSpace.gutter,
              PankhSpace.xl,
            ),
            children: [
              SegmentedButton<String>(
                segments: const [
                  ButtonSegment(value: 'en', label: Text('English')),
                  ButtonSegment(value: 'hi', label: Text('हिन्दी')),
                ],
                selected: {language},
                onSelectionChanged: (value) => setState(() => _language = value.first),
              ),
              const SizedBox(height: PankhSpace.md),
              Text(letter['title'] as String, style: text.titleLarge),
              if (full.contains('________')) ...[
                const SizedBox(height: PankhSpace.xs),
                Text(l10n.letterBlanks, style: text.bodySmall),
              ],
              const SizedBox(height: PankhSpace.md),
              Container(
                padding: const EdgeInsets.all(18),
                decoration: BoxDecoration(
                  color: PankhColors.card,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: PankhColors.line, width: 1.5),
                ),
                child: SelectableText(full, style: text.bodyMedium?.copyWith(height: 1.55)),
              ),
              const SizedBox(height: PankhSpace.md),
              FilledButton.icon(
                onPressed: () async {
                  await Clipboard.setData(ClipboardData(text: full));
                  if (!context.mounted) return;
                  ScaffoldMessenger.of(
                    context,
                  ).showSnackBar(SnackBar(content: Text(l10n.letterCopied)));
                },
                icon: const Icon(Icons.copy_rounded),
                label: Text(l10n.letterCopy),
              ),
            ],
          );
        },
      ),
    );
  }
}
