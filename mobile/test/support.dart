import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pankh/app.dart';
import 'package:pankh/data/api.dart';
import 'package:pankh/data/document_capture.dart';
import 'package:pankh/data/local_store.dart';
import 'package:pankh/data/models.dart';
import 'package:pankh/state/providers.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// A response recorded from the real API by tool/refresh_fixtures.sh.
dynamic fixture(String name) => jsonDecode(File('test/fixtures/$name.json').readAsStringSync());

/// Answers from recorded API responses, choosing one by what the Student has answered.
class FakeApi extends PankhApi {
  FakeApi() : super(baseUrl: 'http://test', tokens: TokenStore());

  final requests = <Json>[];

  /// What /me/verification returns; null means DigiLocker is not linked yet.
  Json? verificationJson;

  /// What /me/applications returns.
  Json applicationsJson = {
    'linked': true,
    'stale_sources': <dynamic>[],
    'warning': null,
    'applications': <dynamic>[],
  };

  @override
  Future<Json> applications() async => applicationsJson;

  /// Every message sent to JAGO, and a scripted reply.
  final jagoMessages = <String>[];

  @override
  Future<List<dynamic>> jagoConversation() async => const [];

  @override
  Future<List<dynamic>> reminders() async => const [];

  @override
  Future<Json> family() async => {
    'children': [
      {
        'link_id': 'l1',
        'name': 'Sunita Murmu',
        'eligible': ['Pre-Matric'],
        'answers_needed': false,
        'applications': [
          {
            'scheme': 'Pre-Matric',
            'stage': 'disbursing',
            'waiting_on': null,
            'received': 1625,
            'needs_action': false,
          },
        ],
        'issues': 1,
        'applications_available': true,
      },
    ],
    'guardians': <dynamic>[],
  };

  @override
  Future<String> familyInvite() async => 'ABCD 2345';

  /// What /me/documents/uploads returns, and what the next upload is answered with.
  final uploadsJson = <Json>[];
  Json? nextUploadOutcome;
  final uploadedTexts = <String>[];

  @override
  Future<List<dynamic>> uploads() async => uploadsJson;

  @override
  Future<Json> uploadDocument({
    required String kind,
    required String path,
    required String contentType,
    required String text,
  }) async {
    uploadedTexts.add(text);
    final outcome = nextUploadOutcome!;
    if (outcome['document'] case final Json document) uploadsJson.insert(0, document);
    return outcome;
  }

  @override
  Future<void> deleteUpload(String id) async => uploadsJson.removeWhere((d) => d['id'] == id);

  @override
  Future<Json> schemePath(Json facts) async => fixture('scheme_path') as Json;

  @override
  Future<Json> mySchemePath() async => fixture('scheme_path') as Json;

  @override
  Future<Json> talkToJago(String message, String language) async {
    jagoMessages.add(message);
    return {
      'role': 'assistant',
      'text': 'Do you belong to a Scheduled Tribe (ST) of your state?',
      'sources': [
        {'title': 'para 3.2 (I), page 3', 'url': 'https://tribal.nic.in/x.pdf#page=3'},
      ],
      'suggestions': ['Yes', 'No'],
      'asking': 'is_scheduled_tribe',
    };
  }

  @override
  Future<List<dynamic>> factSchema() async => fixture('fact_schema') as List<dynamic>;

  /// Facts held by the fake server for a signed-in Student.
  final serverFacts = <String, dynamic>{};

  @override
  Future<void> saveFacts(Json facts) async {
    for (final entry in facts.entries) {
      entry.value == null ? serverFacts.remove(entry.key) : serverFacts[entry.key] = entry.value;
    }
  }

  @override
  Future<Json> myFacts() async => Json.of(serverFacts);

  @override
  Future<Json> myEligibility() => eligibility(serverFacts);

  @override
  Future<Json> verification() async =>
      verificationJson ??
      {
        'identity': null,
        'facts': <String, dynamic>{},
        'documents': <dynamic>[],
        'exceptions': <dynamic>[],
      };

  @override
  Future<Json> eligibility(Json facts) async {
    requests.add(Json.of(facts));
    if (facts.isEmpty) return fixture('eligibility_empty') as Json;
    if (facts.length == 1) return fixture('eligibility_st') as Json;
    return fixture('eligibility_post_matric') as Json;
  }
}

Future<(Widget, FakeApi, SharedPreferences)> buildApp({
  Json facts = const {},
  String? phone,
  Json? verification,
  DocumentCapture? capture,
}) async {
  SharedPreferences.setMockInitialValues({
    if (facts.isNotEmpty) 'facts': jsonEncode(facts),
    'phone': ?phone,
  });
  final preferences = await SharedPreferences.getInstance();
  final api = FakeApi()..verificationJson = verification;
  final app = ProviderScope(
    overrides: [
      sharedPreferencesProvider.overrideWithValue(preferences),
      apiProvider.overrideWithValue(api),
      if (capture != null) documentCaptureProvider.overrideWithValue(capture),
    ],
    child: const PankhApp(),
  );
  return (app, api, preferences);
}

/// Stands in for the camera and on-device text recognition.
class FakeCapture extends DocumentCapture {
  FakeCapture(this.text);

  final String text;

  @override
  Future<CapturedDocument?> capture({required bool fromCamera}) async =>
      CapturedDocument(path: '/tmp/photo.jpg', contentType: 'image/jpeg', text: text);
}
