import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/api.dart';
import '../data/voice_line.dart';
import '../l10n/generated/app_localizations.dart';
import '../state/providers.dart';
import '../theme.dart';
import '../widgets/feather_mark.dart';

enum _State { connecting, live, failed }

/// A live spoken conversation with JAGO, with what each side said written out.
class VoiceScreen extends ConsumerStatefulWidget {
  const VoiceScreen({super.key});

  @override
  ConsumerState<VoiceScreen> createState() => _VoiceScreenState();
}

class _VoiceScreenState extends ConsumerState<VoiceScreen> {
  late final VoiceCall _call = ref.read(voiceCallFactoryProvider)();
  final _lines = <VoiceLine>[];
  final _subscriptions = <StreamSubscription<Object?>>[];
  _State _state = _State.connecting;
  bool _speaking = false;
  bool _muted = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _start());
  }

  Future<void> _start() async {
    _subscriptions
      ..add(_call.lines.listen((line) => setState(() => _lines.add(line))))
      ..add(_call.jagoSpeaking.listen((speaking) => setState(() => _speaking = speaking)));
    try {
      final language = Localizations.localeOf(context).languageCode;
      final session = await ref.read(apiProvider).voiceSession(language);
      await _call.connect(session['url'] as String, session['token'] as String);
      if (mounted) setState(() => _state = _State.live);
    } on ApiException {
      if (mounted) setState(() => _state = _State.failed);
    } catch (_) {
      // LiveKit reports connection failures with its own errors.
      if (mounted) setState(() => _state = _State.failed);
    }
  }

  @override
  void dispose() {
    for (final subscription in _subscriptions) {
      unawaited(subscription.cancel());
    }
    unawaited(_call.hangUp());
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final text = Theme.of(context).textTheme;
    final status = switch (_state) {
      _State.connecting => l10n.voiceConnecting,
      _State.failed => l10n.voiceUnavailable,
      _State.live => _speaking ? l10n.voiceSpeaking : l10n.voiceListening,
    };
    return Scaffold(
      appBar: AppBar(title: Text(l10n.voiceTalk)),
      body: SafeArea(
        child: Column(
          children: [
            const SizedBox(height: PankhSpace.lg),
            AnimatedContainer(
              duration: const Duration(milliseconds: 300),
              padding: EdgeInsets.all(_speaking ? 30 : 22),
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: _speaking ? PankhColors.peacockMist : PankhColors.card,
                border: Border.all(
                  color: _speaking ? PankhColors.peacock : PankhColors.line,
                  width: 2,
                ),
              ),
              child: const FeatherMark(size: 64),
            ),
            const SizedBox(height: PankhSpace.md),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: PankhSpace.gutter),
              child: Text(status, style: text.titleMedium, textAlign: TextAlign.center),
            ),
            const SizedBox(height: PankhSpace.md),
            Expanded(
              child: ListView(
                reverse: true,
                padding: const EdgeInsets.symmetric(horizontal: PankhSpace.gutter),
                children: [
                  for (final line in _lines.reversed)
                    Padding(
                      padding: const EdgeInsets.only(bottom: PankhSpace.sm + 2),
                      child: Column(
                        crossAxisAlignment: line.fromStudent
                            ? CrossAxisAlignment.end
                            : CrossAxisAlignment.start,
                        children: [
                          Text(
                            line.fromStudent ? l10n.voiceYou : 'JAGO',
                            style: text.labelMedium?.copyWith(color: PankhColors.inkSoft),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            line.text,
                            style: text.bodyLarge,
                            textAlign: line.fromStudent ? TextAlign.end : TextAlign.start,
                          ),
                        ],
                      ),
                    ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(
                PankhSpace.gutter,
                PankhSpace.sm,
                PankhSpace.gutter,
                PankhSpace.md,
              ),
              child: Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: _state == _State.live
                          ? () async {
                              setState(() => _muted = !_muted);
                              await _call.setMuted(_muted);
                            }
                          : null,
                      icon: Icon(_muted ? Icons.mic_off_rounded : Icons.mic_rounded),
                      label: Text(_muted ? l10n.voiceUnmute : l10n.voiceMute),
                    ),
                  ),
                  const SizedBox(width: PankhSpace.sm),
                  Expanded(
                    child: FilledButton.icon(
                      style: FilledButton.styleFrom(backgroundColor: PankhColors.laterite),
                      onPressed: () => Navigator.of(context).maybePop(),
                      icon: const Icon(Icons.call_end_rounded),
                      label: Text(l10n.voiceEnd),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
