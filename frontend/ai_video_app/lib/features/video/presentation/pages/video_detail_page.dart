import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:percent_indicator/linear_percent_indicator.dart';

import '../../../../core/di/injection_container.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_text_styles.dart';
import '../../../../core/utils/extensions.dart';
import '../../../../core/widgets/app_snackbar.dart';
import '../../../../core/widgets/custom_button.dart';
import '../bloc/video_bloc.dart';
import '../widgets/video_status_badge.dart';

class VideoDetailPage extends StatelessWidget {
  const VideoDetailPage({
    super.key,
    required this.projectId,
    required this.videoId,
  });

  final String projectId;
  final String videoId;

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (_) => sl<VideoBloc>()..add(VideoLoadEvent(projectId: projectId)),
      child: _VideoDetailView(projectId: projectId, videoId: videoId),
    );
  }
}

class _VideoDetailView extends StatelessWidget {
  const _VideoDetailView({
    required this.projectId,
    required this.videoId,
  });

  final String projectId;
  final String videoId;

  @override
  Widget build(BuildContext context) {
    return BlocConsumer<VideoBloc, VideoState>(
      listenWhen: (prev, curr) =>
          prev.errorMessage != curr.errorMessage ||
          prev.successMessage != curr.successMessage,
      listener: (context, state) {
        if (state.errorMessage != null) {
          AppSnackbar.error(context, state.errorMessage!);
        }
        if (state.successMessage != null) {
          AppSnackbar.success(context, state.successMessage!);
        }
      },
      builder: (context, state) {
        final video = state.videos.where((v) => v.id == videoId).firstOrNull;

        if (video == null) {
          return const Scaffold(
            body: Center(child: CircularProgressIndicator()),
          );
        }

        return Scaffold(
          appBar: AppBar(
            title: Text(video.title, overflow: TextOverflow.ellipsis),
            actions: [
              if (video.status == 'uploaded' || video.status == 'failed')
                IconButton(
                  icon: const Icon(Icons.play_arrow_rounded),
                  tooltip: 'Process video',
                  onPressed: () => context
                      .read<VideoBloc>()
                      .add(VideoProcessEvent(videoId: video.id)),
                ),
            ],
          ),
          body: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              // Thumbnail / player area
              Card(
                clipBehavior: Clip.antiAlias,
                child: AspectRatio(
                  aspectRatio: 16 / 9,
                  child: video.thumbnailUrl != null
                      ? Stack(
                          fit: StackFit.expand,
                          children: [
                            CachedNetworkImage(
                              imageUrl: video.thumbnailUrl!,
                              fit: BoxFit.cover,
                            ),
                            if (video.isCompleted && video.outputUrl != null)
                              Center(
                                child: CircleAvatar(
                                  radius: 28,
                                  backgroundColor:
                                      Colors.black.withValues(alpha: 0.5),
                                  child: const Icon(
                                    Icons.play_arrow_rounded,
                                    color: Colors.white,
                                    size: 36,
                                  ),
                                ),
                              ),
                          ],
                        )
                      : Container(
                          color: AppColors.primary.withValues(alpha: 0.08),
                          child: Center(
                            child: Icon(
                              Icons.video_file_outlined,
                              size: 64,
                              color: AppColors.primary.withValues(alpha: 0.4),
                            ),
                          ),
                        ),
                ),
              ),
              const SizedBox(height: 16),

              // Status + progress
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Text('Status',
                              style: Theme.of(context).textTheme.titleSmall),
                          const Spacer(),
                          VideoStatusBadge(status: video.status),
                        ],
                      ),
                      if (state.isPolling) ...[
                        const SizedBox(height: 14),
                        LinearPercentIndicator(
                          lineHeight: 6,
                          percent: state.taskProgress.clamp(0.0, 1.0),
                          backgroundColor:
                              AppColors.primary.withValues(alpha: 0.1),
                          progressColor: AppColors.primary,
                          barRadius: const Radius.circular(3),
                          padding: EdgeInsets.zero,
                          animation: true,
                          animateFromLastPercent: true,
                        ),
                        const SizedBox(height: 6),
                        Text(
                          state.taskMessage ?? 'Processing…',
                          style: AppTextStyles.bodySmall.copyWith(
                            color:
                                Theme.of(context).colorScheme.onSurfaceVariant,
                          ),
                        ),
                      ],
                      if (video.errorMessage != null) ...[
                        const SizedBox(height: 10),
                        Text(
                          video.errorMessage!,
                          style: AppTextStyles.bodySmall
                              .copyWith(color: AppColors.error),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 12),

              // Meta info
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    children: [
                      _InfoRow(
                        label: 'Created',
                        value: video.createdAt.formattedDateTime,
                      ),
                      if (video.durationSeconds != null)
                        _InfoRow(
                          label: 'Duration',
                          value: video.durationSeconds!.formattedDuration,
                        ),
                      if (video.resolution != null)
                        _InfoRow(
                          label: 'Resolution',
                          value: video.resolution!,
                        ),
                      if (video.fileSizeMb != null)
                        _InfoRow(
                          label: 'File size',
                          value: '${video.fileSizeMb!.toStringAsFixed(1)} MB',
                        ),
                      if (video.voiceModel != null)
                        _InfoRow(
                          label: 'Voice',
                          value: video.voiceModel!,
                        ),
                      if (video.language != null)
                        _InfoRow(
                          label: 'Language',
                          value: video.language!.toUpperCase(),
                        ),
                    ],
                  ),
                ),
              ),

