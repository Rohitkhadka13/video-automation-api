import 'package:equatable/equatable.dart';

class TaskEntity extends Equatable {
  const TaskEntity({
    required this.id,
    required this.videoId,
    required this.taskType,
    required this.status,
    required this.retryCount,
    required this.progress,
    required this.progressPercent,
    required this.isTerminal,
    required this.createdAt,
    required this.updatedAt,
    this.celeryTaskId,
    this.progressMessage,
    this.resultData,
    this.errorType,
    this.errorMessage,
    this.logLines = const [],
    this.startedAt,
    this.completedAt,
    this.durationSeconds,
    this.durationFormatted,
  });

  final String id;
  final String videoId;
  final String taskType;
  final String status;
  final int retryCount;
  final double progress;
  final int progressPercent;
  final bool isTerminal;
  final DateTime createdAt;
  final DateTime updatedAt;
  final String? celeryTaskId;
  final String? progressMessage;
  final Map<String, dynamic>? resultData;
  final String? errorType;
  final String? errorMessage;
  final List<String> logLines;
  final DateTime? startedAt;
  final DateTime? completedAt;
  final double? durationSeconds;
  final String? durationFormatted;

  bool get isSuccess => status == 'success';
  bool get isRunning =>
      status == 'pending' || status == 'started' || status == 'retry';

  @override
  List<Object?> get props => [
        id,
        videoId,
        taskType,
        status,
        retryCount,
        progress,
        progressPercent,
        isTerminal,
        createdAt,
        updatedAt,
        progressMessage,
        errorMessage,
      ];
}
