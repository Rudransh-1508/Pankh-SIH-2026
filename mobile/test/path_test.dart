import 'package:flutter_test/flutter_test.dart';

import 'support.dart';

void main() {
  testWidgets('the path shows what to hold at each stage and what to aim for', (tester) async {
    final (app, _, _) = await buildApp(
      facts: {'is_scheduled_tribe': true, 'education_level': 'undergraduate'},
    );
    await tester.pumpWidget(app);
    await tester.pumpAndSettle();

    await tester.scrollUntilVisible(find.text('See my path'), 300);
    await tester.tap(find.text('See my path'));
    await tester.pumpAndSettle();

    expect(find.text('Your scholarship path'), findsOneWidget);
    expect(find.text('2026-27'), findsOneWidget);
    expect(find.text('Hold: Post-Matric'), findsWidgets);
    await tester.scrollUntilVisible(find.text('Aim for: Top Class'), 300);
    expect(find.textContaining('Top Class institutes'), findsOneWidget);
  });
}
