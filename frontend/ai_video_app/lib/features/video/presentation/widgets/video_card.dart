import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../../../core/router/route_names.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_text_styles.dart';
import '../../../../core/utils/extensions.dart';
import '../../domain/entities/video_entity.dart';
import 'video_status_badge.dart';

class VideoCard extends StatelessWidget {
  const VideoCard({
    super.key,
    required this.video,
    required this.projectId,
    this.onDelete,
  });

  final VideoEntity video;
  final String projectId;
  final VoidCallback? onDelete;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () => context.push(
          RouteNames.videoDetailPath(projectId, video.id),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Thumbnail
            AspectRatio(
              aspectRatio: 16 / 9,
              child: video.thumbnailUrl != null
                  ? CachedNetworkImage(
                      imageUrl: video.thumbnailUrl!,
                      fit: BoxFit.cover,
                      placeholder: (_, __) => _PlaceholderThumbnail(
                        status: video.status,
                      ),
                      errorWidget: (_, __, ___) => _PlaceholderThumbnail(
                        status: video.status,
                      ),
                    )
                  : _PlaceholderThumbnail(status: video.status),
            ),
            Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          video.title,
                          style: theme.textTheme.titleSmall,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      PopupMenuButton<String>(
                        iconSize: 18,
                        padding: EdgeInsets.zero,
                        onSelected: (v) {
                          if (v == 'delete') onDelete?.call();
                        },
                        itemBuilder: (_) => [
                          const PopupMenuItem(
                            value: 'delete',
                            child: Row(children: [
                              Icon(Icons.delete_outline,
                                  size: 16, color: AppColors.error),
                              SizedBox(width: 8),
                              Text('Delete',
                                  style: TextStyle(color: AppColors.error)),
                            ]),
                          ),
                        ],
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Row(
                    children: [
                      VideoStatusBadge(status: video.status, compact: true),
                      const Spacer(),
                      if (video.durationSeconds != null)
                        Text(
                          video.durationSeconds!.formattedDuration,
                          style: AppTextStyles.labelSmall.copyWith(
                            color: theme.colorScheme.onSurfaceVariant,
                          ),
                        ),
                      const SizedBox(width: 8),
                      Text(
                        video.createdAt.timeAgo,
                        style: theme.textTheme.bodySmall,
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PlaceholderThumbnail extends StatelessWidget {
  const _PlaceholderThumbnail({required this.status});
  final String status;

  @override
  Widget build(BuildContext context) {
    final color = status.statusColor;
    final icon = switch (status) {
      'completed' => Icons.play_circle_fill_rounded,
      'failed' => Icons.error_outline_rounded,
      'processing' => Icons.autorenew_rounded,
      'uploading' => Icons.upload_rounded,
      _ => Icons.video_file_outlined,
    };
    return Container(
      color: color.withValues(alpha: 0.08),
      child: Center(
        child: Icon(icon, size: 48, color: color.withValues(alpha: 0.5)),
      ),
    );
  }
}