              // Transcription
              if (video.transcriptionText != null) ...[
                const SizedBox(height: 12),
                _ExpandableCard(
                  title: 'Transcription',
                  icon: Icons.record_voice_over_outlined,
                  child: Text(
                    video.transcriptionText!,
                    style: AppTextStyles.bodySmall,
                  ),
                ),
              ],

              // Generated script
              if (video.generatedScript != null) ...[
                const SizedBox(height: 12),
                _ExpandableCard(
                  title: 'Generated Script',
                  icon: Icons.auto_fix_high_outlined,
                  child: Text(
                    video.generatedScript!,
                    style: AppTextStyles.bodySmall,
                  ),
                ),
              ],

              const SizedBox(height: 24),

              // Action buttons
              if (video.status == 'uploaded' || video.status == 'failed')
                AppButton(
                  label: 'Process with AI',
                  onPressed: () => context
                      .read<VideoBloc>()
                      .add(VideoProcessEvent(videoId: video.id)),
                  isLoading: state.isPolling,
                  prefixIcon: Icons.auto_fix_high_outlined,
                ),

              if (state.isPolling) ...[
                const SizedBox(height: 12),
                AppButton(
                  label: 'Cancel Polling',
                  variant: ButtonVariant.ghost,
                  onPressed: () => context
                      .read<VideoBloc>()
                      .add(const VideoStopPollingEvent()),
                ),
              ],
            ],
          ),
        );
      },
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(
        children: [
          Text(
            label,
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const Spacer(),
          Text(
            value,
            style: Theme.of(context)
                .textTheme
                .bodySmall
                ?.copyWith(fontWeight: FontWeight.w600),
          ),
        ],
      ),
    );
  }
}

class _ExpandableCard extends StatefulWidget {
  const _ExpandableCard({
    required this.title,
    required this.icon,
    required this.child,
  });
  final String title;
  final IconData icon;
  final Widget child;

  @override
  State<_ExpandableCard> createState() => _ExpandableCardState();
}

class _ExpandableCardState extends State<_ExpandableCard> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Column(
        children: [
          ListTile(
            leading: Icon(widget.icon, color: AppColors.primary, size: 20),
            title: Text(widget.title,
                style: Theme.of(context).textTheme.titleSmall),
            trailing: Icon(
              _expanded ? Icons.expand_less : Icons.expand_more,
            ),
            onTap: () => setState(() => _expanded = !_expanded),
          ),
          if (_expanded)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
              child: widget.child,
            ),
        ],
      ),
    );
  }
}
