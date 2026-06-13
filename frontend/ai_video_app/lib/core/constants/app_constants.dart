/// General application-wide constants.
abstract final class AppConstants {
  AppConstants._();

  // ── App identity ────────────────────────────────────────────────────────────
  static const String appName = 'AI Video SaaS';
  static const String appVersion = '1.0.0';

  // ── Pagination ──────────────────────────────────────────────────────────────
  static const int defaultPageSize = 20;
  static const int maxPageSize = 100;

  // ── File upload ─────────────────────────────────────────────────────────────
  static const int maxUploadSizeMb = 500;
  static const int maxUploadSizeBytes = maxUploadSizeMb * 1024 * 1024;
  static const List<String> allowedVideoExtensions = [
    'mp4',
    'mov',
    'avi',
    'mkv',
    'webm',
  ];
  static const List<String> allowedAudioExtensions = [
    'mp3',
    'wav',
    'aac',
    'ogg',
    'm4a',
  ];

  // ── Token refresh ────────────────────────────────────────────────────────────
  /// Refresh the access token when it has less than this many minutes remaining.
  static const int tokenRefreshThresholdMinutes = 5;

  // ── Task polling ─────────────────────────────────────────────────────────────
  /// How often to poll the /tasks/{id}/status endpoint during processing.
  static const Duration taskPollInterval = Duration(seconds: 3);

  /// Stop polling after this many consecutive failures.
  static const int taskPollMaxFailures = 5;

  // ── UI ────────────────────────────────────────────────────────────────────────
  static const Duration defaultAnimationDuration = Duration(milliseconds: 300);
  static const Duration snackBarDuration = Duration(seconds: 4);
  static const double defaultBorderRadius = 12.0;
  static const double cardBorderRadius = 16.0;
  static const double buttonBorderRadius = 10.0;

  // ── Spacing (8pt grid) ────────────────────────────────────────────────────────
  static const double spacing4 = 4.0;
  static const double spacing8 = 8.0;
  static const double spacing12 = 12.0;
  static const double spacing16 = 16.0;
  static const double spacing20 = 20.0;
  static const double spacing24 = 24.0;
  static const double spacing32 = 32.0;
  static const double spacing40 = 40.0;
  static const double spacing48 = 48.0;
  static const double spacing64 = 64.0;

  // ── Responsive breakpoints ────────────────────────────────────────────────────
  static const double mobileBreakpoint = 600.0;
  static const double tabletBreakpoint = 900.0;
  static const double desktopBreakpoint = 1200.0;
}

/// All local storage keys.
abstract final class StorageKeys {
  StorageKeys._();

  // Stored in FlutterSecureStorage (iOS Keychain / Android Keystore)
  static const String accessToken = 'access_token';
  static const String refreshToken = 'refresh_token';

  // Stored in SharedPreferences (non-sensitive)
  static const String themeMode = 'theme_mode';
  static const String locale = 'locale';
  static const String onboardingDone = 'onboarding_done';
  static const String lastUsedProjectId = 'last_used_project_id';
}
