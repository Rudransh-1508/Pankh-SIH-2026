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
    required this.isMota,
    required this.provider,
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
    isMota: json['kind'] == 'mota',
    provider: json['provider'] as String,
    name: json['name'] as String,
    shortName: json['short_name'] as String,
    summary: json['summary'] as String,
    systemOfRecord: json['system_of_record'] as String,
    applyUrl: json['apply_url'] as String,
    applicationWindow: json['application_window'] as String?,
    benefits: [for (final b in json['benefits'] as List) Benefit.fromJson(b as Json)],
  );

  final String id;

  /// One of the five Ministry of Tribal Affairs Schemes, rather than a Catalogue Scheme.
  final bool isMota;
  final String provider;
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

/// A photo of a Document the Student uploaded, and what became of it.
class UploadedDocument {
  const UploadedDocument({
    required this.id,
    required this.kind,
    required this.status,
    required this.fields,
    this.message,
    this.remedy,
    this.reviewerNote,
  });

  factory UploadedDocument.fromJson(Json json) => UploadedDocument(
    id: json['id'] as String,
    kind: json['kind'] as String,
    status: json['status'] as String,
    fields: json['fields'] as Json,
    message: json['message'] as String?,
    remedy: json['remedy'] as String?,
    reviewerNote: json['reviewer_note'] as String?,
  );

  final String id;
  final String kind;

  /// verified | with_reviewer | accepted | rejected
  final String status;
  final Json fields;
  final String? message;
  final String? remedy;
  final String? reviewerNote;
}

/// What happened to one upload: confirmed, sent to an officer, or not readable.
class UploadOutcome {
  const UploadOutcome({
    required this.readable,
    required this.message,
    required this.problems,
    required this.document,
  });

  factory UploadOutcome.fromJson(Json json) => UploadOutcome(
    readable: json['readable'] as bool,
    message: json['message'] as String,
    problems: [for (final p in json['problems'] as List) p as String],
    document: json['document'] == null ? null : UploadedDocument.fromJson(json['document'] as Json),
  );

  final bool readable;
  final String message;
  final List<String> problems;
  final UploadedDocument? document;

  bool get verified => document?.status == 'verified';
}

class VerificationIssue {
  const VerificationIssue({
    required this.factName,
    required this.kind,
    required this.message,
    required this.remedy,
    this.id,
    this.letter,
  });

  factory VerificationIssue.fromJson(Json json) => VerificationIssue(
    id: json['id'] as String?,
    factName: json['fact_name'] as String?,
    kind: json['kind'] as String,
    message: json['message'] as String,
    remedy: json['remedy'] as String?,
    letter: json['letter'] as String?,
  );

  final String? id;

  /// A request letter that helps fix this, if one does.
  final String? letter;
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

class Problem {
  const Problem({required this.reason, required this.fix, this.letter});

  factory Problem.fromJson(Json json) => Problem(
    reason: json['reason'] as String,
    fix: json['fix'] as String,
    letter: json['letter'] as String?,
  );

  /// A request letter that helps with the fix, if one does.
  final String? letter;

  static Problem? maybe(Object? json) => json == null ? null : Problem.fromJson(json as Json);

  final String reason;
  final String fix;
}

enum InstalmentStatus { credited, pending, onHold, failed }

class Instalment {
  const Instalment({
    required this.number,
    required this.amount,
    required this.status,
    required this.date,
    required this.reference,
    required this.problem,
  });

  factory Instalment.fromJson(Json json) => Instalment(
    number: json['number'] as int,
    amount: json['amount'] as int,
    status: switch (json['status'] as String) {
      'credited' => InstalmentStatus.credited,
      'failed' => InstalmentStatus.failed,
      'on_hold' => InstalmentStatus.onHold,
      _ => InstalmentStatus.pending,
    },
    date: (json['credited_on'] ?? json['initiated_on']) as String?,
    reference: json['reference'] as String?,
    problem: Problem.maybe(json['problem']),
  );

  final int number;
  final int amount;
  final InstalmentStatus status;
  final String? date;
  final String? reference;
  final Problem? problem;
}

enum ApplicationStage { submitted, underVerification, sanctioned, disbursing, closed, rejected }

class TrackedApplication {
  const TrackedApplication({
    required this.sourceSystem,
    required this.externalId,
    required this.schemeName,
    required this.academicYear,
    required this.stage,
    required this.statusText,
    required this.waitingOn,
    required this.daysWaiting,
    required this.stalled,
    required this.deficiency,
    required this.received,
    required this.timeline,
    required this.instalments,
  });

