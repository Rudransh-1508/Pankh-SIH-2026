import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../l10n/generated/app_localizations.dart';
import '../theme.dart';
import '../widgets/feather_mark.dart';
import '../widgets/language_button.dart';

class WelcomeScreen extends StatelessWidget {
  const WelcomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final text = Theme.of(context).textTheme;
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(
            PankhSpace.gutter,
            PankhSpace.sm,
            PankhSpace.gutter,
            PankhSpace.md,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Text(
                    l10n.appName,
                    style: text.titleLarge?.copyWith(color: PankhColors.peacockDeep),
                  ),
                  const Spacer(),
                  const LanguageButton(),
                ],
              ),
              const Spacer(flex: 2),
              FeatherMark(size: 168, semanticLabel: l10n.appName),
              const SizedBox(height: PankhSpace.xl),
              Text(l10n.welcomeTitle, style: text.displaySmall),
              const SizedBox(height: PankhSpace.md),
              Text(l10n.welcomeBody, style: text.bodyLarge?.copyWith(color: PankhColors.inkSoft)),
              const Spacer(flex: 3),
              FilledButton(
                onPressed: () => context.push('/questions'),
                child: Text(l10n.welcomeStart),
              ),
              const SizedBox(height: PankhSpace.sm),
              Center(
                child: TextButton(
                  onPressed: () => context.push('/sign-in'),
                  child: Text(l10n.welcomeSignIn),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
