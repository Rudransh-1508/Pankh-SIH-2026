import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pankh/app.dart';
import 'package:pankh/data/sms_sign_in.dart';

import 'support.dart';

class FakeSms implements SmsSignIn {
  final sentTo = <String>[];
  final automatic = StreamController<String>.broadcast();

  @override
  Stream<String> get verifiedAutomatically => automatic.stream;

  @override
  Future<void> send(String phoneE164) async => sentTo.add(phoneE164);

  @override
  Future<String> confirm(String code) async {
    if (code != '654321') {
      throw const SmsSignInError('That code is not right.', wrongCode: true);
    }
    return 'firebase-id-token';
  }
}

Future<void> openSignIn(WidgetTester tester, Widget app) async {
  await tester.pumpWidget(app);
  await tester.pumpAndSettle();
  final container = ProviderScope.containerOf(tester.element(find.byType(MaterialApp)));
  unawaited(container.read(routerProvider).push('/sign-in'));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('a real number signs in with a code sent by SMS', (tester) async {
    final sms = FakeSms();
    final (app, api, _) = await buildApp(facts: {'is_scheduled_tribe': true}, smsSignIn: sms);
    await openSignIn(tester, app);

    await tester.enterText(find.byType(TextField), '9812345678');
    await tester.pump();
    await tester.tap(find.text('Send code'));
    await tester.pumpAndSettle();
    expect(sms.sentTo, ['+919812345678']);
    expect(api.signIns, isEmpty); // the API sent nothing

    await tester.enterText(find.byType(TextField), '111111');
    await tester.pumpAndSettle();
    expect(find.text('That code is not right.'), findsOneWidget);
    await tester.enterText(find.byType(TextField), '654321');
    await tester.pumpAndSettle();
    expect(api.signIns, ['sms token firebase-id-token']);
  });

  testWidgets('the phone reading the SMS by itself signs in without typing', (tester) async {
    final sms = FakeSms();
    final (app, api, _) = await buildApp(facts: {'is_scheduled_tribe': true}, smsSignIn: sms);
    await openSignIn(tester, app);
    await tester.enterText(find.byType(TextField), '9812345678');
    await tester.pump();
    await tester.tap(find.text('Send code'));
    await tester.pumpAndSettle();

    sms.automatic.add('auto-token');
    await tester.pumpAndSettle();
    expect(api.signIns, ['sms token auto-token']);
  });

  testWidgets('demo numbers keep using the demo codes', (tester) async {
    final sms = FakeSms();
    final (app, api, _) = await buildApp(facts: {'is_scheduled_tribe': true}, smsSignIn: sms);
    await openSignIn(tester, app);
    await tester.enterText(find.byType(TextField), '9000000176');
    await tester.pump();
    await tester.tap(find.text('Send code'));
    await tester.pumpAndSettle();
    expect(sms.sentTo, isEmpty);
    expect(api.signIns, ['code requested for 9000000176']);
  });
}
