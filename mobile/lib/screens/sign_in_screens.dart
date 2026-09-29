import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../data/api.dart';
import '../data/sms_sign_in.dart';
import '../l10n/generated/app_localizations.dart';
import '../state/providers.dart';
import '../theme.dart';

String _message(BuildContext context, ApiException error) =>
    error.isOffline ? AppLocalizations.of(context).networkError : error.message;

class _Page extends StatelessWidget {
  const _Page({required this.title, required this.body, required this.children});

  final String title;
  final String body;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    return Scaffold(
      appBar: AppBar(),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(
            PankhSpace.gutter,
            PankhSpace.sm,
            PankhSpace.gutter,
            PankhSpace.lg,
          ),
          children: [
            Text(title, style: text.headlineMedium),
            const SizedBox(height: PankhSpace.sm),
            Text(body, style: text.bodyLarge?.copyWith(color: PankhColors.inkSoft)),
            const SizedBox(height: PankhSpace.lg),
            ...children,
          ],
        ),
      ),
    );
  }
}

class PhoneScreen extends ConsumerStatefulWidget {
  const PhoneScreen({super.key});

  @override
  ConsumerState<PhoneScreen> createState() => _PhoneScreenState();
}

class _PhoneScreenState extends ConsumerState<PhoneScreen> {
  final _controller = TextEditingController();
  String? _error;
  bool _busy = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final sms = ref.read(smsSignInProvider);
      final OtpRequested sent;
      if (sms != null && !isDemoNumber(_controller.text)) {
        final phone = '+91${_controller.text}';
        await sms.send(phone);
        sent = OtpRequested(phone: phone, resendAfter: 30, bySms: true);
      } else {
        sent = await ref.read(apiProvider).requestOtp(_controller.text);
      }
      if (!mounted) return;
      unawaited(context.push('/sign-in/code', extra: sent));
    } on ApiException catch (error) {
      setState(() => _error = _message(context, error));
    } on SmsSignInError catch (error) {
      setState(() => _error = error.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return _Page(
      title: l10n.phoneTitle,
      body: l10n.phoneBody,
      children: [
        TextField(
          controller: _controller,
          autofocus: true,
          keyboardType: TextInputType.phone,
          autofillHints: const [AutofillHints.telephoneNumberNational],
          inputFormatters: [
            FilteringTextInputFormatter.digitsOnly,
            LengthLimitingTextInputFormatter(10),
          ],
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(letterSpacing: 1.5),
          decoration: InputDecoration(
            labelText: l10n.phoneLabel,
            prefixText: '+91  ',
            errorText: _error,
            errorMaxLines: 3,
          ),
          onChanged: (_) => setState(() {}),
          onSubmitted: (_) => _controller.text.length == 10 ? _send() : null,
        ),
        const SizedBox(height: PankhSpace.lg),
        FilledButton(
          onPressed: _busy || _controller.text.length != 10 ? null : _send,
          child: _busy ? const _Spinner() : Text(l10n.sendCode),
        ),
      ],
    );
  }
}

class CodeScreen extends ConsumerStatefulWidget {
  const CodeScreen({super.key, required this.sent});

  final OtpRequested sent;

  @override
  ConsumerState<CodeScreen> createState() => _CodeScreenState();
}

class _CodeScreenState extends ConsumerState<CodeScreen> {
  final _controller = TextEditingController();
  late String _phone = widget.sent.phone;
  late int _wait = widget.sent.resendAfter;
  late String? _demoCode = widget.sent.demoCode;
  Timer? _timer;
  StreamSubscription<String>? _automatic;
  String? _error;
  bool _busy = false;

  bool get _bySms => widget.sent.bySms;

  @override
  void initState() {
    super.initState();
    _startTimer();
    // On Android the phone can read the SMS itself; then there is nothing to type.
    _automatic = ref.read(smsSignInProvider)?.verifiedAutomatically.listen(_finish);
  }

  @override
  void dispose() {
    _timer?.cancel();
    unawaited(_automatic?.cancel());
    _controller.dispose();
    super.dispose();
  }

