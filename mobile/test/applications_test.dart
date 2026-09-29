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

  testWidgets('next year shows what to get ready for the renewal', (tester) async {
    final (app, api, _) = await buildApp(
      facts: {'is_scheduled_tribe': true},
      phone: '+919876543210',
      verification: fixture('verification_linked') as Json,
    );
    api.applicationsJson = fixture('applications_failed_payment') as Json;
    // Shaped exactly like /me/renewals for a Class X Pre-Matric holder.
    api.renewalsJson = [
      {
        'scheme_id': 'pre_matric',
        'scheme': 'Pre-Matric',
        'held_year': '2026-27',
        'next_year': '2027-28',
        'next_level': 'class_11',
        'continuing': false,
        'instead': 'Post-Matric',
        'status': 'not_eligible',
        'unmet': <dynamic>[],
        'checks': [
          {'id': 'promoted', 'text': '', 'done': false, 'fact': null},
          {'id': 'income', 'text': '', 'done': false, 'fact': 'family_income'},
          {'id': 'bank', 'text': '', 'done': true, 'fact': 'has_aadhaar_seeded_bank_account'},
        ],
        'apply_on': 'National Scholarship Portal',
        'apply_url': 'https://scholarships.gov.in',
        'window': null,
        'carried': <dynamic>[],
      },
    ];
    await openApplications(tester, app);

    await tester.scrollUntilVisible(
      find.text('Apply on National Scholarship Portal'),
      200,
      scrollable: find.byType(Scrollable).last,
    );
    expect(find.text('Next year'), findsOneWidget);
    expect(find.text('Pre-Matric ends this year'), findsOneWidget);
    expect(find.text('For 2027-28, apply fresh for Post-Matric.'), findsOneWidget);
    expect(find.text('Income certificate for 2026-27'), findsOneWidget);
    expect(find.text('Bank account linked to Aadhaar'), findsOneWidget);
  });
}
