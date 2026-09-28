import 'package:flutter/material.dart';

import '../data/api.dart';
import '../l10n/generated/app_localizations.dart';
import '../theme.dart';

/// Says what went wrong and offers to try again.
class ErrorView extends StatelessWidget {
  const ErrorView({super.key, required this.error, required this.onRetry});

  final Object error;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final message = error is ApiException && !(error as ApiException).isOffline
        ? (error as ApiException).message
        : l10n.networkError;
    return Padding(
      padding: const EdgeInsets.all(PankhSpace.gutter),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Icon(Icons.wifi_off_rounded, size: 40, color: PankhColors.inkSoft),
          const SizedBox(height: PankhSpace.md),
          Text(message, textAlign: TextAlign.center, style: Theme.of(context).textTheme.bodyLarge),
          const SizedBox(height: PankhSpace.lg),
          OutlinedButton(onPressed: onRetry, child: Text(l10n.tryAgain)),
        ],
      ),
    );
  }
}
