import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';
import 'package:mime/mime.dart';

import '../../../../core/constants/app_constants.dart';
import '../../../../core/di/injection_container.dart';
import '../../../../core/router/route_names.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_text_styles.dart';
import '../../../../core/utils/validators.dart';
import '../../../../core/widgets/app_snackbar.dart';
import '../../../../core/widgets/custom_button.dart';
import '../../../../core/widgets/custom_text_field.dart';
import '../bloc/video_bloc.dart';
import '../widgets/upload_progress_widget.dart';

class VideoUploadPage extends StatelessWidget {
  const VideoUploadPage({super.key, required this.projectId});
  final String projectId;

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (_) => sl<VideoBloc>(),
      child: _VideoUploadView(projectId: projectId),
    );
  }
}

class _VideoUploadView extends StatefulWidget {
  const _VideoUploadView({required this.projectId});
  final String projectId;

  @override
  State<_VideoUploadView> createState() => _VideoUploadViewState();
}

class _VideoUploadViewState extends State<_VideoUploadView> {
  final _formKey = GlobalKey<FormState>();
  final _titleCtrl = TextEditingController();
  final _descCtrl = TextEditingController();
  final _promptCtrl = TextEditingController();

  PlatformFile? _pickedFile;
  String? _mimeType;
  String _step = 'form'; // 'form' | 'uploading' | 'processing'

  @override
  void dispose() {
    _titleCtrl.dispose();
    _descCtrl.dispose();
    _promptCtrl.dispose();
    super.dispose();
  }

