import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../l10n/generated/app_localizations.dart';
import '../l10n/languages.dart';
import '../state/providers.dart';
import '../theme.dart';

/// Shows the app's language, in that language, and opens a list of every language to switch to.
class LanguageButton extends ConsumerWidget {
  const LanguageButton({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final current = ref.watch(languageProvider).languageCode;
    return TextButton.icon(
      onPressed: () => _choose(context, ref, current),
      icon: const Icon(Icons.translate_rounded, size: 20),
      label: Text(
        languageNames[current]!,
        semanticsLabel: AppLocalizations.of(context).changeLanguage,
      ),
    );
  }

  Future<void> _choose(BuildContext context, WidgetRef ref, String current) async {
    final chosen = await showModalBottomSheet<String>(
      context: context,
      // Over the tab bar, not under it.
      useRootNavigator: true,
      showDragHandle: true,
      builder: (context) => SafeArea(
        child: RadioGroup<String>(
          groupValue: current,
          onChanged: (code) => Navigator.pop(context, code),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(PankhSpace.gutter, 0, PankhSpace.gutter, 8),
                child: Text(
                  AppLocalizations.of(context).changeLanguage,
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ),
              // Scrolls when six languages do not fit, as on a small phone held sideways.
              Flexible(
                child: ListView(
                  shrinkWrap: true,
                  children: [
                    for (final MapEntry(key: code, value: name) in languageNames.entries)
                      RadioListTile<String>(
                        value: code,
                        title: Text(name, style: Theme.of(context).textTheme.bodyLarge),
                      ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
    if (chosen != null && chosen != current) {
      await ref.read(languageProvider.notifier).set(chosen);
    }
  }
}
