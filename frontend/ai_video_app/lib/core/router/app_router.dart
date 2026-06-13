import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../features/auth/presentation/bloc/auth_bloc.dart';
import '../../features/auth/presentation/pages/login_page.dart';
import '../../features/auth/presentation/pages/register_page.dart';
import '../../features/projects/presentation/pages/project_detail_page.dart';
import '../../features/projects/presentation/pages/projects_page.dart';
import '../../features/video/presentation/pages/video_detail_page.dart';
import '../../features/video/presentation/pages/video_upload_page.dart';
import '../../features/video/presentation/pages/videos_page.dart';
import '../../features/profile/presentation/pages/profile_page.dart';
import 'route_names.dart';

/// Configures the GoRouter instance.
class AppRouter {
  AppRouter({required this.authBloc});

  final AuthBloc authBloc;
  late final GoRouter router = _buildRouter();

  GoRouter _buildRouter() {
    return GoRouter(
      // 🚀 TEMP FIX: no splash screen anymore
      initialLocation: RouteNames.login,
      debugLogDiagnostics: true,
      refreshListenable: GoRouterAuthNotifier(authBloc: authBloc),

      // ── Auth redirect guard ─────────────────────────────────────────────────
      redirect: (BuildContext context, GoRouterState state) {
        final authStatus = authBloc.state.status;

        final isOnAuthPage = state.matchedLocation == RouteNames.login ||
            state.matchedLocation == RouteNames.register;

        // Still checking auth → do nothing (stay where you are)
        if (authStatus == AuthStatus.loading ||
            authStatus == AuthStatus.initial) {
          return null;
        }

        // Not authenticated → force login
        if (authStatus == AuthStatus.unauthenticated) {
          return isOnAuthPage ? null : RouteNames.login;
        }

        // Authenticated → block auth pages
        if (authStatus == AuthStatus.authenticated && isOnAuthPage) {
          return RouteNames.projects;
        }

        return null;
      },

      routes: [
        // ── Auth ───────────────────────────────────────────────────────────────
        GoRoute(
          path: RouteNames.login,
          name: 'login',
          builder: (_, __) => const LoginPage(),
        ),
        GoRoute(
          path: RouteNames.register,
          name: 'register',
          builder: (_, __) => const RegisterPage(),
        ),

        // ── Shell with bottom navigation ────────────────────────────────────────
        ShellRoute(
          builder: (context, state, child) => _MainShell(child: child),
          routes: [
            // Projects
            GoRoute(
              path: RouteNames.projects,
              name: 'projects',
              builder: (_, __) => const ProjectsPage(),
              routes: [
                GoRoute(
                  path: 'create',
                  name: 'projectCreate',
                  builder: (_, __) =>
                      const ProjectsPage(openCreateDialog: true),
                ),
                GoRoute(
                  path: ':projectId',
                  name: 'projectDetail',
                  builder: (_, state) => ProjectDetailPage(
                    projectId: state.pathParameters['projectId']!,
                  ),
                  routes: [
                    GoRoute(
                      path: 'videos',
                      name: 'videos',
                      builder: (_, state) => VideosPage(
                        projectId: state.pathParameters['projectId']!,
                      ),
                      routes: [
                        GoRoute(
                          path: 'upload',
                          name: 'videoUpload',
                          builder: (_, state) => VideoUploadPage(
                            projectId: state.pathParameters['projectId']!,
                          ),
                        ),
                        GoRoute(
                          path: ':videoId',
                          name: 'videoDetail',
                          builder: (_, state) => VideoDetailPage(
                            projectId: state.pathParameters['projectId']!,
                            videoId: state.pathParameters['videoId']!,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ],
            ),

            // Profile
            GoRoute(
              path: RouteNames.profile,
              name: 'profile',
              builder: (_, __) => const ProfilePage(),
            ),
          ],
        ),
      ],

      errorBuilder: (context, state) => _ErrorPage(error: state.error),
    );
  }

  void dispose() {
    // GoRouter disposes internally
  }
}

// =============================================================================
// GoRouterAuthNotifier — bridges AuthBloc state to GoRouter refresh
// =============================================================================

class GoRouterAuthNotifier extends ChangeNotifier {
  GoRouterAuthNotifier({required AuthBloc authBloc}) {
    _subscription = authBloc.stream.listen((_) => notifyListeners());
  }

  late final dynamic _subscription;

  @override
  void dispose() {
    _subscription.cancel();
    super.dispose();
  }
}

// =============================================================================
// _MainShell — bottom navigation bar shell
// =============================================================================

class _MainShell extends StatelessWidget {
  const _MainShell({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    final location = GoRouterState.of(context).matchedLocation;

    int currentIndex = 0;
    if (location.startsWith('/projects')) currentIndex = 0;
    if (location.startsWith('/profile')) currentIndex = 1;

    return Scaffold(
      body: child,
      bottomNavigationBar: NavigationBar(
        selectedIndex: currentIndex,
        onDestinationSelected: (index) {
          switch (index) {
            case 0:
              context.go(RouteNames.projects);
              break;
            case 1:
              context.go(RouteNames.profile);
              break;
          }
        },
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.video_library_outlined),
            selectedIcon: Icon(Icons.video_library),
            label: 'Projects',
          ),
          NavigationDestination(
            icon: Icon(Icons.person_outline),
            selectedIcon: Icon(Icons.person),
            label: 'Profile',
          ),
        ],
      ),
    );
  }
}

// =============================================================================
// Error page
// =============================================================================

class _ErrorPage extends StatelessWidget {
  const _ErrorPage({this.error});

  final Exception? error;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, size: 64, color: Colors.red),
            const SizedBox(height: 16),
            Text(
              'Page not found',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            TextButton(
              onPressed: () => context.go(RouteNames.projects),
              child: const Text('Go Home'),
            ),
          ],
        ),
      ),
    );
  }
}
