import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/api.dart';
import '../data/document_capture.dart';
import '../data/models.dart';
import '../l10n/generated/app_localizations.dart';
import '../state/providers.dart';
import '../theme.dart';

/// The kinds of Document a Student can photograph, in the order they are usually needed.
const photoKinds = [
  'caste_certificate',
  'income_certificate',
  'bachelors_marksheet',
  'masters_marksheet',
];

String photoKindName(AppLocalizations l10n, String kind) => switch (kind) {
  'caste_certificate' => l10n.photoKindCaste,
  'income_certificate' => l10n.photoKindIncome,
  'bachelors_marksheet' => l10n.photoKindBachelors,
  _ => l10n.photoKindMasters,
};

IconData _kindIcon(String kind) => switch (kind) {
  'caste_certificate' => Icons.badge_outlined,
  'income_certificate' => Icons.account_balance_wallet_outlined,
  _ => Icons.school_outlined,
};

enum _Step { reading, checking }

/// Photograph a Document no issuer holds digitally, and follow what happens to each photo.
class PhotoSection extends ConsumerStatefulWidget {
  const PhotoSection({super.key});

  @override
  ConsumerState<PhotoSection> createState() => _PhotoSectionState();
}

class _PhotoSectionState extends ConsumerState<PhotoSection> {
  String? _busyKind;
  _Step _step = _Step.reading;

