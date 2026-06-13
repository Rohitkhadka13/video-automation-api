/// All named route paths used with GoRouter.
/// Using constants prevents typos in go() / push() calls.
abstract final class RouteNames {
  RouteNames._();

  // ── Auth ──────────────────────────────────────────────────────────────────
  static const String splash = '/';
  static const String login = '/login';
  static const String register = '/register';

  // ── Main shell (bottom nav) ────────────────────────────────────────────────
  static const String home = '/home';

  // ── Projects ──────────────────────────────────────────────────────────────
  static const String projects = '/projects';
  static const String projectDetail = '/projects/:projectId';
  static const String projectCreate = '/projects/create';

  // ── Videos ────────────────────────────────────────────────────────────────
  static const String videos = '/projects/:projectId/videos';
  static const String videoDetail = '/projects/:projectId/videos/:videoId';
  static const String videoUpload = '/projects/:projectId/videos/upload';

  // ── Profile ────────────────────────────────────────────────────────────────
  static const String profile = '/profile';
  static const String editProfile = '/profile/edit';
  static const String changePassword = '/profile/password';

  // ── Helpers to build parameterised paths ──────────────────────────────────
  static String projectDetailPath(String projectId) => '/projects/$projectId';

  static String videosPath(String projectId) => '/projects/$projectId/videos';

  static String videoDetailPath(String projectId, String videoId) =>
      '/projects/$projectId/videos/$videoId';

  static String videoUploadPath(String projectId) =>
      '/projects/$projectId/videos/upload';
}
