import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pankh/app.dart';
import 'package:pankh/screens/family_screen.dart';

import 'support.dart';

void main() {
  testWidgets('a guardian sees each child and can share their own code', (tester) async {
    final (app, _, _) = await buildApp(facts: {'is_scheduled_tribe': true}, phone: '+919876543210');
    await tester.pumpWidget(app);
    await tester.pumpAndSettle();
    final container = ProviderScope.containerOf(tester.element(find.byType(MaterialApp)));
    unawaited(container.read(routerProvider).push('/family'));
    await tester.pumpAndSettle();

    expect(find.text('Sunita Murmu'), findsOneWidget);
    expect(find.text('Qualifies for: Pre-Matric'), findsOneWidget);
    expect(find.text('Pre-Matric · disbursing · ₹ 1,625'), findsOneWidget);
    expect(find.text('1 thing needs attention'), findsOneWidget);

    await tester.scrollUntilVisible(
      find.text('Get a family code'),
      300,
      scrollable: find
          .descendant(of: find.byType(FamilyScreen), matching: find.byType(Scrollable))
          .first,
    );
    await tester.tap(find.text('Get a family code'));
    await tester.pumpAndSettle();
    expect(find.text('ABCD 2345'), findsOneWidget);
  });
}
