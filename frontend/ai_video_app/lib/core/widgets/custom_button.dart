import 'package:flutter/material.dart';
import '../theme/app_colors.dart';
import '../theme/app_text_styles.dart';

enum ButtonVariant { primary, secondary, outlined, ghost, danger }

enum ButtonSize { small, medium, large }

/// Production-grade button with loading state, variants and sizes.
class AppButton extends StatelessWidget {
  const AppButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.variant = ButtonVariant.primary,
    this.size = ButtonSize.medium,
    this.isLoading = false,
    this.isDisabled = false,
    this.prefixIcon,
    this.suffixIcon,
    this.width,
  });

  final String label;
  final VoidCallback? onPressed;
  final ButtonVariant variant;
  final ButtonSize size;
  final bool isLoading;
  final bool isDisabled;
  final IconData? prefixIcon;
  final IconData? suffixIcon;
  final double? width;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    final height = switch (size) {
      ButtonSize.small => 40.0,
      ButtonSize.medium => 52.0,
      ButtonSize.large => 60.0,
    };
    final fontSize = switch (size) {
      ButtonSize.small => 13.0,
      ButtonSize.medium => 15.0,
      ButtonSize.large => 17.0,
    };
    final iconSize = switch (size) {
      ButtonSize.small => 16.0,
      ButtonSize.medium => 18.0,
      ButtonSize.large => 20.0,
    };

    final bool disabled = isDisabled || isLoading || onPressed == null;

    return SizedBox(
      width: width ?? double.infinity,
      height: height,
      child: switch (variant) {
        ButtonVariant.primary =>
          _buildElevated(context, disabled, fontSize, iconSize, isDark),
        ButtonVariant.secondary =>
          _buildSecondary(context, disabled, fontSize, iconSize),
        ButtonVariant.outlined =>
          _buildOutlined(context, disabled, fontSize, iconSize),
        ButtonVariant.ghost =>
          _buildGhost(context, disabled, fontSize, iconSize),
        ButtonVariant.danger =>
          _buildDanger(context, disabled, fontSize, iconSize),
      },
    );
  }

  Widget _buildElevated(
      BuildContext ctx, bool disabled, double fs, double is_, bool isDark) {
    return ElevatedButton(
      onPressed: disabled ? null : onPressed,
      style: ElevatedButton.styleFrom(
        backgroundColor:
            disabled ? AppColors.lightTextDisabled : AppColors.primary,
        foregroundColor: AppColors.white,
        textStyle: AppTextStyles.button.copyWith(fontSize: fs),
      ),
      child: _child(AppColors.white, fs, is_),
    );
  }

  Widget _buildSecondary(
      BuildContext ctx, bool disabled, double fs, double is_) {
    return ElevatedButton(
      onPressed: disabled ? null : onPressed,
      style: ElevatedButton.styleFrom(
        backgroundColor: AppColors.primaryLight.withValues(alpha: 0.15),
        foregroundColor: AppColors.primary,
        elevation: 0,
        textStyle: AppTextStyles.button.copyWith(fontSize: fs),
      ),
      child: _child(AppColors.primary, fs, is_),
    );
  }

  Widget _buildOutlined(
      BuildContext ctx, bool disabled, double fs, double is_) {
    return OutlinedButton(
      onPressed: disabled ? null : onPressed,
      style: OutlinedButton.styleFrom(
        foregroundColor: AppColors.primary,
        side: BorderSide(
          color: disabled ? AppColors.lightTextDisabled : AppColors.primary,
          width: 1.5,
        ),
        textStyle: AppTextStyles.button.copyWith(fontSize: fs),
      ),
      child: _child(AppColors.primary, fs, is_),
    );
  }

  Widget _buildGhost(BuildContext ctx, bool disabled, double fs, double is_) {
    return TextButton(
      onPressed: disabled ? null : onPressed,
      style: TextButton.styleFrom(
        foregroundColor: AppColors.primary,
        textStyle: AppTextStyles.button.copyWith(fontSize: fs),
      ),
      child: _child(AppColors.primary, fs, is_),
    );
  }

  Widget _buildDanger(BuildContext ctx, bool disabled, double fs, double is_) {
    return ElevatedButton(
      onPressed: disabled ? null : onPressed,
      style: ElevatedButton.styleFrom(
        backgroundColor:
            disabled ? AppColors.lightTextDisabled : AppColors.error,
        foregroundColor: AppColors.white,
        textStyle: AppTextStyles.button.copyWith(fontSize: fs),
      ),
      child: _child(AppColors.white, fs, is_),
    );
  }

  Widget _child(Color color, double fontSize, double iconSize) {
    if (isLoading) {
      return SizedBox(
        width: iconSize + 2,
        height: iconSize + 2,
        child: CircularProgressIndicator(
          strokeWidth: 2,
          color: color,
        ),
      );
    }
    return Row(
      mainAxisSize: MainAxisSize.min,
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        if (prefixIcon != null) ...[
          Icon(prefixIcon, size: iconSize, color: color),
          const SizedBox(width: 8),
        ],
        Text(label, style: AppTextStyles.button.copyWith(fontSize: fontSize)),
        if (suffixIcon != null) ...[
          const SizedBox(width: 8),
          Icon(suffixIcon, size: iconSize, color: color),
        ],
      ],
    );
  }
}
