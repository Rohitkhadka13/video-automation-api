import 'package:dartz/dartz.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:timeago/timeago.dart' as timeago;

import '../error/failures.dart';
import '../theme/app_colors.dart';

// =============================================================================
// String extensions
// =============================================================================

extension StringX on String {
  /// Capitalise the first letter of every word.
  String get titleCase {
    if (isEmpty) return this;
    return split(' ')
        .map((w) => w.isEmpty ? w : w[0].toUpperCase() + w.substring(1))
        .join(' ');
  }

  /// Capitalise only the first letter.
  String get sentenceCase {
    if (isEmpty) return this;
    return this[0].toUpperCase() + substring(1).toLowerCase();
  }

  /// Return null if the string is empty or only whitespace.
  String? get nullIfEmpty => trim().isEmpty ? null : this;

  /// Truncate and append ellipsis if longer than [maxLength].
  String truncate(int maxLength, {String ellipsis = '…'}) {
    if (length <= maxLength) return this;
    return '${substring(0, maxLength)}$ellipsis';
  }

  /// True if the string is a valid email address.
  bool get isValidEmail {
    final regex = RegExp(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$');
    return regex.hasMatch(trim());
  }

  /// True if the string contains at least one uppercase, one digit, min 8 chars.
  bool get isStrongPassword {
    return length >= 8 &&
        contains(RegExp(r'[A-Z]')) &&
        contains(RegExp(r'[0-9]'));
  }
}

extension NullableStringX on String? {
  /// True if null or empty after trimming.
  bool get isNullOrEmpty => this == null || this!.trim().isEmpty;

  /// Return the string or a fallback.
  String orDefault(String fallback) => isNullOrEmpty ? fallback : this!;
}

// =============================================================================
// DateTime extensions
// =============================================================================

extension DateTimeX on DateTime {
  /// "Jun 7, 2025"
  String get formattedDate => DateFormat('MMM d, y').format(this);

  /// "2:34 PM"
  String get formattedTime => DateFormat('h:mm a').format(this);

  /// "Jun 7, 2025 · 2:34 PM"
  String get formattedDateTime => DateFormat('MMM d, y · h:mm a').format(this);

  /// "2 hours ago", "3 days ago", etc.
  String get timeAgo => timeago.format(this);

  /// True if the date is today.
  bool get isToday {
    final now = DateTime.now();
    return year == now.year && month == now.month && day == now.day;
  }

  /// True if the date was yesterday.
  bool get isYesterday {
    final yesterday = DateTime.now().subtract(const Duration(days: 1));
    return year == yesterday.year &&
        month == yesterday.month &&
        day == yesterday.day;
  }
}

// =============================================================================
// int / double extensions
// =============================================================================

extension IntX on int {
  /// Format bytes as human-readable: "1.2 MB", "500 KB", etc.
  String get readableFileSize {
    if (this < 1024) return '$this B';
    if (this < 1024 * 1024) return '${(this / 1024).toStringAsFixed(1)} KB';
    if (this < 1024 * 1024 * 1024)
      return '${(this / (1024 * 1024)).toStringAsFixed(1)} MB';
    return '${(this / (1024 * 1024 * 1024)).toStringAsFixed(2)} GB';
  }
}

extension DoubleX on double {
  /// Format seconds as "1:34" or "1:04:23"
  String get formattedDuration {
    final totalSeconds = toInt();
    final hours = totalSeconds ~/ 3600;
    final minutes = (totalSeconds % 3600) ~/ 60;
    final seconds = totalSeconds % 60;
    if (hours > 0) {
      return '$hours:${minutes.toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')}';
    }
    return '$minutes:${seconds.toString().padLeft(2, '0')}';
  }

  /// Clamp to percentage string "45.2%"
  String get percentString => '${(clamp(0, 1) * 100).toStringAsFixed(1)}%';
}

// =============================================================================
// BuildContext extensions
// =============================================================================

extension BuildContextX on BuildContext {
  // ── Theme shortcuts ──────────────────────────────────────────────────────
  ThemeData get theme => Theme.of(this);
  TextTheme get textTheme => Theme.of(this).textTheme;
  ColorScheme get colors => Theme.of(this).colorScheme;
  bool get isDark => Theme.of(this).brightness == Brightness.dark;

  // ── Media query shortcuts ────────────────────────────────────────────────
  MediaQueryData get mediaQuery => MediaQuery.of(this);
  Size get screenSize => MediaQuery.of(this).size;
  double get screenWidth => MediaQuery.of(this).size.width;
  double get screenHeight => MediaQuery.of(this).size.height;
  EdgeInsets get padding => MediaQuery.of(this).padding;
  EdgeInsets get viewInsets => MediaQuery.of(this).viewInsets;
  bool get isKeyboardOpen => MediaQuery.of(this).viewInsets.bottom > 0;

  // ── Responsive helpers ────────────────────────────────────────────────────
  bool get isMobile => screenWidth < 600;
  bool get isTablet => screenWidth >= 600 && screenWidth < 900;
  bool get isDesktop => screenWidth >= 900;

  // ── Navigation ────────────────────────────────────────────────────────────
  void unfocus() => FocusScope.of(this).unfocus();
  void pop<T>([T? result]) => Navigator.of(this).pop(result);

  // ── Snack bar shortcuts (use AppSnackbar in real usage) ───────────────────
  void showSnack(String message) {
    ScaffoldMessenger.of(this).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }
}

// =============================================================================
// Either extensions
// =============================================================================

extension EitherX<L extends Failure, R> on Either<L, R> {
  /// Execute [onSuccess] if Right, [onFailure] if Left.
  void fold2({
    required void Function(L failure) onFailure,
    required void Function(R value) onSuccess,
  }) {
    fold(onFailure, onSuccess);
  }

  /// True if this is a Right (success) value.
  bool get isSuccess => isRight();

  /// True if this is a Left (failure) value.
  bool get isFailure => isLeft();

  /// Return the Right value or null.
  R? get rightOrNull => fold((_) => null, (r) => r);

  /// Return the Left failure or null.
  L? get leftOrNull => fold((l) => l, (_) => null);
}

// =============================================================================
// Video status color extension
// =============================================================================

extension VideoStatusX on String {
  Color get statusColor => switch (this) {
        'pending' => AppColors.statusPending,
        'uploading' => AppColors.statusUploading,
        'uploaded' => AppColors.statusUploaded,
        'processing' => AppColors.statusProcessing,
        'completed' => AppColors.statusCompleted,
        'failed' => AppColors.statusFailed,
        'cancelled' => AppColors.statusCancelled,
        _ => AppColors.statusPending,
      };

  String get statusLabel => switch (this) {
        'pending' => 'Pending',
        'uploading' => 'Uploading',
        'uploaded' => 'Uploaded',
        'processing' => 'Processing',
        'completed' => 'Completed',
        'failed' => 'Failed',
        'cancelled' => 'Cancelled',
        _ => 'Unknown',
      };

  bool get isTerminalStatus =>
      this == 'completed' || this == 'failed' || this == 'cancelled';
}