  factory TrackedApplication.fromJson(Json json) => TrackedApplication(
    sourceSystem: json['source_system'] as String,
    externalId: json['external_id'] as String,
    schemeName: json['scheme_name'] as String,
    academicYear: json['academic_year'] as String,
    stage: switch (json['stage'] as String) {
      'under_verification' => ApplicationStage.underVerification,
      'sanctioned' => ApplicationStage.sanctioned,
      'disbursing' => ApplicationStage.disbursing,
      'closed' => ApplicationStage.closed,
      'rejected' => ApplicationStage.rejected,
      _ => ApplicationStage.submitted,
    },
    statusText: json['status_text'] as String,
    waitingOn: json['waiting_on'] as String?,
    daysWaiting: json['days_waiting'] as int?,
    stalled: json['stalled'] as bool,
    deficiency: Problem.maybe(json['deficiency']),
    received: json['received'] as int,
    timeline: [
      for (final t in json['timeline'] as List) ((t as Json)['label'] as String, t['on'] as String),
    ],
    instalments: [for (final i in json['instalments'] as List) Instalment.fromJson(i as Json)],
  );

  final String sourceSystem;
  final String externalId;
  final String schemeName;
  final String academicYear;
  final ApplicationStage stage;
  final String statusText;
  final String? waitingOn;
  final int? daysWaiting;
  final bool stalled;
  final Problem? deficiency;
  final int received;
  final List<(String, String)> timeline;
  final List<Instalment> instalments;

  bool get needsAction =>
      deficiency != null || instalments.any((i) => i.problem != null) || stalled;
}

class Applications {
  const Applications({
    required this.linked,
    required this.staleSources,
    required this.warning,
    required this.items,
  });

  factory Applications.fromJson(Json json) => Applications(
    linked: json['linked'] as bool,
    staleSources: [for (final s in json['stale_sources'] as List) s as String],
    warning: json['warning'] as String?,
    items: [for (final a in json['applications'] as List) TrackedApplication.fromJson(a as Json)],
  );

  final bool linked;
  final List<String> staleSources;
  final String? warning;
  final List<TrackedApplication> items;
}

class ChatMessage {
  const ChatMessage({
    required this.fromStudent,
    required this.text,
    this.sources = const [],
    this.suggestions = const [],
  });

  factory ChatMessage.fromJson(Json json) => ChatMessage(
    fromStudent: json['role'] == 'user',
    text: json['text'] as String,
    sources: [
      for (final s in json['sources'] as List? ?? const [])
        ((s as Json)['title'] as String, s['url'] as String),
    ],
    suggestions: [for (final s in json['suggestions'] as List? ?? const []) s as String],
  );

  final bool fromStudent;
  final String text;
  final List<(String, String)> sources;
  final List<String> suggestions;
}

class PathOption {
  const PathOption({
    required this.scheme,
    required this.value,
    required this.citation,
    required this.condition,
  });

  factory PathOption.fromJson(Json json) => PathOption(
    scheme: json['scheme'] as String,
    value: json['value'] as String,
    citation: Citation(
      sourceTitle: (json['citation'] as Json)['source_title'] as String,
      page: (json['citation'] as Json)['page'] as int,
      clause: (json['citation'] as Json)['clause'] as String,
      url: (json['citation'] as Json)['url'] as String,
    ),
    condition: json['condition'] as String?,
  );

  final String scheme;
  final String value;
  final Citation citation;
  final String? condition;
}

class PathStage {
  const PathStage({
    required this.level,
    required this.label,
    required this.recommended,
    required this.needsAnswers,
    required this.opportunities,
  });

  factory PathStage.fromJson(Json json) => PathStage(
    level: json['level'] as String,
    label: json['label'] as String,
    recommended: json['recommended'] == null
        ? null
        : PathOption.fromJson(json['recommended'] as Json),
    needsAnswers: json['needs_answers'] as bool,
    opportunities: [for (final o in json['opportunities'] as List) PathOption.fromJson(o as Json)],
  );

  final String level;
  final String label;
  final PathOption? recommended;
  final bool needsAnswers;
  final List<PathOption> opportunities;
}

/// One thing to have ready for next year's application.
class RenewalCheck {
  const RenewalCheck({required this.id, required this.done});

  factory RenewalCheck.fromJson(Json json) =>
      RenewalCheck(id: json['id'] as String, done: json['done'] as bool);

  /// promoted | income | bank | institution
  final String id;
  final bool done;
}

/// Next year's application for a Scheme the Student holds now.
class RenewalPlan {
  const RenewalPlan({
    required this.scheme,
    required this.nextYear,
    required this.continuing,
    required this.instead,
    required this.checks,
    required this.applyOn,
    required this.applyUrl,
  });

  factory RenewalPlan.fromJson(Json json) => RenewalPlan(
    scheme: json['scheme'] as String,
    nextYear: json['next_year'] as String,
    continuing: json['continuing'] as bool,
    instead: json['instead'] as String?,
    checks: [for (final c in json['checks'] as List) RenewalCheck.fromJson(c as Json)],
    applyOn: json['apply_on'] as String,
    applyUrl: json['apply_url'] as String,
  );

  final String scheme;

  /// Like "2027-28".
  final String nextYear;

  /// False when the Scheme ends this year and next year needs a fresh application.
  final bool continuing;
  final String? instead;
  final List<RenewalCheck> checks;
  final String applyOn;
  final String applyUrl;

  /// The financial year an income certificate must be for, like "2026-27".
  String get incomeYear {
    final start = int.parse(nextYear.substring(0, 4));
    return '${start - 1}-${(start % 100).toString().padLeft(2, '0')}';
  }
}