  Future<void> _photograph(String kind) async {
    final l10n = AppLocalizations.of(context);
    final fromCamera = await showModalBottomSheet<bool>(
      context: context,
      showDragHandle: true,
      builder: (context) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(PankhSpace.gutter, 0, PankhSpace.gutter, 8),
              child: Text(
                photoKindName(l10n, kind),
                style: Theme.of(context).textTheme.titleMedium,
              ),
            ),
            ListTile(
              leading: const Icon(Icons.photo_camera_rounded, color: PankhColors.peacock),
              title: Text(l10n.photoCamera),
              onTap: () => Navigator.pop(context, true),
            ),
            ListTile(
              leading: const Icon(Icons.photo_library_rounded, color: PankhColors.peacock),
              title: Text(l10n.photoGallery),
              onTap: () => Navigator.pop(context, false),
            ),
            const SizedBox(height: PankhSpace.sm),
          ],
        ),
      ),
    );
    if (fromCamera == null || !mounted) return;

    setState(() {
      _busyKind = kind;
      _step = _Step.reading;
    });
    CapturedDocument? captured;
    try {
      captured = await ref.read(documentCaptureProvider).capture(fromCamera: fromCamera);
      if (captured == null) return;
      if (mounted) setState(() => _step = _Step.checking);
      final outcome = UploadOutcome.fromJson(
        await ref
            .read(apiProvider)
            .uploadDocument(
              kind: kind,
              path: captured.path,
              contentType: captured.contentType,
              text: captured.text,
            ),
      );
      ref.invalidate(uploadsProvider);
      ref.invalidate(verificationProvider);
      await ref.read(profileProvider.notifier).refresh();
      if (!mounted) return;
      setState(() => _busyKind = null);
      final retake = await _showOutcome(outcome);
      if (retake == true && mounted) await _photograph(kind);
    } on ApiException catch (error) {
      if (!mounted) return;
      if (error.isOffline && captured != null) {
        await ref.read(uploadQueueProvider).add(kind, captured);
        if (!mounted) return;
        setState(() {});
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l10n.photoQueued)));
        return;
      }
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(error.isOffline ? l10n.networkError : error.message)));
    } finally {
      if (mounted) setState(() => _busyKind = null);
    }
  }

  /// Returns true when the Student wants to take the photo again.
  Future<bool?> _showOutcome(UploadOutcome outcome) {
    final l10n = AppLocalizations.of(context);
    final (icon, color, title) = !outcome.readable
        ? (Icons.photo_camera_back_rounded, PankhColors.laterite, l10n.photoUnreadableTitle)
        : outcome.verified
        ? (Icons.verified_rounded, PankhColors.leaf, l10n.photoVerifiedTitle)
        : (Icons.hourglass_top_rounded, PankhColors.peacock, l10n.photoReviewerTitle);
    return showModalBottomSheet<bool>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (context) {
        final text = Theme.of(context).textTheme;
        return SafeArea(
          child: SingleChildScrollView(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(
                PankhSpace.gutter,
                0,
                PankhSpace.gutter,
                PankhSpace.md,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Icon(icon, color: color, size: 44),
                  const SizedBox(height: PankhSpace.sm),
                  Text(title, style: text.titleLarge, textAlign: TextAlign.center),
                  const SizedBox(height: PankhSpace.sm),
                  Text(outcome.message, style: text.bodyLarge, textAlign: TextAlign.center),
                  if (outcome.document?.remedy case final remedy?) ...[
                    const SizedBox(height: PankhSpace.md),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: PankhColors.paper,
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(remedy, style: text.bodyMedium),
                    ),
                  ],
                  const SizedBox(height: PankhSpace.lg),
                  if (!outcome.readable) ...[
                    FilledButton.icon(
                      onPressed: () => Navigator.pop(context, true),
                      icon: const Icon(Icons.photo_camera_rounded),
                      label: Text(l10n.photoRetake),
                    ),
                    const SizedBox(height: PankhSpace.sm),
                    TextButton(
                      onPressed: () => Navigator.pop(context, false),
                      child: Text(l10n.photoCancel),
                    ),
                  ] else
                    FilledButton(
                      onPressed: () => Navigator.pop(context, false),
                      child: Text(l10n.photoDone),
                    ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final text = Theme.of(context).textTheme;
    final uploads = ref.watch(uploadsProvider).value ?? const [];
    final waiting = ref.watch(uploadQueueProvider).pending;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.only(top: PankhSpace.xl, bottom: PankhSpace.xs),
          child: Text(l10n.photoTitle, style: text.titleLarge),
        ),
        Text(l10n.photoIntro, style: text.bodyMedium),
        const SizedBox(height: PankhSpace.md),
        LayoutBuilder(
          builder: (context, constraints) {
            final width = (constraints.maxWidth - PankhSpace.sm) / 2;
            return Wrap(
              spacing: PankhSpace.sm,
              runSpacing: PankhSpace.sm,
              children: [
                for (final kind in photoKinds)
                  SizedBox(
                    width: width,
                    child: _KindButton(
                      label: photoKindName(l10n, kind),
                      icon: _kindIcon(kind),
                      busyLabel: _busyKind == kind
                          ? (_step == _Step.reading ? l10n.photoReading : l10n.photoChecking)
                          : null,
                      onPressed: _busyKind == null ? () => _photograph(kind) : null,
                    ),
                  ),
              ],
            );
          },
        ),
        const SizedBox(height: PankhSpace.sm),
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Padding(
              padding: EdgeInsets.only(top: 2),
              child: Icon(Icons.lock_outline_rounded, size: 16, color: PankhColors.inkSoft),
            ),
            const SizedBox(width: 6),
            Expanded(child: Text(l10n.photoPrivacy, style: text.bodySmall)),
          ],
        ),
        if (uploads.isNotEmpty || waiting.isNotEmpty) ...[
          Padding(
            padding: const EdgeInsets.only(top: PankhSpace.lg, bottom: PankhSpace.xs),
            child: Text(l10n.photoYours, style: text.titleMedium),
          ),
          for (final upload in waiting)
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.cloud_upload_outlined, color: PankhColors.inkSoft),
              title: Text(photoKindName(l10n, upload['kind'] as String), style: text.titleSmall),
              subtitle: Text(l10n.photoStatusWaiting, style: text.bodySmall),
            ),
          for (final upload in uploads) _UploadTile(upload: upload),
        ],
      ],
    );
  }
}

class _KindButton extends StatelessWidget {
  const _KindButton({
    required this.label,
    required this.icon,
    required this.onPressed,
    this.busyLabel,
  });

