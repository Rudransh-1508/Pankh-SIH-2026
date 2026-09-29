import 'package:flutter/widgets.dart';

import '../data/models.dart';
import '../l10n/generated/app_localizations.dart';

/// An answer as a Student would read it: "Yes", "Class IX", "₹ 1,80,000", "14 / 03 / 2008".
String answerText(BuildContext context, FactSpec spec, Object value) {
  final l10n = AppLocalizations.of(context);
  final language = Localizations.localeOf(context).languageCode;
  return switch (spec.kind) {
    FactKind.boolean => value == true ? l10n.yes : l10n.no,
    FactKind.choice => localised(spec.choices.firstWhere((c) => c.key == value).labels, language),
    FactKind.number =>
      spec.name == 'family_income' ? '₹ ${indianDigits((value as num).round())}' : '$value%',
    FactKind.date => value.toString().split('-').reversed.join(' / '),
  };
}

/// 180000 -> 1,80,000
String indianDigits(int amount) {
  final digits = amount.toString();
  if (digits.length <= 3) return digits;
  var head = digits.substring(0, digits.length - 3);
  final groups = <String>[];
  while (head.length > 2) {
    groups.insert(0, head.substring(head.length - 2));
    head = head.substring(0, head.length - 2);
  }
  if (head.isNotEmpty) groups.insert(0, head);
  return '${groups.join(',')},${digits.substring(digits.length - 3)}';
}

/// Where a confirmed Fact came from, in words a Student recognises.
String sourceName(String source) => switch (source) {
  'digilocker' => 'DigiLocker',
  'aishe' => 'AISHE',
  'udise' => 'UDISE+',
  'nta' => 'National Testing Agency',
  'npci' => 'NPCI',
  'edistrict' => 'e-District',
  'apaar' => 'APAAR',
  'reviewer' => 'an officer',
  'uploaded' => 'your photo',
  _ => source,
};
