import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/di/injection_container.dart';
import '../../../../core/router/route_names.dart';
import '../../../../core/widgets/app_snackbar.dart';
import '../../../../core/widgets/loading_widget.dart';
import '../bloc/video_bloc.dart';
import '../widgets/video_card.dart';

class VideosPage extends StatelessWidget {
  const VideosPage({super.key, required this.projectId});
  final String projectId;

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (_) => sl<VideoBloc>()..add(VideoLoadEvent(projectId: projectId)),
      child: _VideosView(projectId: projectId),
    );
  }
}

class _VideosView extends StatefulWidget {
  const _VideosView({required this.projectId});
  final String projectId;

  @override
  State<_VideosView> createState() => _VideosViewState();
}

class _VideosViewState extends State<_VideosView> {
  final _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (_scrollController.position.pixels >=
        _scrollController.position.maxScrollExtent - 200) {
      // Load more if needed (add pagination event here)
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Videos'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_outlined),
            onPressed: () => context.read<VideoBloc>().add(
                VideoLoadEvent(projectId: widget.projectId, refresh: true)),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () =>
            context.push(RouteNames.videoUploadPath(widget.projectId)),
        icon: const Icon(Icons.add),
        label: const Text('Upload Video'),
      ),
      body: BlocConsumer<VideoBloc, VideoState>(
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
          if (state.isLoading && state.videos.isEmpty) {
            return const ShimmerList(count: 4, cardHeight: 200);
          }
          if (state.isEmpty) {
            return _EmptyState(
              onUploadTap: () =>
                  context.push(RouteNames.videoUploadPath(widget.projectId)),
            );
          }
          return RefreshIndicator(
            onRefresh: () async => context.read<VideoBloc>().add(
                VideoLoadEvent(projectId: widget.projectId, refresh: true)),
            child: GridView.builder(
              controller: _scrollController,
              padding: const EdgeInsets.fromLTRB(0, 8, 0, 100),
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 1,
                mainAxisExtent: 240,
              ),
              itemCount: state.videos.length,
              itemBuilder: (_, i) {
                final video = state.videos[i];
                return VideoCard(
                  video: video,
                  projectId: widget.projectId,
                  onDelete: () => context.read<VideoBloc>().add(
                        VideoDeleteEvent(
                          videoId: video.id,
                          projectId: widget.projectId,
                        ),
                      ),
                );
              },
            ),
          );
        },
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.onUploadTap});
  final VoidCallback onUploadTap;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.video_library_outlined,
              size: 80,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
            const SizedBox(height: 16),
            Text('No videos yet',
                style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            Text(
              'Upload a video to start the AI processing pipeline.',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
            ),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: onUploadTap,
              icon: const Icon(Icons.upload_outlined),
              label: const Text('Upload Video'),
            ),
          ],
        ),
      ),
    );
  }
}