  final String label;
  final IconData icon;
  final String? busyLabel;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    final busy = busyLabel != null;
    return Material(
      color: PankhColors.card,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: busy ? PankhColors.peacock : PankhColors.line, width: 1.5),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: onPressed,
        child: ConstrainedBox(
          constraints: const BoxConstraints(minHeight: 92),
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                busy
                    ? const SizedBox.square(
                        dimension: 24,
                        child: CircularProgressIndicator(strokeWidth: 2.5),
                      )
                    : Icon(icon, color: PankhColors.peacock),
                const SizedBox(height: PankhSpace.sm),
                Text(
                  busyLabel ?? label,
                  style: text.titleSmall?.copyWith(
                    color: onPressed == null && !busy ? PankhColors.inkSoft : PankhColors.ink,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _UploadTile extends ConsumerWidget {
  const _UploadTile({required this.upload});

  final UploadedDocument upload;

  (IconData, Color, String) _status(AppLocalizations l10n) => switch (upload.status) {
    'verified' => (Icons.verified_rounded, PankhColors.leaf, l10n.photoStatusVerified),
    'accepted' => (Icons.verified_rounded, PankhColors.leaf, l10n.photoStatusAccepted),
    'rejected' => (Icons.error_outline_rounded, PankhColors.laterite, l10n.photoStatusRejected),
    _ => (Icons.hourglass_top_rounded, PankhColors.peacock, l10n.photoStatusWithReviewer),
  };

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final (icon, color, label) = _status(l10n);
    return ListTile(
      contentPadding: EdgeInsets.zero,
      leading: Icon(icon, color: color),
      title: Text(photoKindName(l10n, upload.kind), style: Theme.of(context).textTheme.titleSmall),
      subtitle: Text(label, style: Theme.of(context).textTheme.bodySmall?.copyWith(color: color)),
      trailing: const Icon(Icons.chevron_right_rounded),
      onTap: () => _details(context, ref),
    );
  }

  Future<void> _details(BuildContext context, WidgetRef ref) async {
    final l10n = AppLocalizations.of(context);
    final action = await showModalBottomSheet<String>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (context) {
        final text = Theme.of(context).textTheme;
        return SafeArea(
          child: SingleChildScrollView(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(
                PankhSpace.gutter,
                0,
                PankhSpace.gutter,
                PankhSpace.md,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(photoKindName(l10n, upload.kind), style: text.titleLarge),
                  const SizedBox(height: PankhSpace.xs),
                  Text(_status(l10n).$3, style: text.titleSmall?.copyWith(color: _status(l10n).$2)),
                  if (upload.message case final message?) ...[
                    const SizedBox(height: PankhSpace.sm),
                    Text(message, style: text.bodyMedium),
                  ],
                  if (upload.reviewerNote case final note?) ...[
                    const SizedBox(height: PankhSpace.sm),
                    Text(l10n.photoOfficerNote(note), style: text.bodyMedium),
                  ],
                  const SizedBox(height: PankhSpace.lg),
                  OutlinedButton.icon(
                    onPressed: () => Navigator.pop(context, 'view'),
                    icon: const Icon(Icons.image_outlined),
                    label: Text(l10n.photoView),
                  ),
                  const SizedBox(height: PankhSpace.sm),
                  TextButton.icon(
                    style: TextButton.styleFrom(foregroundColor: PankhColors.laterite),
                    onPressed: () => Navigator.pop(context, 'delete'),
                    icon: const Icon(Icons.delete_outline_rounded),
                    label: Text(l10n.photoDelete),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
    if (!context.mounted) return;
    try {
      if (action == 'view') {
        final bytes = await ref.read(apiProvider).uploadPhoto(upload.id);
        if (context.mounted) await _showPhoto(context, bytes);
      } else if (action == 'delete') {
        final sure = await showDialog<bool>(
          context: context,
          builder: (context) => AlertDialog(
            content: Text(l10n.photoDeleteConfirm),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context, false),
                child: Text(l10n.photoCancel),
              ),
              TextButton(
                style: TextButton.styleFrom(foregroundColor: PankhColors.laterite),
                onPressed: () => Navigator.pop(context, true),
                child: Text(l10n.photoDelete),
              ),
            ],
          ),
        );
        if (sure != true) return;
        await ref.read(apiProvider).deleteUpload(upload.id);
        ref.invalidate(uploadsProvider);
        ref.invalidate(verificationProvider);
      }
    } on ApiException catch (error) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(error.isOffline ? l10n.networkError : error.message)));
    }
  }
}

Future<void> _showPhoto(BuildContext context, Uint8List bytes) => showDialog<void>(
  context: context,
  builder: (context) => Dialog.fullscreen(
    backgroundColor: Colors.black,
    child: Stack(
      children: [
        Positioned.fill(
          child: InteractiveViewer(
            maxScale: 5,
            child: Center(child: Image.memory(bytes, gaplessPlayback: true)),
          ),
        ),
        SafeArea(
          child: IconButton(
            color: Colors.white,
            tooltip: MaterialLocalizations.of(context).closeButtonTooltip,
            icon: const Icon(Icons.close_rounded),
            onPressed: () => Navigator.pop(context),
          ),
        ),
      ],
    ),
  ),
);
