import 'package:flutter/material.dart';
import 'package:percent_indicator/linear_percent_indicator.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_text_styles.dart';

class UploadProgressWidget extends StatelessWidget {
  const UploadProgressWidget({
    super.key,
    required this.progress,
    required this.label,
    this.subtitle,
  });
  final double progress; // 0.0 – 1.0
  final String label;
  final String? subtitle;

  @override
  Widget build(BuildContext context) {
    final percent = (progress * 100).toInt();
    return Card(
      margin: const EdgeInsets.all(16),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.upload_rounded,
                    color: AppColors.primary, size: 22),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(label, style: AppTextStyles.titleSmall),
                ),
                Text(
                  '$percent%',
                  style: AppTextStyles.titleSmall
                      .copyWith(color: AppColors.primary),
                ),
              ],
            ),
            const SizedBox(height: 12),
            LinearPercentIndicator(
              lineHeight: 8,
              percent: progress.clamp(0.0, 1.0),
              backgroundColor: AppColors.primary.withValues(alpha: 0.1),
              progressColor: AppColors.primary,
              barRadius: const Radius.circular(4),
              padding: EdgeInsets.zero,
              animation: true,
              animateFromLastPercent: true,
            ),
            if (subtitle != null) ...[
              const SizedBox(height: 8),
              Text(
                subtitle!,
                style: AppTextStyles.bodySmall.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
