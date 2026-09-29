import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pankh/app.dart';
import 'package:pankh/data/models.dart';

import 'support.dart';

const _certificateText =
    'GOVERNMENT OF JHARKHAND\nCASTE CERTIFICATE\nCertificate No. : JH/CS/92777/2012';

/// Shaped exactly like the API's answer for a paper certificate not in e-District.
Json _withReviewer() => {
  'readable': true,
  'message':
      'It is not in the Jharkhand e-District register (older paper certificates often are not), '
      'so an officer will check the photo of your caste certificate.',
  'problems': <dynamic>[],
  'verified_facts': <dynamic>[],
  'document': {
    'id': '389c027a-7f15-4e0b-867c-fccea077d72d',
    'kind': 'caste_certificate',
    'name': 'caste certificate',
    'fact_name': 'is_scheduled_tribe',
    'status': 'with_reviewer',
    'fields': {'certificate_number': 'JH/CS/92777/2012', 'state': 'Jharkhand'},
    'message':
        'It is not in the Jharkhand e-District register (older paper certificates often are '
        'not), so an officer will check the photo of your caste certificate.',
    'remedy':
        'No action needed from you. A certificate issued through e-District can be confirmed '
        'at once, so ask for one when you next renew it.',
    'reviewer_note': null,
    'created_at': '2026-09-29T03:39:46.960734Z',
  },
};

Future<void> _openWallet(WidgetTester tester, Widget app) async {
  await tester.pumpWidget(app);
  await tester.pumpAndSettle();
  final container = ProviderScope.containerOf(tester.element(find.byType(MaterialApp)));
  unawaited(container.read(routerProvider).push('/wallet'));
  await tester.pumpAndSettle();
}

Future<void> _photograph(WidgetTester tester, String kind) async {
  await tester.scrollUntilVisible(find.text(kind), 200, scrollable: find.byType(Scrollable).last);
  await tester.tap(find.text(kind));
  await tester.pumpAndSettle();
  await tester.tap(find.text('Take a photo'));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('a photographed certificate goes to an officer and is listed', (tester) async {
    final (app, api, _) = await buildApp(
      facts: {'is_scheduled_tribe': true},
      phone: '+919876543210',
      capture: FakeCapture(_certificateText),
    );
    api.nextUploadOutcome = _withReviewer();
    await _openWallet(tester, app);

    await _photograph(tester, 'Caste certificate');
    expect(api.uploadedTexts, [_certificateText]);
    expect(find.text('Sent to an officer'), findsOneWidget);
    expect(find.textContaining('not in the Jharkhand e-District register'), findsOneWidget);
    expect(find.textContaining('ask for one when you next renew it'), findsOneWidget);

    await tester.tap(find.text('Done'));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(
      find.text('With an officer'),
      200,
      scrollable: find.byType(Scrollable).last,
    );
    expect(find.text('Your photos'), findsOneWidget);
  });

  testWidgets('an unreadable photo offers to take it again', (tester) async {
    final (app, api, _) = await buildApp(
      facts: {'is_scheduled_tribe': true},
      phone: '+919876543210',
      capture: FakeCapture('blurry'),
    );
    api.nextUploadOutcome = {
      'readable': false,
      'message':
          'We could not read any text in this photo. Take the photo again in daylight, with the '
          'whole page flat and filling the frame, and no shadow or glare on the text.',
      'problems': ['We could not read any text in this photo.'],
      'verified_facts': <dynamic>[],
      'document': null,
    };
    await _openWallet(tester, app);

    await _photograph(tester, 'Income certificate');
    expect(find.text('We could not read it'), findsOneWidget);
    expect(find.textContaining('in daylight'), findsOneWidget);
    expect(find.text('Take it again'), findsOneWidget);
    await tester.tap(find.text('Cancel'));
    await tester.pumpAndSettle();
    expect(find.text('Your photos'), findsNothing);
  });

  testWidgets('a photo can be deleted', (tester) async {
    final (app, api, _) = await buildApp(
      facts: {'is_scheduled_tribe': true},
      phone: '+919876543210',
    );
    api.uploadsJson.add(_withReviewer()['document'] as Json);
    await _openWallet(tester, app);

    await tester.scrollUntilVisible(
      find.text('With an officer'),
      200,
      scrollable: find.byType(Scrollable).last,
    );
    // Bring the row clear of the navigation bar before tapping it.
    await tester.drag(find.byType(Scrollable).last, const Offset(0, -300));
    await tester.pumpAndSettle();
    await tester.tap(find.text('With an officer'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Delete photo'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(TextButton, 'Delete photo').last);
    await tester.pumpAndSettle();
    expect(api.uploadsJson, isEmpty);
    expect(find.text('Your photos'), findsNothing);
  });
}
