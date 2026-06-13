part of 'video_bloc.dart';

enum VideoStatus {
  initial,
  loading,
  loaded,
  uploading,
  processing,
  polling,
  success,
  failure,
}

class VideoState extends Equatable {
  const VideoState({
    this.status = VideoStatus.initial,
    this.videos = const [],
    this.activeTaskId,
    this.uploadProgress = 0.0,
    this.taskProgress = 0.0,
    this.taskMessage,
    this.errorMessage,
    this.successMessage,
    this.hasMore = true,
    this.currentPage = 0,
    this.currentProjectId,
  });

  final VideoStatus status;
  final List<VideoEntity> videos;
  final String? activeTaskId;
  final double uploadProgress; // 0.0 – 1.0
  final double taskProgress; // 0.0 – 1.0
  final String? taskMessage;
  final String? errorMessage;
  final String? successMessage;
  final bool hasMore;
  final int currentPage;
  final String? currentProjectId;

  bool get isLoading => status == VideoStatus.loading;
  bool get isUploading => status == VideoStatus.uploading;
  bool get isPolling => status == VideoStatus.polling;
  bool get isEmpty => videos.isEmpty && status == VideoStatus.loaded;

  int get uploadPercent => (uploadProgress * 100).toInt();
  int get taskPercent => (taskProgress * 100).toInt();

  VideoState copyWith({
    VideoStatus? status,
    List<VideoEntity>? videos,
    String? activeTaskId,
    double? uploadProgress,
    double? taskProgress,
    String? taskMessage,
    String? errorMessage,
    String? successMessage,
    bool? hasMore,
    int? currentPage,
    String? currentProjectId,
    bool clearError = false,
    bool clearSuccess = false,
    bool clearTask = false,
  }) {
    return VideoState(
      status: status ?? this.status,
      videos: videos ?? this.videos,
      activeTaskId: clearTask ? null : (activeTaskId ?? this.activeTaskId),
      uploadProgress: uploadProgress ?? this.uploadProgress,
      taskProgress: taskProgress ?? this.taskProgress,
      taskMessage: clearTask ? null : (taskMessage ?? this.taskMessage),
      errorMessage: clearError ? null : (errorMessage ?? this.errorMessage),
      successMessage:
          clearSuccess ? null : (successMessage ?? this.successMessage),
      hasMore: hasMore ?? this.hasMore,
      currentPage: currentPage ?? this.currentPage,
      currentProjectId: currentProjectId ?? this.currentProjectId,
    );
  }

  @override
  List<Object?> get props => [
        status,
        videos,
        activeTaskId,
        uploadProgress,
        taskProgress,
        taskMessage,
        errorMessage,
        successMessage,
        hasMore,
        currentPage,
        currentProjectId,
      ];
}