  Future<void> _pickFile() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: AppConstants.allowedVideoExtensions +
          AppConstants.allowedAudioExtensions,
      withData: false,
      withReadStream: false,
    );

    if (result != null && result.files.isNotEmpty) {
      final file = result.files.first;
      final mime = lookupMimeType(file.path ?? '') ?? 'video/mp4';

      // Basic size check
      if (file.size > AppConstants.maxUploadSizeBytes) {
        if (mounted) {
          AppSnackbar.error(
            context,
            'File too large. Maximum size is ${AppConstants.maxUploadSizeMb} MB.',
          );
        }
        return;
      }

      setState(() {
        _pickedFile = file;
        _mimeType = mime;
        // Auto-fill title from filename
        if (_titleCtrl.text.isEmpty) {
          final name = file.name.replaceAll(RegExp(r'\.[^.]+$'), '');
          _titleCtrl.text = name;
        }
      });
    }
  }

  Future<void> _submit(BuildContext ctx) async {
    if (!_formKey.currentState!.validate()) return;
    if (_pickedFile == null || _pickedFile!.path == null) {
      AppSnackbar.error(ctx, 'Please select a video file first');
      return;
    }

    final bloc = ctx.read<VideoBloc>();

    // Step 1: Create video record
    bloc.add(VideoCreateEvent(
      projectId: widget.projectId,
      title: _titleCtrl.text.trim(),
      description: _descCtrl.text.trim().isEmpty ? null : _descCtrl.text.trim(),
      scriptPrompt:
          _promptCtrl.text.trim().isEmpty ? null : _promptCtrl.text.trim(),
    ));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Upload Video')),
      body: BlocConsumer<VideoBloc, VideoState>(
        listenWhen: (prev, curr) =>
            prev.status != curr.status ||
            prev.errorMessage != curr.errorMessage,
        listener: (context, state) {
          if (state.errorMessage != null) {
            AppSnackbar.error(context, state.errorMessage!);
          }

          // After video record created → start upload
          if (state.status == VideoStatus.success &&
              state.videos.isNotEmpty &&
              _step == 'form' &&
              _pickedFile != null) {
            setState(() => _step = 'uploading');
            final newVideo = state.videos.first;
            context.read<VideoBloc>().add(VideoUploadEvent(
                  videoId: newVideo.id,
                  filePath: _pickedFile!.path!,
                  mimeType: _mimeType ?? 'video/mp4',
                ));
          }

          // After upload done → trigger processing
          if (state.status == VideoStatus.success && _step == 'uploading') {
            setState(() => _step = 'processing');
            final uploadedVideo = state.videos.firstWhere(
              (v) => v.status == 'uploaded',
              orElse: () => state.videos.first,
            );
            context.read<VideoBloc>().add(
                  VideoProcessEvent(videoId: uploadedVideo.id),
                );
          }

          // Processing complete → navigate to detail
          if (state.status == VideoStatus.success && _step == 'processing') {
            AppSnackbar.success(context, 'Video is being processed!');
            final video = state.videos.first;
            context.go(RouteNames.videoDetailPath(widget.projectId, video.id));
          }
        },
        builder: (context, state) {
          // Show upload progress
          if (_step == 'uploading') {
            return UploadProgressWidget(
              progress: state.uploadProgress,
              label: 'Uploading "${_titleCtrl.text}"',
              subtitle: '${state.uploadPercent}% uploaded…',
            );
          }

          // Show processing progress
          if (_step == 'processing') {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(32),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const CircularProgressIndicator(color: AppColors.primary),
                    const SizedBox(height: 24),
                    Text('Queuing AI processing…',
                        style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 8),
                    Text(
                      'Whisper transcription → Ollama script → Piper TTS → FFmpeg merge',
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color:
                                Theme.of(context).colorScheme.onSurfaceVariant,
                          ),
                    ),
                  ],
                ),
              ),
            );
          }

          // Default: the form
          return SingleChildScrollView(
            padding: const EdgeInsets.all(20),
            child: Form(
              key: _formKey,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // File picker area
                  GestureDetector(
                    onTap: _pickFile,
                    child: AnimatedContainer(
                      duration: const Duration(milliseconds: 200),
                      height: 140,
                      decoration: BoxDecoration(
                        color: _pickedFile != null
                            ? AppColors.primary.withValues(alpha: 0.06)
                            : Theme.of(context)
                                .colorScheme
                                .surfaceContainerHighest,
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(
                          color: _pickedFile != null
                              ? AppColors.primary
                              : Theme.of(context).colorScheme.outline,
                          width: _pickedFile != null ? 1.5 : 1,
                        ),
                      ),
                      child: _pickedFile == null
                          ? Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(
                                  Icons.upload_file_rounded,
                                  size: 40,
                                  color: Theme.of(context)
                                      .colorScheme
                                      .onSurfaceVariant,
                                ),
                                const SizedBox(height: 10),
                                Text(
                                  'Tap to select a video file',
                                  style: AppTextStyles.bodyMedium.copyWith(
                                    color: Theme.of(context)
                                        .colorScheme
                                        .onSurfaceVariant,
                                  ),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  'MP4, MOV, AVI, MKV, WEBM · max ${AppConstants.maxUploadSizeMb} MB',
                                  style: AppTextStyles.bodySmall.copyWith(
                                    color: Theme.of(context)
                                        .colorScheme
                                        .onSurfaceVariant,
                                  ),
                                ),
                              ],
                            )
                          : Padding(
                              padding: const EdgeInsets.all(16),
                              child: Row(
                                children: [
                                  const Icon(Icons.video_file_rounded,
                                      size: 40, color: AppColors.primary),
                                  const SizedBox(width: 12),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      mainAxisAlignment:
                                          MainAxisAlignment.center,
                                      children: [
                                        Text(
                                          _pickedFile!.name,
                                          style: AppTextStyles.titleSmall,
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                        const SizedBox(height: 4),
                                        Text(
                                          '${(_pickedFile!.size / (1024 * 1024)).toStringAsFixed(1)} MB · ${_mimeType ?? ''}',
                                          style:
                                              AppTextStyles.bodySmall.copyWith(
                                            color: Theme.of(context)
                                                .colorScheme
                                                .onSurfaceVariant,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                  IconButton(
                                    icon: const Icon(Icons.close, size: 20),
                                    onPressed: () => setState(() {
                                      _pickedFile = null;
                                      _mimeType = null;
                                    }),
                                  ),
                                ],
                              ),
                            ),
                    ),
                  ),
                  const SizedBox(height: 24),

                  AppTextField(
                    label: 'Video title',
                    hint: 'Give your video a name',
                    controller: _titleCtrl,
                    prefixIcon: Icons.title,
                    validator: Validators.videoTitle,
                  ),
                  const SizedBox(height: 16),

                  AppTextField(
                    label: 'Description (optional)',
                    hint: 'What is this video about?',
                    controller: _descCtrl,
                    prefixIcon: Icons.notes,
                    maxLines: 3,
                  ),
                  const SizedBox(height: 16),

                  AppTextField(
                    label: 'AI Script Prompt (optional)',
                    hint: 'Guide the AI when rewriting the script…',
                    controller: _promptCtrl,
                    prefixIcon: Icons.auto_fix_high_outlined,
                    maxLines: 4,
                  ),
                  const SizedBox(height: 32),

                  BlocBuilder<VideoBloc, VideoState>(
                    builder: (context, state) => AppButton(
                      label: 'Upload & Process',
                      onPressed: () => _submit(context),
                      isLoading: state.isLoading || state.isUploading,
                      prefixIcon: Icons.rocket_launch_outlined,
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}
