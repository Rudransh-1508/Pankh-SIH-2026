import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'data/api.dart';
import 'l10n/generated/app_localizations.dart';
import 'screens/answers_screen.dart';
import 'screens/discover_screen.dart';
import 'screens/questions_screen.dart';
import 'screens/scheme_screen.dart';
import 'screens/sign_in_screens.dart';
import 'screens/welcome_screen.dart';
import 'state/providers.dart';
import 'theme.dart';

final routerProvider = Provider((ref) {
  final store = ref.read(localStoreProvider);
  final returning = store.phone != null || store.facts.isNotEmpty;
  return GoRouter(
    initialLocation: returning ? '/discover' : '/welcome',
    routes: [
      GoRoute(path: '/welcome', builder: (_, _) => const WelcomeScreen()),
      GoRoute(path: '/sign-in', builder: (_, _) => const PhoneScreen()),
      GoRoute(
        path: '/sign-in/code',
        builder: (_, state) => CodeScreen(sent: state.extra! as OtpRequested),
      ),
      GoRoute(
        path: '/questions',
        builder: (_, state) => QuestionsScreen(fact: state.uri.queryParameters['fact']),
      ),
      GoRoute(path: '/discover', builder: (_, _) => const DiscoverScreen()),
      GoRoute(path: '/answers', builder: (_, _) => const AnswersScreen()),
      GoRoute(
        path: '/schemes/:id',
        builder: (_, state) => SchemeScreen(schemeId: state.pathParameters['id']!),
      ),
    ],
  );
});

class PankhApp extends ConsumerWidget {
  const PankhApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return MaterialApp.router(
      onGenerateTitle: (context) => AppLocalizations.of(context).appName,
      debugShowCheckedModeBanner: false,
      theme: pankhTheme(),
      locale: ref.watch(languageProvider),
      supportedLocales: AppLocalizations.supportedLocales,
      localizationsDelegates: const [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      routerConfig: ref.watch(routerProvider),
    );
  }
}
