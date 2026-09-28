import 'dart:io';

/// Base URL of the Pankh API. Override with --dart-define=PANKH_API_URL=https://...
String apiBaseUrl() {
  const configured = String.fromEnvironment('PANKH_API_URL');
  if (configured.isNotEmpty) return configured;
  // The Android emulator reaches the host machine at 10.0.2.2.
  return Platform.isAndroid ? 'http://10.0.2.2:8000' : 'http://localhost:8000';
}
