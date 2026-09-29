import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:go_router/go_router.dart';
import 'package:speech_to_text/speech_to_text.dart';
import 'package:url_launcher/url_launcher.dart';

import '../data/api.dart';
import '../data/models.dart';
import '../l10n/generated/app_localizations.dart';
import '../state/providers.dart';
import '../theme.dart';
import '../widgets/error_view.dart';
import '../widgets/feather_mark.dart';

/// A conversation with JAGO, by typing or by voice, with replies read aloud on request.
class JagoScreen extends ConsumerWidget {
  const JagoScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final signedIn = ref.watch(sessionProvider) != null;
    return Scaffold(
      appBar: AppBar(
        titleSpacing: PankhSpace.gutter,
        title: Row(
          children: [
            const FeatherMark(size: 26),
            const SizedBox(width: PankhSpace.sm),
            Text(l10n.jagoTitle, style: Theme.of(context).textTheme.titleLarge),
          ],
        ),
        actions: [
          if (signedIn)
            IconButton(
              tooltip: l10n.voiceTalk,
              icon: const Icon(Icons.graphic_eq_rounded, color: PankhColors.peacockDeep),
              // The spoken conversation joins JAGO's history, so the chat shows it after.
              onPressed: () async {
                await context.push('/voice');
                ref.invalidate(jagoProvider);
              },
            ),
        ],
      ),
      body: !signedIn
          ? Padding(
              padding: const EdgeInsets.all(PankhSpace.gutter),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(l10n.jagoSignIn, style: Theme.of(context).textTheme.bodyLarge),
                  const SizedBox(height: PankhSpace.lg),
                  FilledButton(onPressed: () => context.push('/sign-in'), child: Text(l10n.signIn)),
                ],
              ),
            )
          : const _Conversation(),
    );
  }
}

class _Conversation extends ConsumerStatefulWidget {
  const _Conversation();

  @override
  ConsumerState<_Conversation> createState() => _ConversationState();
}

class _ConversationState extends ConsumerState<_Conversation> {
  final _input = TextEditingController();
  final _scroll = ScrollController();
  final _speech = SpeechToText();
  final _tts = FlutterTts();
  bool _sending = false;
  bool _listening = false;
  int? _speaking;

  @override
  void dispose() {
    _input.dispose();
    _scroll.dispose();
    unawaited(_speech.cancel());
    unawaited(_tts.stop());
    super.dispose();
  }

  String get _language => Localizations.localeOf(context).languageCode;

  Future<void> _send(String text) async {
    if (text.trim().isEmpty || _sending) return;
    setState(() => _sending = true);
    _input.clear();
    try {
      await ref.read(jagoProvider.notifier).say(text);
      _scrollToEnd();
    } on ApiException catch (error) {
      if (!mounted) return;
      final l10n = AppLocalizations.of(context);
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(error.isOffline ? l10n.networkError : error.message)));
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  void _scrollToEnd() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        unawaited(
          _scroll.animateTo(
            _scroll.position.maxScrollExtent,
            duration: const Duration(milliseconds: 250),
            curve: Curves.easeOut,
          ),
        );
      }
    });
  }

  Future<void> _listen() async {
    final l10n = AppLocalizations.of(context);
    if (_listening) {
      await _speech.stop();
      setState(() => _listening = false);
      return;
    }
    final available = await _speech.initialize(
      onStatus: (status) {
        if (status == 'done' || status == 'notListening') {
          if (mounted) setState(() => _listening = false);
        }
      },
    );
    if (!available) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l10n.jagoNoMic)));
      }
      return;
    }
    setState(() => _listening = true);
    await _speech.listen(
      listenOptions: SpeechListenOptions(
        partialResults: true,
        localeId: _language == 'hi' ? 'hi_IN' : 'en_IN',
      ),
      onResult: (result) {
        _input.text = result.recognizedWords;
        if (result.finalResult) {
          setState(() => _listening = false);
          unawaited(_send(result.recognizedWords));
        }
      },
    );
  }

  Future<void> _readAloud(int index, String text) async {
    if (_speaking == index) {
      await _tts.stop();
      setState(() => _speaking = null);
      return;
    }
    await _tts.setLanguage(_language == 'hi' ? 'hi-IN' : 'en-IN');
    await _tts.setSpeechRate(0.45);
    _tts.setCompletionHandler(() {
      if (mounted) setState(() => _speaking = null);
    });
    setState(() => _speaking = index);
    await _tts.speak(text);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final conversation = ref.watch(jagoProvider);
    return conversation.when(
      error: (error, _) => ErrorView(error: error, onRetry: () => ref.invalidate(jagoProvider)),
      loading: () => const Center(child: CircularProgressIndicator()),
      data: (messages) {
        final suggestions = messages.isEmpty
            ? _starterSuggestions(l10n)
            : (messages.last.fromStudent ? const <String>[] : messages.last.suggestions);
        return Column(
          children: [
            Expanded(
              child: ListView(
                controller: _scroll,
                padding: const EdgeInsets.fromLTRB(
                  PankhSpace.gutter,
                  PankhSpace.sm,
                  PankhSpace.gutter,
                  PankhSpace.md,
                ),
                children: [
                  if (messages.isEmpty)
                    _Bubble(message: ChatMessage(fromStudent: false, text: l10n.jagoIntro)),
                  for (final (index, message) in messages.indexed)
                    _Bubble(
                      message: message,
                      speaking: _speaking == index,
                      onReadAloud: message.fromStudent
                          ? null
                          : () => _readAloud(index, message.text),
                    ),
                  if (_sending)
                    const Padding(
                      padding: EdgeInsets.only(top: PankhSpace.sm),
                      child: Align(
                        alignment: Alignment.centerLeft,
                        child: SizedBox.square(
                          dimension: 24,
                          child: CircularProgressIndicator(strokeWidth: 2.5),
                        ),
                      ),
                    ),
                ],
              ),
            ),
            if (suggestions.isNotEmpty)
              SizedBox(
                height: 52,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  padding: const EdgeInsets.symmetric(horizontal: PankhSpace.gutter),
                  itemCount: suggestions.length,
                  separatorBuilder: (_, _) => const SizedBox(width: PankhSpace.sm),
                  itemBuilder: (context, index) => ActionChip(
                    label: Text(suggestions[index]),
                    onPressed: _sending ? null : () => _send(suggestions[index]),
                    backgroundColor: PankhColors.card,
                    side: const BorderSide(color: PankhColors.line, width: 1.5),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                  ),
                ),
              ),
            _Composer(
              controller: _input,
              listening: _listening,
              sending: _sending,
              onSend: () => _send(_input.text),
              onMic: _listen,
            ),
          ],
        );
      },
    );
  }

  List<String> _starterSuggestions(AppLocalizations l10n) => _language == 'hi'
      ? const ['मुझे कौन-सी छात्रवृत्ति मिल सकती है?', 'मेरा आवेदन कहाँ है?', 'क्या मेरा पैसा आया?']
      : const ['Which scholarships can I get?', 'Where is my application?', 'Has my money come?'];
}

