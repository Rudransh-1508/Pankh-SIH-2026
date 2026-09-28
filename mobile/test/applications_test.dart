import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pankh/data/models.dart';

import 'support.dart';

Future<void> openApplications(WidgetTester tester, Widget app) async {
  await tester.pumpWidget(app);
  await tester.pumpAndSettle();
  await tester.tap(find.text('Applications'));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('the tabs lead to applications', (tester) async {
    final (app, _, _) = await buildApp(facts: {'is_scheduled_tribe': true});
    await openApplications(tester, app);
    expect(find.text('My applications'), findsOneWidget);
    expect(find.text('Sign in with your mobile number to link DigiLocker.'), findsOneWidget);
  });

  testWidgets('a failed payment says why and what to do', (tester) async {
    final (app, api, _) = await buildApp(
      facts: {'is_scheduled_tribe': true},
      phone: '+919876543210',
      verification: fixture('verification_linked') as Json,
    );
    api.applicationsJson = fixture('applications_failed_payment') as Json;
    await openApplications(tester, app);

    expect(find.text('Post-Matric Scholarship for ST Students'), findsOneWidget);
    expect(find.text('Money'), findsOneWidget);
    expect(
      find.text('Your bank account is not linked with your Aadhaar for direct benefit transfer.'),
      findsOneWidget,
    );

    await tester.tap(find.text('Post-Matric Scholarship for ST Students'));
    await tester.pumpAndSettle();
    expect(find.text('Payments'), findsOneWidget);
    expect(find.textContaining('Did not reach you'), findsOneWidget);
  });

  testWidgets('asks to link DigiLocker to find applications', (tester) async {
    final (app, api, _) = await buildApp(
      facts: {'is_scheduled_tribe': true},
      phone: '+919876543210',
    );
    api.applicationsJson = {
      'linked': false,
      'stale_sources': <dynamic>[],
      'warning': null,
      'applications': <dynamic>[],
    };
    await openApplications(tester, app);
    expect(find.textContaining('Link DigiLocker so we can find your applications'), findsOneWidget);
  });
}
