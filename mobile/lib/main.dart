import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'app.dart';
import 'data/sms_sign_in.dart';
import 'state/providers.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final preferences = await SharedPreferences.getInstance();
  runApp(
    ProviderScope(
      overrides: [
        sharedPreferencesProvider.overrideWithValue(preferences),
        smsSignInProvider.overrideWithValue(await _firebaseSignIn()),
      ],
      child: const PankhApp(),
    ),
  );
}

/// Real SMS sign-in, when the build includes a Firebase configuration (google-services.json).
/// Without one, the API's own codes are used, as for demo numbers.
Future<SmsSignIn?> _firebaseSignIn() async {
  try {
    await Firebase.initializeApp();
    return FirebaseSmsSignIn();
  } catch (_) {
    return null;
  }
}