class _Bubble extends StatelessWidget {
  const _Bubble({required this.message, this.onReadAloud, this.speaking = false});

  final ChatMessage message;
  final VoidCallback? onReadAloud;
  final bool speaking;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    final l10n = AppLocalizations.of(context);
    final mine = message.fromStudent;
    return Align(
      alignment: mine ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        constraints: BoxConstraints(maxWidth: MediaQuery.sizeOf(context).width * 0.82),
        margin: const EdgeInsets.only(bottom: PankhSpace.sm + 2),
        padding: const EdgeInsets.fromLTRB(14, 12, 14, 8),
        decoration: BoxDecoration(
          color: mine ? PankhColors.peacock : PankhColors.card,
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(18),
            topRight: const Radius.circular(18),
            bottomLeft: Radius.circular(mine ? 18 : 4),
            bottomRight: Radius.circular(mine ? 4 : 18),
          ),
          border: mine ? null : Border.all(color: PankhColors.line, width: 1.5),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              message.text,
              style: text.bodyLarge?.copyWith(color: mine ? Colors.white : PankhColors.ink),
            ),
            for (final (title, url) in message.sources.take(3))
              InkWell(
                onTap: () => launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication),
                child: Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(
                        Icons.description_outlined,
                        size: 14,
                        color: PankhColors.peacockDeep,
                      ),
                      const SizedBox(width: 4),
                      Flexible(
                        child: Text(
                          title,
                          style: text.labelMedium?.copyWith(
                            color: PankhColors.peacockDeep,
                            decoration: TextDecoration.underline,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            if (onReadAloud != null)
              Align(
                alignment: Alignment.centerLeft,
                child: TextButton.icon(
                  style: TextButton.styleFrom(
                    padding: EdgeInsets.zero,
                    minimumSize: const Size(0, 40),
                    tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                  ),
                  onPressed: onReadAloud,
                  icon: Icon(
                    speaking ? Icons.stop_circle_outlined : Icons.volume_up_rounded,
                    size: 20,
                  ),
                  label: Text(speaking ? l10n.jagoStop : l10n.jagoSpeak),
                ),
              )
            else
              const SizedBox(height: 4),
          ],
        ),
      ),
    );
  }
}

class _Composer extends StatelessWidget {
  const _Composer({
    required this.controller,
    required this.listening,
    required this.sending,
    required this.onSend,
    required this.onMic,
  });

  final TextEditingController controller;
  final bool listening;
  final bool sending;
  final VoidCallback onSend;
  final VoidCallback onMic;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(PankhSpace.gutter, PankhSpace.sm, 12, PankhSpace.sm),
        child: Row(
          children: [
            Expanded(
              child: TextField(
                controller: controller,
                minLines: 1,
                maxLines: 4,
                textInputAction: TextInputAction.send,
                onSubmitted: (_) => onSend(),
                decoration: InputDecoration(
                  hintText: listening ? l10n.jagoListening : l10n.jagoHint,
                  contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                ),
              ),
            ),
            const SizedBox(width: 6),
            IconButton.filled(
              tooltip: l10n.jagoMic,
              onPressed: sending ? null : onMic,
              style: IconButton.styleFrom(
                backgroundColor: listening ? PankhColors.laterite : PankhColors.turmeric,
                foregroundColor: PankhColors.ink,
                minimumSize: const Size(52, 52),
              ),
              icon: Icon(listening ? Icons.stop_rounded : Icons.mic_rounded),
            ),
            IconButton(
              tooltip: l10n.jagoSend,
              onPressed: sending ? null : onSend,
              icon: const Icon(Icons.send_rounded, color: PankhColors.peacockDeep),
            ),
          ],
        ),
      ),
    );
  }
}
