import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../config.dart';
import '../data/api.dart';
import '../data/document_capture.dart';
import '../data/upload_queue.dart';
import '../data/voice_line.dart';
import '../data/local_store.dart';
import '../data/models.dart';

/// Overridden in main() once SharedPreferences has loaded.
final sharedPreferencesProvider = Provider<SharedPreferences>(
  (ref) => throw UnimplementedError('sharedPreferencesProvider must be overridden'),
);

final localStoreProvider = Provider((ref) => LocalStore(ref.watch(sharedPreferencesProvider)));

final tokenStoreProvider = Provider((ref) => TokenStore());

final apiProvider = Provider((ref) {
  final api = PankhApi(baseUrl: apiBaseUrl(), tokens: ref.watch(tokenStoreProvider));
  api.onSignedOut = () => ref.read(sessionProvider.notifier).forget();
  return api;
});

const supportedLanguages = ['en', 'hi'];

class LanguageController extends Notifier<Locale> {
  @override
  Locale build() {
    final saved = ref.read(localStoreProvider).languageCode;
    if (saved != null) return Locale(saved);
    final device = WidgetsBinding.instance.platformDispatcher.locale.languageCode;
    return Locale(supportedLanguages.contains(device) ? device : 'en');
  }

  Future<void> set(String code) async {
    await ref.read(localStoreProvider).setLanguageCode(code);
    state = Locale(code);
  }
}

final languageProvider = NotifierProvider<LanguageController, Locale>(LanguageController.new);

/// The signed-in phone number, or null when not signed in.
class SessionController extends Notifier<String?> {
  @override
  String? build() => ref.read(localStoreProvider).phone;

  Future<void> signedIn(String phone) async {
    await ref.read(localStoreProvider).setPhone(phone);
    state = phone;
  }

  /// Forget the session after the server ended it. Answers stay on the phone.
  Future<void> forget() async {
    await ref.read(localStoreProvider).setPhone(null);
    state = null;
  }

  Future<void> signOut() async {
    await ref.read(apiProvider).signOut();
    await ref.read(localStoreProvider).clearAccount();
    state = null;
    ref.invalidate(profileProvider);
  }
}

final sessionProvider = NotifierProvider<SessionController, String?>(SessionController.new);

/// Every Fact the Rules use, keyed by name. Cached so questions work offline.
final factSchemaProvider = FutureProvider<Map<String, FactSpec>>((ref) async {
  final store = ref.read(localStoreProvider);
  List<dynamic> raw;
  try {
    raw = await ref.read(apiProvider).factSchema();
    await store.setFactSchema({'facts': raw});
  } on ApiException catch (error) {
    final cached = store.factSchema;
    if (!error.isOffline || cached == null) rethrow;
    raw = cached['facts'] as List<dynamic>;
  }
  return {for (final item in raw) (item as Json)['name'] as String: FactSpec.fromJson(item)};
});

class ProfileState {
  const ProfileState({required this.facts, required this.eligibility, required this.isStale});

  /// Answers known so far.
  final Json facts;

  /// Latest results, or null if they have never been fetched.
  final Eligibility? eligibility;

  /// True when [eligibility] comes from the phone's cache because the API was unreachable.
  final bool isStale;
}

/// The Student's answers and the eligibility results they lead to.
class ProfileController extends AsyncNotifier<ProfileState> {
  LocalStore get _store => ref.read(localStoreProvider);
  PankhApi get _api => ref.read(apiProvider);
  bool get _signedIn => ref.read(sessionProvider) != null;

  @override
  Future<ProfileState> build() async {
    ref.watch(sessionProvider);
    return _load();
  }

  Future<void> refresh() async {
    state = AsyncData(await _load());
  }

  /// Record an answer. A null [value] withdraws it.
  Future<void> answer(String name, Object? value) async {
    final facts = Json.of(_store.facts);
    if (value == null) {
      facts.remove(name);
    } else {
      facts[name] = value;
    }
    await _store.setFacts(facts);
    if (_signedIn) {
      await _store.setUnsyncedFacts({..._store.unsyncedFacts, name});
    }
    state = AsyncData(await _load());
  }

  /// After signing in, keep answers given on this phone and load any saved on the server.
  Future<void> adoptAfterSignIn() async {
    await _store.setUnsyncedFacts(_store.facts.keys.toSet());
    state = AsyncData(await _load());
  }

  Future<ProfileState> _load() async {
    try {
      final Json json;
      if (_signedIn) {
        await _pushUnsynced();
        final serverFacts = await _api.myFacts();
        await _store.setFacts(serverFacts);
        json = await _api.myEligibility();
      } else {
        json = await _api.eligibility(_store.facts);
      }
      await _store.setLastEligibility(json);
      return ProfileState(
        facts: _store.facts,
        eligibility: Eligibility.fromJson(json),
        isStale: false,
      );
    } on ApiException catch (error) {
      final cached = _store.lastEligibility;
      if (!error.isOffline) rethrow;
      return ProfileState(
        facts: _store.facts,
        eligibility: cached == null ? null : Eligibility.fromJson(cached),
        isStale: true,
      );
    }
  }

  Future<void> _pushUnsynced() async {
    final names = _store.unsyncedFacts;
    if (names.isEmpty) return;
    final facts = _store.facts;
    await _api.saveFacts({for (final name in names) name: facts[name]});
    await _store.setUnsyncedFacts({});
  }
}

