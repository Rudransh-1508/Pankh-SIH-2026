import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../l10n/generated/app_localizations.dart';
import '../state/providers.dart';

/// Switches between English and Hindi. Shows the language it switches to, in that language.
class LanguageButton extends ConsumerWidget {
  const LanguageButton({super.key});

  static const _names = {'en': 'English', 'hi': 'हिन्दी'};

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final current = ref.watch(languageProvider).languageCode;
    final other = current == 'hi' ? 'en' : 'hi';
    return TextButton.icon(
      onPressed: () => ref.read(languageProvider.notifier).set(other),
      icon: const Icon(Icons.translate_rounded, size: 20),
      label: Text(_names[other]!, semanticsLabel: AppLocalizations.of(context).changeLanguage),
    );
  }
}
