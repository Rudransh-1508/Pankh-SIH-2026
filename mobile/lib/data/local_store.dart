import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'models.dart';

/// Sign-in tokens, kept in the platform's encrypted storage.
class TokenStore {
  TokenStore([FlutterSecureStorage? storage]) : _storage = storage ?? const FlutterSecureStorage();

  final FlutterSecureStorage _storage;

  Future<String?> accessToken() => _storage.read(key: 'access_token');
  Future<String?> refreshToken() => _storage.read(key: 'refresh_token');

  Future<void> save({required String access, required String refresh}) async {
    await _storage.write(key: 'access_token', value: access);
    await _storage.write(key: 'refresh_token', value: refresh);
  }

  Future<void> clear() async {
    await _storage.delete(key: 'access_token');
    await _storage.delete(key: 'refresh_token');
  }
}

/// Everything the app keeps on the phone so it works without a connection.
class LocalStore {
  LocalStore(this._prefs);

  final SharedPreferences _prefs;

  String? get languageCode => _prefs.getString('language');
  Future<void> setLanguageCode(String code) => _prefs.setString('language', code);

  String? get phone => _prefs.getString('phone');
  Future<void> setPhone(String? phone) =>
      phone == null ? _prefs.remove('phone') : _prefs.setString('phone', phone);

  /// Answers given on this phone. Kept even before sign-in.
  Json get facts => _decode(_prefs.getString('facts')) ?? {};
  Future<void> setFacts(Json facts) => _prefs.setString('facts', jsonEncode(facts));

  /// Answers not yet saved to the server, because the phone was offline.
  Set<String> get unsyncedFacts => (_prefs.getStringList('unsynced_facts') ?? const []).toSet();
  Future<void> setUnsyncedFacts(Set<String> names) =>
      _prefs.setStringList('unsynced_facts', names.toList());

  Json? get lastEligibility => _decode(_prefs.getString('eligibility'));
  Future<void> setLastEligibility(Json json) => _prefs.setString('eligibility', jsonEncode(json));

  Json? get factSchema => _decode(_prefs.getString('fact_schema'));
  Future<void> setFactSchema(Json json) => _prefs.setString('fact_schema', jsonEncode(json));

  Future<void> clearAccount() async {
    await setPhone(null);
    await _prefs.remove('facts');
    await _prefs.remove('unsynced_facts');
    await _prefs.remove('eligibility');
  }

  static Json? _decode(String? raw) => raw == null ? null : jsonDecode(raw) as Json;
}
