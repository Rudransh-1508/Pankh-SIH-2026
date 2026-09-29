import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pankh/app.dart';

import 'support.dart';

Future<void> openHelp(WidgetTester tester, Widget app) async {
  await tester.pumpWidget(app);
  await tester.pumpAndSettle();
  final container = ProviderScope.containerOf(tester.element(find.byType(MaterialApp)));
  unawaited(container.read(routerProvider).push('/help'));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('someone not yet a facilitator sees how to ask', (tester) async {
    final (app, _, _) = await buildApp(facts: {'is_scheduled_tribe': true}, phone: '+919876543210');
    await openHelp(tester, app);
    expect(find.text('Ask to be a facilitator'), findsOneWidget);
    expect(find.text('School or organisation'), findsOneWidget);
  });

  testWidgets('an approved facilitator answers a question for a student', (tester) async {
    final (app, api, _) = await buildApp(
      facts: {'is_scheduled_tribe': true},
      phone: '+919876543210',
    );
    api.facilitatorJson = {'id': 'f1', 'status': 'approved'};
    // Shaped exactly like GET /me/facilitator/students.
    api.helpedJson = [
      {
        'student_id': 's1',
        'link_id': 'l1',
        'name': '…5670',
        'phone': '…5670',
        'eligible': <dynamic>[],
        'answers_needed': 5,
        'next_question': {
          'fact': 'is_scheduled_tribe',
          'question': 'Do you belong to a Scheduled Tribe of your state?',
          'kind': 'boolean',
          'choices': <dynamic>[],
        },
        'issues': 0,
      },
    ];
    await openHelp(tester, app);

    expect(find.text('5 questions left'), findsOneWidget);
    expect(find.text('Do you belong to a Scheduled Tribe of your state?'), findsOneWidget);
    await tester.tap(find.text('Yes'));
    await tester.pumpAndSettle();
    expect(api.facilitatorAnswers, [
      {'is_scheduled_tribe': true},
    ]);
    expect(find.text('Add a student'), findsOneWidget);
  });
}