final profileProvider = AsyncNotifierProvider<ProfileController, ProfileState>(
  ProfileController.new,
);

/// What DigiLocker and the registers have confirmed. Null when not signed in.
final verificationProvider = FutureProvider<Verification?>((ref) async {
  if (ref.watch(sessionProvider) == null) return null;
  return Verification.fromJson(await ref.read(apiProvider).verification());
});

final uploadQueueProvider = Provider(
  (ref) => UploadQueue(ref.watch(localStoreProvider), ref.watch(apiProvider)),
);

/// The Student's uploaded Document photos. Empty when not signed in. Photos taken offline are
/// uploaded first, when there is a connection again.
final uploadsProvider = FutureProvider<List<UploadedDocument>>((ref) async {
  if (ref.watch(sessionProvider) == null) return const [];
  if (ref.read(uploadQueueProvider).pending.isNotEmpty) {
    await ref.read(uploadQueueProvider).flush();
  }
  return [
    for (final d in await ref.read(apiProvider).uploads()) UploadedDocument.fromJson(d as Json),
  ];
});

final documentCaptureProvider = Provider((ref) => DocumentCapture());

/// Makes a new voice call for each conversation. Overridden in tests.
final voiceCallFactoryProvider = Provider<VoiceCall Function()>((ref) => LiveKitVoiceCall.new);

/// The account's facilitator registration and the Students it helps. Null when not signed in.
final facilitatorProvider = FutureProvider.autoDispose<({Json? me, List<dynamic> students})?>((
  ref,
) async {
  if (ref.watch(sessionProvider) == null) return null;
  final api = ref.read(apiProvider);
  final me = await api.facilitator();
  final language = ref.watch(languageProvider).languageCode;
  final students = me?['status'] == 'approved' ? await api.helpedStudents(language) : const [];
  return (me: me, students: students);
});

/// Facilitators helping the signed-in Student.
final helpersProvider = FutureProvider.autoDispose<List<dynamic>>((ref) async {
  if (ref.watch(sessionProvider) == null) return const [];
  return ref.read(apiProvider).helpers();
});

/// Grievances the Student could file on CPGRAMS, and those filed. Null when not signed in.
final grievancesProvider = FutureProvider<Json?>((ref) async {
  if (ref.watch(sessionProvider) == null) return null;
  ref.watch(verificationProvider);
  return ref.read(apiProvider).grievances();
});

/// Next year's applications for Schemes held now. Empty when not signed in.
final renewalsProvider = FutureProvider<List<RenewalPlan>>((ref) async {
  if (ref.watch(sessionProvider) == null) return const [];
  ref.watch(verificationProvider);
  return [for (final r in await ref.read(apiProvider).renewals()) RenewalPlan.fromJson(r as Json)];
});

/// Applications across NSP, SFMP and the NOS Portal. Null when not signed in.
final applicationsProvider = FutureProvider<Applications?>((ref) async {
  if (ref.watch(sessionProvider) == null) return null;
  ref.watch(verificationProvider);
  return Applications.fromJson(await ref.read(apiProvider).applications());
});

/// The conversation with JAGO. Replies are appended as they arrive.
class JagoController extends AsyncNotifier<List<ChatMessage>> {
  @override
  Future<List<ChatMessage>> build() async {
    if (ref.watch(sessionProvider) == null) return const [];
    final raw = await ref.read(apiProvider).jagoConversation();
    return [for (final item in raw) ChatMessage.fromJson(item as Json)];
  }

  Future<void> say(String text) async {
    final message = text.trim();
    if (message.isEmpty) return;
    final before = state.value ?? const <ChatMessage>[];
    state = AsyncData([...before, ChatMessage(fromStudent: true, text: message)]);
    final language = ref.read(languageProvider).languageCode;
    try {
      final reply = await ref.read(apiProvider).talkToJago(message, language);
      state = AsyncData([...state.value!, ChatMessage.fromJson(reply)]);
      // JAGO may have saved an answer; results elsewhere should reflect it.
      await ref.read(profileProvider.notifier).refresh();
    } on ApiException {
      state = AsyncData(before);
      rethrow;
    }
  }
}

final jagoProvider = AsyncNotifierProvider<JagoController, List<ChatMessage>>(JagoController.new);

/// Reminders the chasing agent sent to the Student, newest first.
final remindersProvider = FutureProvider<List<(String, String)>>((ref) async {
  if (ref.watch(sessionProvider) == null) return const [];
  final raw = await ref.read(apiProvider).reminders();
  return [
    for (final item in raw) ((item as Json)['message'] as String, item['created_at'] as String),
  ];
});

/// The Scheme Path for the Student's answers so far.
final schemePathProvider = FutureProvider<List<PathStage>>((ref) async {
  final profile = await ref.watch(profileProvider.future);
  final api = ref.read(apiProvider);
  final json = ref.read(sessionProvider) != null
      ? await api.mySchemePath()
      : await api.schemePath(profile.facts);
  return [for (final s in json['stages'] as List) PathStage.fromJson(s as Json)];
});

/// The children this account follows, and who follows it. Raw API data.
final familyProvider = FutureProvider<Json>((ref) async {
  if (ref.watch(sessionProvider) == null) return const {'children': [], 'guardians': []};
  return ref.read(apiProvider).family();
});
