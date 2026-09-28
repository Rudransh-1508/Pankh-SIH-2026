import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'support.dart';

void main() {
  testWidgets('a new Student answers questions and their answers are kept', (tester) async {
    final (app, api, preferences) = await buildApp();
    await tester.pumpWidget(app);
    await tester.pumpAndSettle();

    expect(find.text('Find the scholarships you can get'), findsOneWidget);
    await tester.tap(find.text('Check my scholarships'));
    await tester.pumpAndSettle();

    expect(find.text('Do you belong to a Scheduled Tribe (ST) of your state?'), findsOneWidget);
    await tester.tap(find.text('Yes'));
    await tester.pumpAndSettle();

    expect(find.text('What are you studying this year, or applying to study?'), findsOneWidget);
    expect(jsonDecode(preferences.getString('facts')!), {'is_scheduled_tribe': true});
    expect(api.requests.last, {'is_scheduled_tribe': true});
  });

  testWidgets('"I\'m not sure" moves on without recording an answer', (tester) async {
    final (app, _, preferences) = await buildApp();
    await tester.pumpWidget(app);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Check my scholarships'));
    await tester.pumpAndSettle();

    await tester.tap(find.text("I'm not sure"));
    await tester.pumpAndSettle();

    expect(find.text('What are you studying this year, or applying to study?'), findsOneWidget);
    expect(preferences.getString('facts'), isNull);
  });

  testWidgets('a returning Student sees their results first', (tester) async {
    final (app, _, _) = await buildApp(
      facts: {'is_scheduled_tribe': true, 'education_level': 'undergraduate'},
    );
    await tester.pumpWidget(app);
    await tester.pumpAndSettle();

    expect(find.text('Your scholarships'), findsOneWidget);
    expect(find.text('You qualify for 1 scholarship.'), findsOneWidget);
    expect(find.text('Post-Matric'), findsOneWidget);
  });

  testWidgets('a scheme page explains each Rule and cites its source', (tester) async {
    final (app, _, _) = await buildApp(
      facts: {'is_scheduled_tribe': true, 'education_level': 'undergraduate'},
    );
    await tester.pumpWidget(app);
    await tester.pumpAndSettle();

    await tester.tap(find.text('Post-Matric'));
    await tester.pumpAndSettle();

    expect(find.text('Post-Matric Scholarship for ST Students'), findsOneWidget);
    final income = find.text('Family income is at most ₹2,50,000 a year');
    await tester.scrollUntilVisible(income, 300, scrollable: find.byType(Scrollable).first);
    expect(income, findsOneWidget);
    expect(find.textContaining('letter of 23 May 2013', findRichText: true), findsWidgets);
  });

  testWidgets('switching to Hindi changes the interface language', (tester) async {
    final (app, _, preferences) = await buildApp();
    await tester.pumpWidget(app);
    await tester.pumpAndSettle();

    await tester.tap(find.text('हिन्दी'));
    await tester.pumpAndSettle();

    expect(find.text('मेरी छात्रवृत्तियाँ देखें'), findsOneWidget);
    expect(preferences.getString('language'), 'hi');
    expect(find.byType(MaterialApp), findsOneWidget);
  });
}
