import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/api.dart';
import '../data/models.dart';
import '../l10n/generated/app_localizations.dart';
import '../state/providers.dart';
import '../theme.dart';

/// Complaints on CPGRAMS: ones the grievance agent drafted, waiting for the Student's approval,
/// and ones already filed, with the ministry's reply.
class GrievanceSection extends ConsumerWidget {
  const GrievanceSection({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final text = Theme.of(context).textTheme;
    final data = ref.watch(grievancesProvider).value;
    final drafts = (data?['drafts'] as List?) ?? const [];
    final filed = (data?['filed'] as List?) ?? const [];
    if (drafts.isEmpty && filed.isEmpty) return const SizedBox.shrink();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.only(top: PankhSpace.lg, bottom: PankhSpace.sm + 2),
          child: Text(l10n.grievanceHeading, style: text.titleLarge),
        ),
        for (final draft in drafts.cast<Json>())
          Container(
            margin: const EdgeInsets.only(bottom: PankhSpace.md - 4),
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: PankhColors.card,
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: PankhColors.turmeric, width: 1.5),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(l10n.grievanceDraftTitle, style: text.titleMedium),
                const SizedBox(height: PankhSpace.xs),
                Text(draft['reason'] as String, style: text.bodyMedium),
                const SizedBox(height: PankhSpace.sm + 2),
                OutlinedButton(
                  onPressed: () => _review(context, ref, draft),
                  child: Text(l10n.grievanceDraftAction),
                ),
              ],
            ),
          ),
        for (final grievance in filed.cast<Json>())
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: Icon(
              grievance['closed_at'] == null
                  ? Icons.hourglass_top_rounded
                  : Icons.mark_email_read_rounded,
              color: grievance['closed_at'] == null ? PankhColors.peacock : PankhColors.leaf,
            ),
            title: Text(grievance['subject'] as String, style: text.titleSmall),
            subtitle: Text(
              [
                l10n.grievanceStatus(
                  grievance['registration_number'] as String,
                  grievance['status'] as String,
                ),
                if (grievance['reply'] case final String reply) l10n.grievanceReply(reply),
              ].join('\n'),
              style: text.bodySmall,
            ),
          ),
      ],
    );
  }

  Future<void> _review(BuildContext context, WidgetRef ref, Json draft) async {
    final l10n = AppLocalizations.of(context);
    final note = TextEditingController();
    final approved = await showModalBottomSheet<bool>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (context) {
        final text = Theme.of(context).textTheme;
        return Padding(
          padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
          child: SafeArea(
            child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(
                PankhSpace.gutter,
                0,
                PankhSpace.gutter,
                PankhSpace.md,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(l10n.grievanceSheetTitle, style: text.titleLarge),
                  const SizedBox(height: PankhSpace.xs),
                  Text(l10n.grievanceSheetBody, style: text.bodySmall),
                  const SizedBox(height: PankhSpace.md),
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: PankhColors.paper,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(draft['subject'] as String, style: text.titleSmall),
                        const SizedBox(height: PankhSpace.xs),
                        Text(draft['description'] as String, style: text.bodyMedium),
                      ],
                    ),
                  ),
                  const SizedBox(height: PankhSpace.md),
                  TextField(
                    controller: note,
                    maxLength: 500,
                    maxLines: 3,
                    minLines: 1,
                    decoration: InputDecoration(labelText: l10n.grievanceNote),
                  ),
                  const SizedBox(height: PankhSpace.sm),
                  FilledButton(
                    onPressed: () => Navigator.pop(context, true),
                    child: Text(l10n.grievanceFile),
                  ),
                  const SizedBox(height: PankhSpace.sm),
                  TextButton(
                    onPressed: () => Navigator.pop(context, false),
                    child: Text(l10n.grievanceCancel),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
    final noteText = note.text;
    note.dispose();
    if (approved != true || !context.mounted) return;
    try {
      final filed = await ref.read(apiProvider).fileGrievance(draft['key'] as String, noteText);
      ref.invalidate(grievancesProvider);
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(l10n.grievanceFiled(filed['registration_number'] as String))),
      );
    } on ApiException catch (error) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(error.isOffline ? l10n.networkError : error.message)));
    }
  }
}
