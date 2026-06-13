/// All API configuration and endpoint paths.
///
/// Usage:
///   dio.get(ApiConstants.authMe)
///   dio.post('${ApiConstants.projects}/${projectId}/videos')
abstract final class ApiConstants {
  ApiConstants._();

  // ── Base URLs ──────────────────────────────────────────────────────────────
  static const String baseUrlDev = 'http://192.168.1.5:8000/api/v1';
  static const String baseUrlProd = 'https://api.aivideosaas.com/api/v1';

  // ── Timeouts ───────────────────────────────────────────────────────────────
  static const Duration connectTimeout = Duration(seconds: 15);
  static const Duration receiveTimeout = Duration(seconds: 60);

  /// Upload timeout is longer — video files can be large
  static const Duration uploadTimeout = Duration(minutes: 10);

  // ── Auth ───────────────────────────────────────────────────────────────────
  static const String authLogin = '/auth/login';
  static const String authRefresh = '/auth/refresh';
  static const String authLogout = '/auth/logout';
  static const String authMe = '/auth/me';

  // ── Users ──────────────────────────────────────────────────────────────────
  static const String users = '/users/';
  static const String usersMe = '/users/me';
  static const String userPassword = '/users/me/password';

  // ── Projects ───────────────────────────────────────────────────────────────
  static const String projects = '/projects/';

  static String projectById(String id) => '/projects/$id';

  // ── Videos ─────────────────────────────────────────────────────────────────
  /// POST  — create a video record inside a project
  static String projectVideos(String projectId) =>
      '/videos/projects/$projectId/videos';

  /// GET   — list videos inside a project
  static String listVideos(String projectId) =>
      '/videos/projects/$projectId/videos';

  /// POST  — upload source file (multipart/form-data)
  static String uploadVideo(String videoId) => '/videos/$videoId/upload';

  /// POST  — enqueue AI processing pipeline
  static String processVideo(String videoId) => '/videos/$videoId/process';

  /// GET   — lightweight status poll
  static String videoStatus(String videoId) => '/videos/$videoId/status';

  /// GET   — full video detail
  static String videoById(String videoId) => '/videos/$videoId';

  /// DELETE — soft-delete a video
  static String deleteVideo(String videoId) => '/videos/$videoId';

  // ── Tasks ──────────────────────────────────────────────────────────────────
  /// GET — full task detail + log lines
  static String taskById(String taskId) => '/tasks/$taskId';

  /// GET — lightweight status poll (progress 0–100)
  static String taskStatus(String taskId) => '/tasks/$taskId/status';

  /// GET — all tasks for a video
  static String tasksByVideo(String videoId) => '/tasks/video/$videoId';

  // ── Health ─────────────────────────────────────────────────────────────────
  static const String health = '/health';
}
