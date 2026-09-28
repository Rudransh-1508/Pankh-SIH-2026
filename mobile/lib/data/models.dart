/// Data returned by the Pankh API. Field names mirror the API; see backend/app/schemes/schemas.py.
library;

typedef Json = Map<String, dynamic>;

/// Picks the text for [languageCode], falling back to English.
String localised(Map<String, String> texts, String languageCode) =>
    texts[languageCode] ?? texts['en'] ?? texts.values.first;

Map<String, String> _texts(Object? json) =>
    (json as Map?)?.map((k, v) => MapEntry(k as String, v as String)) ?? const {};

class Citation {
  const Citation({
    required this.sourceTitle,
    required this.page,
    required this.clause,
    required this.url,
  });

  factory Citation.fromJson(Json json) => Citation(
    sourceTitle: json['source_title'] as String,
    page: json['page'] as int,
    clause: json['clause'] as String,
    url: json['url'] as String,
  );

  final String sourceTitle;
  final int page;
  final String clause;
  final String url;
}

class Benefit {
  const Benefit({required this.text, required this.citation});

  factory Benefit.fromJson(Json json) =>
      Benefit(text: json['text'] as String, citation: Citation.fromJson(json['citation'] as Json));

  final String text;
  final Citation citation;
}

class Scheme {
  const Scheme({
    required this.id,
    required this.name,
    required this.shortName,
    required this.summary,
    required this.systemOfRecord,
    required this.applyUrl,
    required this.applicationWindow,
    required this.benefits,
  });

  factory Scheme.fromJson(Json json) => Scheme(
    id: json['id'] as String,
    name: json['name'] as String,
    shortName: json['short_name'] as String,
    summary: json['summary'] as String,
    systemOfRecord: json['system_of_record'] as String,
    applyUrl: json['apply_url'] as String,
    applicationWindow: json['application_window'] as String?,
    benefits: [for (final b in json['benefits'] as List) Benefit.fromJson(b as Json)],
  );

  final String id;
  final String name;
  final String shortName;
  final String summary;
  final String systemOfRecord;
  final String applyUrl;
  final String? applicationWindow;
  final List<Benefit> benefits;
}

enum Outcome { pass, fail, waived, unknown }

enum EligibilityStatus { eligible, notEligible, needsInformation }

EligibilityStatus _status(String value) => switch (value) {
  'eligible' => EligibilityStatus.eligible,
  'not_eligible' => EligibilityStatus.notEligible,
  _ => EligibilityStatus.needsInformation,
};

class RuleResult {
  const RuleResult({
    required this.id,
    required this.title,
    required this.outcome,
    required this.reason,
    required this.remedy,
    required this.missingFacts,
    required this.citation,
  });

  factory RuleResult.fromJson(Json json) => RuleResult(
    id: json['id'] as String,
    title: json['title'] as String,
    outcome: Outcome.values.byName(json['outcome'] as String),
    reason: json['reason'] as String?,
    remedy: json['remedy'] as String?,
    missingFacts: [for (final f in json['missing_facts'] as List) f as String],
    citation: Citation.fromJson(json['citation'] as Json),
  );

  final String id;
  final String title;
  final Outcome outcome;
  final String? reason;
  final String? remedy;
  final List<String> missingFacts;
  final Citation citation;
}

class SchemeResult {
  const SchemeResult({
    required this.scheme,
    required this.status,
    required this.rules,
    required this.missingFacts,
  });

  factory SchemeResult.fromJson(Json json) => SchemeResult(
    scheme: Scheme.fromJson(json['scheme'] as Json),
    status: _status(json['status'] as String),
    rules: [for (final r in json['rules'] as List) RuleResult.fromJson(r as Json)],
    missingFacts: [for (final f in json['missing_facts'] as List) f as String],
  );

  final Scheme scheme;
  final EligibilityStatus status;
  final List<RuleResult> rules;
  final List<String> missingFacts;
}

class Eligibility {
  const Eligibility({
    required this.academicYearLabel,
    required this.schemes,
    required this.nextFacts,
  });

  factory Eligibility.fromJson(Json json) => Eligibility(
    academicYearLabel: json['academic_year_label'] as String,
    schemes: [for (final s in json['schemes'] as List) SchemeResult.fromJson(s as Json)],
    nextFacts: [for (final f in json['next_facts'] as List) f as String],
  );

  final String academicYearLabel;
  final List<SchemeResult> schemes;
  final List<String> nextFacts;

  SchemeResult? byId(String schemeId) =>
      schemes.where((result) => result.scheme.id == schemeId).firstOrNull;
}

enum FactKind { boolean, number, date, choice }

class Choice {
  const Choice({required this.key, required this.labels});

  factory Choice.fromJson(Json json) =>
      Choice(key: json['key'] as String, labels: _texts(json['labels']));

  final String key;
  final Map<String, String> labels;
}

class FactSpec {
  const FactSpec({
    required this.name,
    required this.kind,
    required this.question,
    required this.help,
    required this.choices,
  });

  factory FactSpec.fromJson(Json json) => FactSpec(
    name: json['name'] as String,
    kind: FactKind.values.byName(json['kind'] as String),
    question: _texts(json['question']),
    help: json['help'] == null ? null : _texts(json['help']),
    choices: [for (final c in json['choices'] as List) Choice.fromJson(c as Json)],
  );

  final String name;
  final FactKind kind;
  final Map<String, String> question;
  final Map<String, String>? help;
  final List<Choice> choices;
}

class Institute {
  const Institute({required this.id, required this.name, required this.location});

  factory Institute.fromJson(Json json) => Institute(
    id: json['id'] as int,
    name: json['name'] as String,
    location: json['location'] as String,
  );

  final int id;
  final String name;
  final String location;
}

class DocumentRef {
  const DocumentRef({required this.doctype, required this.name, required this.issuer});

  factory DocumentRef.fromJson(Json json) => DocumentRef(
    doctype: json['doctype'] as String,
    name: json['name'] as String,
    issuer: json['issuer'] as String,
  );

  final String doctype;
  final String name;
  final String issuer;
}

class VerificationIssue {
  const VerificationIssue({
    required this.factName,
    required this.kind,
    required this.message,
    required this.remedy,
  });

  factory VerificationIssue.fromJson(Json json) => VerificationIssue(
    factName: json['fact_name'] as String?,
    kind: json['kind'] as String,
    message: json['message'] as String,
    remedy: json['remedy'] as String?,
  );

  final String? factName;
  final String kind;
  final String message;
  final String? remedy;
}

class FactVerification {
  const FactVerification({required this.source, required this.verified});

  factory FactVerification.fromJson(Json json) =>
      FactVerification(source: json['source'] as String, verified: json['verified'] as bool);

  final String source;
  final bool verified;
}

class Verification {
  const Verification({
    required this.identityName,
    required this.facts,
    required this.documents,
    required this.issues,
  });

  factory Verification.fromJson(Json json) => Verification(
    identityName: (json['identity'] as Json?)?['name'] as String?,
    facts: {
      for (final entry in (json['facts'] as Json).entries)
        entry.key: FactVerification.fromJson(entry.value as Json),
    },
    documents: [for (final d in json['documents'] as List) DocumentRef.fromJson(d as Json)],
    issues: [for (final e in json['exceptions'] as List) VerificationIssue.fromJson(e as Json)],
  );

  /// The Student's name as DigiLocker confirmed it, or null before DigiLocker is linked.
  final String? identityName;
  final Map<String, FactVerification> facts;
  final List<DocumentRef> documents;
  final List<VerificationIssue> issues;

  bool get linked => identityName != null;
}
