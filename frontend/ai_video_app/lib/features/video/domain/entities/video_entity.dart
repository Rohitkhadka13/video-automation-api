import 'package:equatable/equatable.dart';

class VideoEntity extends Equatable {
  const VideoEntity({
    required this.id,
    required this.title,
    required this.slug,
    required this.projectId,
    required this.ownerId,
    required this.status,
    required this.createdAt,
    required this.updatedAt,
    this.description,
    this.originalFilename,
    this.mimeType,
    this.fileSizeBytes,
    this.fileSizeMb,
    this.durationSeconds,
    this.width,
    this.height,
    this.fps,
    this.resolution,
    this.voiceModel,
    this.language,
    this.scriptPrompt,
    this.transcriptionText,
    this.generatedScript,
    this.outputUrl,
    this.thumbnailUrl,
    this.errorMessage,
  });

  final String id;
  final String title;
  final String slug;
  final String projectId;
  final String ownerId;
  final String status;
  final DateTime createdAt;
  final DateTime updatedAt;
  final String? description;
  final String? originalFilename;
  final String? mimeType;
  final int? fileSizeBytes;
  final double? fileSizeMb;
  final double? durationSeconds;
  final int? width;
  final int? height;
  final double? fps;
  final String? resolution;
  final String? voiceModel;
  final String? language;
  final String? scriptPrompt;
  final String? transcriptionText;
  final String? generatedScript;
  final String? outputUrl;
  final String? thumbnailUrl;
  final String? errorMessage;

  bool get isCompleted => status == 'completed';
  bool get isProcessing =>
      status == 'processing' || status == 'uploading' || status == 'uploaded';
  bool get isFailed => status == 'failed';
  bool get isPending => status == 'pending';
  bool get isTerminal => isCompleted || isFailed || status == 'cancelled';

  @override
  List<Object?> get props => [
        id,
        title,
        slug,
        projectId,
        ownerId,
        status,
        createdAt,
        updatedAt,
        description,
        originalFilename,
        mimeType,
        fileSizeBytes,
        durationSeconds,
        width,
        height,
        fps,
        resolution,
        voiceModel,
        language,
        scriptPrompt,
        transcriptionText,
        generatedScript,
        outputUrl,
        thumbnailUrl,
        errorMessage,
      ];
}