  void _startTimer() {
    _timer?.cancel();
    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (_wait <= 1) timer.cancel();
      setState(() => _wait = _wait > 0 ? _wait - 1 : 0);
    });
  }

  Future<void> _resend() async {
    try {
      if (_bySms) {
        await ref.read(smsSignInProvider)!.send(_phone);
        setState(() {
          _wait = 30;
          _error = null;
        });
      } else {
        final sent = await ref.read(apiProvider).requestOtp(_phone);
        setState(() {
          _phone = sent.phone;
          _wait = sent.resendAfter;
          _demoCode = sent.demoCode;
          _error = null;
        });
      }
      _startTimer();
    } on ApiException catch (error) {
      if (mounted) setState(() => _error = _message(context, error));
    } on SmsSignInError catch (error) {
      if (mounted) setState(() => _error = error.message);
    }
  }

  Future<void> _verify() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      if (_bySms) {
        await _finish(await ref.read(smsSignInProvider)!.confirm(_controller.text));
      } else {
        await ref.read(apiProvider).verifyOtp(_phone, _controller.text);
        await _signedIn();
      }
    } on ApiException catch (error) {
      if (mounted) setState(() => _error = _message(context, error));
    } on SmsSignInError catch (error) {
      if (mounted) setState(() => _error = error.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  /// The number is proved by SMS: exchange Firebase's token for a Pankh session.
  Future<void> _finish(String idToken) async {
    try {
      await ref.read(apiProvider).signInWithSms(idToken);
      await _signedIn();
    } on ApiException catch (error) {
      if (mounted) setState(() => _error = _message(context, error));
    }
  }

  Future<void> _signedIn() async {
    await ref.read(sessionProvider.notifier).signedIn(_phone);
    await ref.read(profileProvider.notifier).adoptAfterSignIn();
    if (mounted) context.go('/discover');
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final readable = '+91 ${_phone.substring(3, 8)} ${_phone.substring(8)}';
    return _Page(
      title: l10n.codeTitle,
      body: l10n.codeBody(readable),
      children: [
        if (_demoCode != null) ...[
          DemoCodeNote(code: _demoCode!),
          const SizedBox(height: PankhSpace.md),
        ],
        TextField(
          controller: _controller,
          autofocus: true,
          keyboardType: TextInputType.number,
          autofillHints: const [AutofillHints.oneTimeCode],
          inputFormatters: [
            FilteringTextInputFormatter.digitsOnly,
            LengthLimitingTextInputFormatter(6),
          ],
          textAlign: TextAlign.center,
          style: Theme.of(context).textTheme.headlineMedium?.copyWith(letterSpacing: 12),
          decoration: InputDecoration(hintText: '······', errorText: _error, errorMaxLines: 3),
          onChanged: (value) {
            setState(() {});
            if (value.length == 6 && !_busy) _verify();
          },
        ),
        const SizedBox(height: PankhSpace.lg),
        FilledButton(
          onPressed: _busy || _controller.text.length != 6 ? null : _verify,
          child: _busy ? const _Spinner() : Text(l10n.verifyCode),
        ),
        const SizedBox(height: PankhSpace.sm),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            TextButton(onPressed: () => context.pop(), child: Text(l10n.changeNumber)),
            TextButton(
              onPressed: _wait > 0 ? null : _resend,
              child: Text(_wait > 0 ? l10n.resendIn(_wait) : l10n.resendCode),
            ),
          ],
        ),
      ],
    );
  }
}

class _Spinner extends StatelessWidget {
  const _Spinner();

  @override
  Widget build(BuildContext context) => const SizedBox.square(
    dimension: 22,
    child: CircularProgressIndicator(strokeWidth: 2.5, color: Colors.white),
  );
}

/// On a demo deployment, demo numbers get no SMS; the code is shown instead.
class DemoCodeNote extends StatelessWidget {
  const DemoCodeNote({super.key, required this.code});

  final String code;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(12),
    decoration: BoxDecoration(
      color: PankhColors.turmericMist,
      borderRadius: BorderRadius.circular(12),
    ),
    child: Text(
      AppLocalizations.of(context).demoCode(code),
      style: Theme.of(context).textTheme.bodyMedium,
    ),
  );
}
