import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pankh/app.dart';
import 'package:pankh/data/api.dart';
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

  @override
  Future<List<dynamic>> factSchema() async => fixture('fact_schema') as List<dynamic>;

  @override
  Future<Json> eligibility(Json facts) async {
    requests.add(Json.of(facts));
    if (facts.isEmpty) return fixture('eligibility_empty') as Json;
    if (facts.length == 1) return fixture('eligibility_st') as Json;
    return fixture('eligibility_post_matric') as Json;
  }
}

Future<(Widget, FakeApi, SharedPreferences)> buildApp({Json facts = const {}}) async {
  SharedPreferences.setMockInitialValues({if (facts.isNotEmpty) 'facts': jsonEncode(facts)});
  final preferences = await SharedPreferences.getInstance();
  final api = FakeApi();
  final app = ProviderScope(
    overrides: [
      sharedPreferencesProvider.overrideWithValue(preferences),
      apiProvider.overrideWithValue(api),
    ],
    child: const PankhApp(),
  );
  return (app, api, preferences);
}
