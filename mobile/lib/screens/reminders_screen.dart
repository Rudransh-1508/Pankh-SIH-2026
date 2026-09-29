import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../l10n/generated/app_localizations.dart';
import '../state/providers.dart';
import '../theme.dart';
import '../widgets/error_view.dart';

/// Reminders about the Student's own applications, payments and documents.
class RemindersScreen extends ConsumerWidget {
  const RemindersScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final text = Theme.of(context).textTheme;
    return Scaffold(
      appBar: AppBar(title: Text(l10n.remindersTitle)),
      body: ref
          .watch(remindersProvider)
          .when(
            error: (error, _) =>
                ErrorView(error: error, onRetry: () => ref.invalidate(remindersProvider)),
            loading: () => const Center(child: CircularProgressIndicator()),
            data: (reminders) => reminders.isEmpty
                ? Padding(
                    padding: const EdgeInsets.all(PankhSpace.gutter),
                    child: Text(l10n.remindersNone, style: text.bodyLarge),
                  )
                : ListView.separated(
                    padding: const EdgeInsets.all(PankhSpace.gutter),
                    itemCount: reminders.length,
                    separatorBuilder: (_, _) => const SizedBox(height: PankhSpace.sm + 2),
                    itemBuilder: (context, index) {
                      final (message, at) = reminders[index];
                      final date = at.substring(0, 10).split('-').reversed.join('/');
                      return Container(
                        padding: const EdgeInsets.all(14),
                        decoration: BoxDecoration(
                          color: PankhColors.card,
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(color: PankhColors.line, width: 1.5),
                        ),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Icon(Icons.notifications_rounded, color: PankhColors.turmeric),
                            const SizedBox(width: PankhSpace.sm + 2),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(message, style: text.bodyLarge),
                                  const SizedBox(height: 4),
                                  Text(date, style: text.bodySmall),
                                ],
                              ),
                            ),
                          ],
                        ),
                      );
                    },
                  ),
          ),
    );
  }
}
