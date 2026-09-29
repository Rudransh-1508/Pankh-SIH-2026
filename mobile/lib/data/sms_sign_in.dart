import 'dart:async';

import 'package:firebase_auth/firebase_auth.dart';

/// A sign-in code could not be sent or was not accepted. [message] is ready to show.
class SmsSignInError implements Exception {
  const SmsSignInError(this.message, {this.wrongCode = false});

  final String message;
  final bool wrongCode;

  @override
  String toString() => message;
}

/// Sending a sign-in code by SMS and confirming it, ending with an ID token the Pankh API
/// accepts. Behind an interface so screens are tested without Firebase.
abstract class SmsSignIn {
  /// ID tokens from numbers the phone verified by itself (Android reads the SMS).
  Stream<String> get verifiedAutomatically;

  Future<void> send(String phoneE164);
  Future<String> confirm(String code);
}

/// Firebase Authentication: Google sends the SMS, registered for Indian delivery (DLT) on its
/// own account, so Pankh needs no SMS sender of its own for the prototype.
class FirebaseSmsSignIn implements SmsSignIn {
  final _auth = FirebaseAuth.instance;
  final _automatic = StreamController<String>.broadcast();
  String? _verificationId;
  int? _resendToken;

  @override
  Stream<String> get verifiedAutomatically => _automatic.stream;

  @override
  Future<void> send(String phoneE164) {
    final sent = Completer<void>();
    unawaited(
      _auth.verifyPhoneNumber(
        phoneNumber: phoneE164,
        forceResendingToken: _resendToken,
        timeout: const Duration(seconds: 60),
        verificationCompleted: (credential) async {
          final token = await _idToken(credential);
          if (token != null) _automatic.add(token);
        },
        verificationFailed: (error) {
          if (!sent.isCompleted) sent.completeError(_error(error));
        },
        codeSent: (verificationId, resendToken) {
          _verificationId = verificationId;
          _resendToken = resendToken;
          if (!sent.isCompleted) sent.complete();
        },
        codeAutoRetrievalTimeout: (_) {},
      ),
    );
    return sent.future;
  }

  @override
  Future<String> confirm(String code) async {
    final verificationId = _verificationId;
    if (verificationId == null) {
      throw const SmsSignInError('Ask for a new code.');
    }
    try {
      final token = await _idToken(
        PhoneAuthProvider.credential(verificationId: verificationId, smsCode: code),
      );
      if (token == null) throw const SmsSignInError('Sign-in did not finish. Try again.');
      return token;
    } on FirebaseAuthException catch (error) {
      throw _error(error);
    }
  }

  Future<String?> _idToken(PhoneAuthCredential credential) async {
    final result = await _auth.signInWithCredential(credential);
    final token = await result.user?.getIdToken();
    // Pankh keeps its own session; Firebase only proved the number.
    await _auth.signOut();
    return token;
  }

  static SmsSignInError _error(FirebaseAuthException error) => switch (error.code) {
    'invalid-verification-code' => const SmsSignInError(
      'That code is not right. Check the SMS and try again.',
      wrongCode: true,
    ),
    'session-expired' ||
    'code-expired' => const SmsSignInError('That code has expired. Ask for a new one.'),
    'too-many-requests' => const SmsSignInError(
      'Too many tries from this phone. Wait a while and try again.',
    ),
    'invalid-phone-number' => const SmsSignInError('Enter a valid 10-digit mobile number.'),
    'network-request-failed' => const SmsSignInError(
      'No connection. Check your internet and try again.',
    ),
    _ => SmsSignInError(error.message ?? 'The code could not be sent. Try again.'),
  };
}
