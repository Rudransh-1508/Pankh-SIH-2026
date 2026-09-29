import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'data/api.dart';
import 'l10n/generated/app_localizations.dart';
import 'screens/answers_screen.dart';
import 'screens/applications_screen.dart';
import 'screens/digilocker_callback_screen.dart';
import 'screens/discover_screen.dart';
import 'screens/jago_screen.dart';
import 'screens/path_screen.dart';
import 'screens/questions_screen.dart';
import 'screens/reminders_screen.dart';
import 'screens/scheme_screen.dart';
import 'screens/sign_in_screens.dart';
import 'screens/wallet_screen.dart';
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
      StatefulShellRoute.indexedStack(
        builder: (_, _, shell) => _Tabs(shell: shell),
        branches: [
          StatefulShellBranch(
            routes: [GoRoute(path: '/discover', builder: (_, _) => const DiscoverScreen())],
          ),
          StatefulShellBranch(
            routes: [GoRoute(path: '/applications', builder: (_, _) => const ApplicationsScreen())],
          ),
          StatefulShellBranch(
            routes: [GoRoute(path: '/wallet', builder: (_, _) => const WalletScreen())],
          ),
          StatefulShellBranch(
            routes: [GoRoute(path: '/jago', builder: (_, _) => const JagoScreen())],
          ),
        ],
      ),
      GoRoute(path: '/answers', builder: (_, _) => const AnswersScreen()),
      GoRoute(path: '/reminders', builder: (_, _) => const RemindersScreen()),
      GoRoute(path: '/path', builder: (_, _) => const PathScreen()),
      // DigiLocker returns to pankh://digilocker/callback; the router sees the path.
      GoRoute(
        path: '/callback',
        builder: (_, state) => DigiLockerCallbackScreen(
          code: state.uri.queryParameters['code'],
          state: state.uri.queryParameters['state'],
        ),
      ),
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

/// The three places a Student keeps coming back to, always one tap away.
class _Tabs extends StatelessWidget {
  const _Tabs({required this.shell});

  final StatefulNavigationShell shell;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      body: shell,
      bottomNavigationBar: NavigationBar(
        selectedIndex: shell.currentIndex,
        onDestinationSelected: (index) =>
            shell.goBranch(index, initialLocation: index == shell.currentIndex),
        backgroundColor: PankhColors.card,
        indicatorColor: PankhColors.peacockMist,
        destinations: [
          NavigationDestination(
            icon: const Icon(Icons.school_outlined),
            selectedIcon: const Icon(Icons.school_rounded, color: PankhColors.peacockDeep),
            label: l10n.tabScholarships,
          ),
          NavigationDestination(
            icon: const Icon(Icons.assignment_outlined),
            selectedIcon: const Icon(Icons.assignment_rounded, color: PankhColors.peacockDeep),
            label: l10n.tabApplications,
          ),
          NavigationDestination(
            icon: const Icon(Icons.folder_outlined),
            selectedIcon: const Icon(Icons.folder_rounded, color: PankhColors.peacockDeep),
            label: l10n.tabDocuments,
          ),
          NavigationDestination(
            icon: const Icon(Icons.forum_outlined),
            selectedIcon: const Icon(Icons.forum_rounded, color: PankhColors.peacockDeep),
            label: l10n.tabJago,
          ),
        ],
      ),
    );
  }
}
