import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:pankh/app.dart';
import 'package:pankh/data/models.dart';

import 'support.dart';

Future<void> openWallet(WidgetTester tester, Widget app) async {
  await tester.pumpWidget(app);
  await tester.pumpAndSettle();
  final container = ProviderScope.containerOf(tester.element(find.byType(MaterialApp)));
  unawaited(container.read(routerProvider).push('/wallet'));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('offers to link DigiLocker before it is linked', (tester) async {
    final (app, _, _) = await buildApp(facts: {'is_scheduled_tribe': true}, phone: '+919876543210');
    await openWallet(tester, app);

    expect(find.text('Confirm your details with DigiLocker'), findsOneWidget);
    expect(find.text('Link DigiLocker'), findsOneWidget);
    expect(find.text('Check my bank account is linked to Aadhaar'), findsNothing);
  });

  testWidgets('shows what is confirmed, from where, and what needs attention', (tester) async {
    final (app, _, _) = await buildApp(
      facts: {'is_scheduled_tribe': true, 'family_income': 180000},
      phone: '+919876543210',
      verification: fixture('verification_linked') as Json,
    );
    await openWallet(tester, app);

    expect(find.text('Linked to DigiLocker as Sunita Murmu'), findsOneWidget);
    expect(find.textContaining('income certificate is for 2023-24'), findsOneWidget);
    expect(find.text('What you can do'), findsOneWidget);
    expect(find.text('Confirmed by DigiLocker'), findsOneWidget);
    await tester.scrollUntilVisible(find.text('Caste Certificate'), 200);
    expect(find.text('e-District, Jharkhand'), findsOneWidget);
  });

  testWidgets('asks to sign in before linking', (tester) async {
    final (app, _, _) = await buildApp(facts: {'is_scheduled_tribe': true});
    await openWallet(tester, app);
    expect(find.text('Sign in with your mobile number to link DigiLocker.'), findsOneWidget);
    expect(GoRouter.of(tester.element(find.byType(Scaffold).last)), isNotNull);
  });

  testWidgets('an old income certificate offers a letter to the tehsildar', (tester) async {
    final verification = fixture('verification_linked') as Json;
    for (final issue in verification['exceptions'] as List) {
      if ((issue as Json)['kind'] == 'stale_document') issue['letter'] = 'income_certificate';
    }
    final (app, api, _) = await buildApp(
      facts: {'is_scheduled_tribe': true, 'family_income': 180000},
      phone: '+919876543210',
      verification: verification,
    );
    await openWallet(tester, app);

    await tester.tap(find.text('Write the request'));
    await tester.pumpAndSettle();
    expect(find.text('Request for an income certificate'), findsOneWidget);
    expect(find.textContaining('The Tehsildar'), findsOneWidget);
    expect(api.letters.single, startsWith('income_certificate:en:'));

    await tester.tap(find.text('हिन्दी'));
    await tester.pumpAndSettle();
    expect(find.text('आय प्रमाण पत्र के लिए आवेदन'), findsOneWidget);
  });
}
