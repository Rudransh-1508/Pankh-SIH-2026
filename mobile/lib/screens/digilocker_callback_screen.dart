import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../data/api.dart';
import '../l10n/generated/app_localizations.dart';
import '../state/providers.dart';
import '../theme.dart';
import '../widgets/feather_mark.dart';

/// Where DigiLocker sends the Student back (pankh://digilocker/callback?code=..&state=..).
class DigiLockerCallbackScreen extends ConsumerStatefulWidget {
  const DigiLockerCallbackScreen({super.key, required this.code, required this.state});

  final String? code;
  final String? state;

  @override
  ConsumerState<DigiLockerCallbackScreen> createState() => _DigiLockerCallbackScreenState();
}

class _DigiLockerCallbackScreenState extends ConsumerState<DigiLockerCallbackScreen> {
  String? _error;
  (int, int)? _result;

  @override
  void initState() {
    super.initState();
    _complete();
  }

  Future<void> _complete() async {
    if (widget.code == null || widget.state == null) {
      setState(() => _error = 'DigiLocker did not finish signing in. Start again.');
      return;
    }
    try {
      final json = await ref.read(apiProvider).completeDigiLocker(widget.code!, widget.state!);
      ref.invalidate(verificationProvider);
      await ref.read(profileProvider.notifier).refresh();
      setState(
        () => _result = ((json['proofs'] as List).length, (json['exceptions'] as List).length),
      );
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(
        () => _error = error.isOffline ? AppLocalizations.of(context).networkError : error.message,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final text = Theme.of(context).textTheme;
    final result = _result;
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(PankhSpace.gutter),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Spacer(),
              const FeatherMark(size: 96),
              const SizedBox(height: PankhSpace.lg),
              if (_error != null)
                Text(_error!, style: text.headlineSmall)
              else if (result == null) ...[
                Text(l10n.linkingDigiLocker, style: text.headlineSmall),
                const SizedBox(height: PankhSpace.lg),
                const LinearProgressIndicator(),
              ] else ...[
                Text(l10n.digiLockerDone(result.$1), style: text.headlineMedium),
                if (result.$2 > 0) ...[
                  const SizedBox(height: PankhSpace.sm),
                  Text(
                    l10n.digiLockerIssues(result.$2),
                    style: text.bodyLarge?.copyWith(color: PankhColors.inkSoft),
                  ),
                ],
              ],
              const Spacer(flex: 2),
              if (_error != null || result != null)
                FilledButton(onPressed: () => context.go('/wallet'), child: Text(l10n.done)),
            ],
          ),
        ),
      ),
    );
  }
}
