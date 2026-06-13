import 'dart:async';
import 'package:equatable/equatable.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../../core/constants/app_constants.dart';
import '../../domain/entities/video_entity.dart';
import '../../domain/usecases/create_video_usecase.dart';
import '../../domain/usecases/get_video_status_usecase.dart';
import '../../domain/usecases/get_videos_usecase.dart';
import '../../domain/usecases/process_video_usecase.dart';
import '../../domain/usecases/upload_video_usecase.dart';

part 'video_event.dart';
part 'video_state.dart';

class VideoBloc extends Bloc<VideoEvent, VideoState> {
  VideoBloc({
    required this.getVideosUseCase,
    required this.createVideoUseCase,
    required this.uploadVideoUseCase,
    required this.processVideoUseCase,
    required this.getVideoStatusUseCase,
  }) : super(const VideoState()) {
    on<VideoLoadEvent>(_onLoad);
    on<VideoCreateEvent>(_onCreate);
    on<VideoUploadEvent>(_onUpload);
    on<VideoProcessEvent>(_onProcess);
    on<VideoPollStatusEvent>(_onPollStatus);
    on<VideoStopPollingEvent>(_onStopPolling);
    on<VideoDeleteEvent>(_onDelete);
    on<VideoUploadProgressEvent>(_onUploadProgress);
  }

  final GetVideosUseCase getVideosUseCase;
  final CreateVideoUseCase createVideoUseCase;
  final UploadVideoUseCase uploadVideoUseCase;
  final ProcessVideoUseCase processVideoUseCase;
  final GetVideoStatusUseCase getVideoStatusUseCase;

  Timer? _pollTimer;
  int _pollFailureCount = 0;
  static const int _pageSize = 20;

  @override
  Future<void> close() {
    _pollTimer?.cancel();
    return super.close();
  }

  Future<void> _onLoad(VideoLoadEvent event, Emitter<VideoState> emit) async {
    if (event.refresh || state.currentProjectId != event.projectId) {
      emit(state.copyWith(
        status: VideoStatus.loading,
        videos: [],
        currentPage: 0,
        hasMore: true,
        currentProjectId: event.projectId,
        clearError: true,
      ));
    } else {
      emit(state.copyWith(status: VideoStatus.loading, clearError: true));
    }

    final result = await getVideosUseCase(
      GetVideosParams(projectId: event.projectId, skip: 0, limit: _pageSize),
    );

    result.fold(
      (f) => emit(state.copyWith(
        status: VideoStatus.failure,
        errorMessage: f.message,
      )),
      (videos) => emit(state.copyWith(
        status: VideoStatus.loaded,
        videos: videos,
        hasMore: videos.length >= _pageSize,
        currentPage: 1,
      )),
    );
  }

  Future<void> _onCreate(
    VideoCreateEvent event,
    Emitter<VideoState> emit,
  ) async {
    emit(state.copyWith(status: VideoStatus.loading, clearError: true));

    final result = await createVideoUseCase(CreateVideoParams(
      projectId: event.projectId,
      title: event.title,
      description: event.description,
      scriptPrompt: event.scriptPrompt,
      voiceModel: event.voiceModel,
      language: event.language,
    ));

    result.fold(
      (f) => emit(state.copyWith(
        status: VideoStatus.failure,
        errorMessage: f.message,
      )),
      (video) => emit(state.copyWith(
        status: VideoStatus.success,
        videos: [video, ...state.videos],
        successMessage: 'Video record created',
      )),
    );
  }

  Future<void> _onUpload(
    VideoUploadEvent event,
    Emitter<VideoState> emit,
  ) async {
    emit(state.copyWith(
      status: VideoStatus.uploading,
      uploadProgress: 0.0,
      clearError: true,
    ));

    final result = await uploadVideoUseCase(UploadVideoParams(
      videoId: event.videoId,
      filePath: event.filePath,
      mimeType: event.mimeType,
      onProgress: (sent, total) {
        if (!isClosed) {
          add(VideoUploadProgressEvent(sent: sent, total: total));
        }
      },
    ));

    result.fold(
      (f) => emit(state.copyWith(
        status: VideoStatus.failure,
        errorMessage: f.message,
      )),
      (video) {
        // Update video in list
        final updated =
            state.videos.map((v) => v.id == video.id ? video : v).toList();
        emit(state.copyWith(
          status: VideoStatus.success,
          videos: updated,
          uploadProgress: 1.0,
          successMessage: 'Upload complete',
        ));
      },
    );
  }

  void _onUploadProgress(
    VideoUploadProgressEvent event,
    Emitter<VideoState> emit,
  ) {
    if (event.total > 0) {
      emit(state.copyWith(
        uploadProgress: event.sent / event.total,
      ));
    }
  }

  Future<void> _onProcess(
    VideoProcessEvent event,
    Emitter<VideoState> emit,
  ) async {
    emit(state.copyWith(
      status: VideoStatus.processing,
      taskProgress: 0.0,
      clearError: true,
    ));

    final result = await processVideoUseCase(
      ProcessVideoParams(videoId: event.videoId),
    );

    result.fold(
      (f) => emit(state.copyWith(
        status: VideoStatus.failure,
        errorMessage: f.message,
      )),
      (data) {
        final taskId = data['task_id'] as String?;
        emit(state.copyWith(
          status: VideoStatus.polling,
          activeTaskId: taskId,
        ));
        if (taskId != null) {
          _startPolling(event.videoId, taskId);
        }
      },
    );
  }

  Future<void> _onPollStatus(
    VideoPollStatusEvent event,
    Emitter<VideoState> emit,
  ) async {
    final result = await getVideoStatusUseCase(
      GetVideoStatusParams(videoId: event.videoId),
    );

    result.fold(
      (f) {
        _pollFailureCount++;
        if (_pollFailureCount >= AppConstants.taskPollMaxFailures) {
          _pollTimer?.cancel();
          emit(state.copyWith(
            status: VideoStatus.failure,
            errorMessage: 'Lost connection during processing',
            clearTask: true,
          ));
        }
      },
      (video) {
        _pollFailureCount = 0;
        final updated =
            state.videos.map((v) => v.id == video.id ? video : v).toList();

        if (video.isTerminal) {
          _pollTimer?.cancel();
          emit(state.copyWith(
            status:
                video.isCompleted ? VideoStatus.success : VideoStatus.failure,
            videos: updated,
            errorMessage: video.isFailed ? video.errorMessage : null,
            successMessage:
                video.isCompleted ? 'Video processed successfully!' : null,
            clearTask: true,
          ));
        } else {
          emit(state.copyWith(
            status: VideoStatus.polling,
            videos: updated,
          ));
        }
      },
    );
  }

  void _onStopPolling(VideoStopPollingEvent event, Emitter<VideoState> emit) {
    _pollTimer?.cancel();
    emit(state.copyWith(status: VideoStatus.loaded, clearTask: true));
  }

  Future<void> _onDelete(
    VideoDeleteEvent event,
    Emitter<VideoState> emit,
  ) async {
    // Optimistic removal
    final updated = state.videos.where((v) => v.id != event.videoId).toList();
    emit(state.copyWith(videos: updated, successMessage: 'Video deleted'));
  }

  void _startPolling(String videoId, String taskId) {
    _pollTimer?.cancel();
    _pollFailureCount = 0;
    _pollTimer = Timer.periodic(AppConstants.taskPollInterval, (_) {
      if (!isClosed) {
        add(VideoPollStatusEvent(videoId: videoId, taskId: taskId));
      }
    });
  }
}
