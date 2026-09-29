import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'support.dart';

Future<void> openJago(WidgetTester tester, Widget app) async {
  await tester.pumpWidget(app);
  await tester.pumpAndSettle();
  await tester.tap(find.text('JAGO').last);
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('asks to sign in before talking to JAGO', (tester) async {
    final (app, _, _) = await buildApp(facts: {'is_scheduled_tribe': true});
    await openJago(tester, app);
    expect(find.text('Ask JAGO'), findsOneWidget);
    expect(find.textContaining('Sign in with your mobile number to talk to JAGO'), findsOneWidget);
  });

  testWidgets('a suggestion starts a conversation with cited, tappable answers', (tester) async {
    final (app, api, _) = await buildApp(
      facts: {'is_scheduled_tribe': true},
      phone: '+919876543210',
    );
    await openJago(tester, app);

    expect(find.textContaining('Ask about scholarships'), findsOneWidget);
    await tester.tap(find.text('Which scholarships can I get?'));
    await tester.pumpAndSettle();

    expect(api.jagoMessages, ['Which scholarships can I get?']);
    expect(find.text('Do you belong to a Scheduled Tribe (ST) of your state?'), findsOneWidget);
    expect(find.text('para 3.2 (I), page 3'), findsOneWidget);
    expect(find.text('Read aloud'), findsOneWidget);

    await tester.tap(find.widgetWithText(ActionChip, 'Yes'));
    await tester.pumpAndSettle();
    expect(api.jagoMessages.last, 'Yes');
  });
}
