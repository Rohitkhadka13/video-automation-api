part of 'video_bloc.dart';

abstract class VideoEvent extends Equatable {
  const VideoEvent();
  @override
  List<Object?> get props => [];
}

class VideoLoadEvent extends VideoEvent {
  const VideoLoadEvent({required this.projectId, this.refresh = false});
  final String projectId;
  final bool refresh;
  @override
  List<Object> get props => [projectId, refresh];
}

class VideoCreateEvent extends VideoEvent {
  const VideoCreateEvent({
    required this.projectId,
    required this.title,
    this.description,
    this.scriptPrompt,
    this.voiceModel,
    this.language,
  });
  final String projectId;
  final String title;
  final String? description;
  final String? scriptPrompt;
  final String? voiceModel;
  final String? language;
  @override
  List<Object?> get props =>
      [projectId, title, description, scriptPrompt, voiceModel, language];
}

class VideoUploadEvent extends VideoEvent {
  const VideoUploadEvent({
    required this.videoId,
    required this.filePath,
    required this.mimeType,
  });
  final String videoId;
  final String filePath;
  final String mimeType;
  @override
  List<Object> get props => [videoId, filePath, mimeType];
}

class VideoProcessEvent extends VideoEvent {
  const VideoProcessEvent({required this.videoId});
  final String videoId;
  @override
  List<Object> get props => [videoId];
}

class VideoPollStatusEvent extends VideoEvent {
  const VideoPollStatusEvent({required this.videoId, required this.taskId});
  final String videoId;
  final String taskId;
  @override
  List<Object> get props => [videoId, taskId];
}

class VideoStopPollingEvent extends VideoEvent {
  const VideoStopPollingEvent();
}

class VideoDeleteEvent extends VideoEvent {
  const VideoDeleteEvent({required this.videoId, required this.projectId});
  final String videoId;
  final String projectId;
  @override
  List<Object> get props => [videoId, projectId];
}

class VideoUploadProgressEvent extends VideoEvent {
  const VideoUploadProgressEvent({required this.sent, required this.total});
  final int sent;
  final int total;
  @override
  List<Object> get props => [sent, total];
}
