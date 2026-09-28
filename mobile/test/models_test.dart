import 'package:flutter_test/flutter_test.dart';
import 'package:pankh/data/models.dart';

import 'support.dart';

void main() {
  test('parses eligibility exactly as the API sends it', () {
    final eligibility = Eligibility.fromJson(fixture('eligibility_post_matric') as Json);
    expect(eligibility.academicYearLabel, '2026-27');
    final first = eligibility.schemes.first;
    expect(first.scheme.id, 'post_matric');
    expect(first.status, EligibilityStatus.eligible);
    final income = first.rules.firstWhere((r) => r.id == 'post_matric.income_within_ceiling');
    expect(income.outcome, Outcome.pass);
    expect(income.citation.url, endsWith('.pdf#page=1'));
    expect(eligibility.byId('nos')!.status, EligibilityStatus.notEligible);
  });

  test('parses the fact schema with questions in every language', () {
    final specs = [
      for (final item in fixture('fact_schema') as List) FactSpec.fromJson(item as Json),
    ];
    final level = specs.firstWhere((s) => s.name == 'education_level');
    expect(level.kind, FactKind.choice);
    expect(localised(level.question, 'hi'), startsWith('इस साल'));
    expect(localised(level.choices.first.labels, 'hi'), 'कक्षा 9');
    expect(localised({'en': 'Only English'}, 'hi'), 'Only English');
  });
}
