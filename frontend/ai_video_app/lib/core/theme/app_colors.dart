import 'package:flutter/material.dart';

/// Light and dark color palettes for the app.
/// All colors are accessed through [AppColors.light] or [AppColors.dark].
abstract final class AppColors {
  AppColors._();

  // ── Brand ────────────────────────────────────────────────────────────────────
  static const Color primary = Color(0xFF6C63FF); // indigo-violet
  static const Color primaryLight = Color(0xFF9D97FF);
  static const Color primaryDark = Color(0xFF4A42D6);
  static const Color secondary = Color(0xFF00D4AA); // teal-mint
  static const Color secondaryLight = Color(0xFF5FFFDE);
  static const Color secondaryDark = Color(0xFF00A37C);
  static const Color accent = Color(0xFFFF6B6B); // coral

  // ── Semantic ─────────────────────────────────────────────────────────────────
  static const Color success = Color(0xFF22C55E);
  static const Color warning = Color(0xFFF59E0B);
  static const Color error = Color(0xFFEF4444);
  static const Color info = Color(0xFF3B82F6);

  // ── Semantic light variants ───────────────────────────────────────────────────
  static const Color successLight = Color(0xFFDCFCE7);
  static const Color warningLight = Color(0xFFFEF3C7);
  static const Color errorLight = Color(0xFFFEE2E2);
  static const Color infoLight = Color(0xFFDBEAFE);

  // ── Video status colors ───────────────────────────────────────────────────────
  static const Color statusPending = Color(0xFF94A3B8);
  static const Color statusUploading = Color(0xFF3B82F6);
  static const Color statusUploaded = Color(0xFF8B5CF6);
  static const Color statusProcessing = Color(0xFFF59E0B);
  static const Color statusCompleted = Color(0xFF22C55E);
  static const Color statusFailed = Color(0xFFEF4444);
  static const Color statusCancelled = Color(0xFF64748B);

  // ── Neutral ───────────────────────────────────────────────────────────────────
  static const Color white = Color(0xFFFFFFFF);
  static const Color black = Color(0xFF000000);
  static const Color transparent = Color(0x00000000);

  // ── Light theme surface colors ────────────────────────────────────────────────
  static const Color lightBackground = Color(0xFFF8F9FC);
  static const Color lightSurface = Color(0xFFFFFFFF);
  static const Color lightSurfaceVariant = Color(0xFFF1F3F9);
  static const Color lightBorder = Color(0xFFE2E8F0);
  static const Color lightBorderStrong = Color(0xFFCBD5E1);
  static const Color lightTextPrimary = Color(0xFF0F172A);
  static const Color lightTextSecondary = Color(0xFF475569);
  static const Color lightTextTertiary = Color(0xFF94A3B8);
  static const Color lightTextDisabled = Color(0xFFCBD5E1);
  static const Color lightScaffold = Color(0xFFF8F9FC);
  static const Color lightCard = Color(0xFFFFFFFF);
  static const Color lightDivider = Color(0xFFE2E8F0);
  static const Color lightInputFill = Color(0xFFF1F5F9);
  static const Color lightInputBorder = Color(0xFFE2E8F0);
  static const Color lightInputFocusBorder = primary;

  // ── Dark theme surface colors ─────────────────────────────────────────────────
  static const Color darkBackground = Color(0xFF0B0E1A);
  static const Color darkSurface = Color(0xFF141827);
  static const Color darkSurfaceVariant = Color(0xFF1E2335);
  static const Color darkBorder = Color(0xFF2D3348);
  static const Color darkBorderStrong = Color(0xFF3D4459);
  static const Color darkTextPrimary = Color(0xFFF1F5F9);
  static const Color darkTextSecondary = Color(0xFF94A3B8);
  static const Color darkTextTertiary = Color(0xFF64748B);
  static const Color darkTextDisabled = Color(0xFF475569);
  static const Color darkScaffold = Color(0xFF0B0E1A);
  static const Color darkCard = Color(0xFF141827);
  static const Color darkDivider = Color(0xFF2D3348);
  static const Color darkInputFill = Color(0xFF1E2335);
  static const Color darkInputBorder = Color(0xFF2D3348);
  static const Color darkInputFocusBorder = primaryLight;

  // ── Gradients ─────────────────────────────────────────────────────────────────
  static const LinearGradient primaryGradient = LinearGradient(
    colors: [primary, Color(0xFF9D97FF)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient cardGradient = LinearGradient(
    colors: [Color(0xFF6C63FF), Color(0xFF00D4AA)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient darkBackgroundGradient = LinearGradient(
    colors: [Color(0xFF0B0E1A), Color(0xFF141827)],
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
  );
}
