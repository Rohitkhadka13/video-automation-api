import 'package:dartz/dartz.dart';
import '../../../../core/error/failures.dart';
import '../entities/task_entity.dart';
import '../entities/video_entity.dart';

abstract class VideoRepository {
  Future<Either<Failure, List<VideoEntity>>> getVideos({
    required String projectId,
    int skip = 0,
    int limit = 20,
    List<String>? statusFilter,
  });

  Future<Either<Failure, VideoEntity>> getVideoById({
    required String videoId,
    required String projectId,
  });

  Future<Either<Failure, VideoEntity>> createVideo({
    required String projectId,
    required String title,
    String? description,
    String? scriptPrompt,
    String? voiceModel,
    String? language,
  });

  Future<Either<Failure, VideoEntity>> uploadVideo({
    required String videoId,
    required String filePath,
    required String mimeType,
    void Function(int sent, int total)? onProgress,
  });

  Future<Either<Failure, Map<String, dynamic>>> processVideo({
    required String videoId,
  });

  Future<Either<Failure, VideoEntity>> getVideoStatus({
    required String videoId,
  });

  Future<Either<Failure, Unit>> deleteVideo({
    required String videoId,
    required String projectId,
  });

  Future<Either<Failure, TaskEntity>> getTaskById(String taskId);

  Future<Either<Failure, TaskEntity>> getTaskStatus(String taskId);
}
