import 'package:dartz/dartz.dart';
import '../../../../core/error/exceptions.dart';
import '../../../../core/error/failures.dart';
import '../../../../core/network/network_info.dart';
import '../../domain/entities/task_entity.dart';
import '../../domain/entities/video_entity.dart';
import '../../domain/repositories/video_repository.dart';
import '../datasources/video_remote_data_source.dart';

class VideoRepositoryImpl implements VideoRepository {
  const VideoRepositoryImpl({
    required this.remoteDataSource,
    required this.networkInfo,
  });

  final VideoRemoteDataSource remoteDataSource;
  final NetworkInfo networkInfo;

  @override
  Future<Either<Failure, List<VideoEntity>>> getVideos({
    required String projectId,
    int skip = 0,
    int limit = 20,
    List<String>? statusFilter,
  }) async {
    if (!await networkInfo.isConnected) return const Left(NetworkFailure());
    try {
      final videos = await remoteDataSource.getVideos(
        projectId: projectId,
        skip: skip,
        limit: limit,
        statusFilter: statusFilter,
      );
      return Right(videos);
    } on AppException catch (e) {
      return Left(_toFailure(e));
    }
  }

  @override
  Future<Either<Failure, VideoEntity>> getVideoById({
    required String videoId,
    required String projectId,
  }) async {
    if (!await networkInfo.isConnected) return const Left(NetworkFailure());
    try {
      final video = await remoteDataSource.getVideoById(
        videoId: videoId,
        projectId: projectId,
      );
      return Right(video);
    } on AppException catch (e) {
      return Left(_toFailure(e));
    }
  }

  @override
  Future<Either<Failure, VideoEntity>> createVideo({
    required String projectId,
    required String title,
    String? description,
    String? scriptPrompt,
    String? voiceModel,
    String? language,
  }) async {
    if (!await networkInfo.isConnected) return const Left(NetworkFailure());
    try {
      final video = await remoteDataSource.createVideo(projectId, {
        'title': title,
        if (description != null) 'description': description,
        if (scriptPrompt != null) 'script_prompt': scriptPrompt,
        if (voiceModel != null) 'voice_model': voiceModel,
        if (language != null) 'language': language,
      });
      return Right(video);
    } on AppException catch (e) {
      return Left(_toFailure(e));
    }
  }

  @override
  Future<Either<Failure, VideoEntity>> uploadVideo({
    required String videoId,
    required String filePath,
    required String mimeType,
    void Function(int sent, int total)? onProgress,
  }) async {
    if (!await networkInfo.isConnected) return const Left(NetworkFailure());
    try {
      final video = await remoteDataSource.uploadVideo(
        videoId: videoId,
        filePath: filePath,
        mimeType: mimeType,
        onProgress: onProgress,
      );
      return Right(video);
    } on FileTooLargeException {
      return const Left(FileTooLargeFailure());
    } on InvalidFileTypeException {
      return const Left(InvalidFileTypeFailure());
    } on AppException catch (e) {
      return Left(_toFailure(e));
    }
  }

  @override
  Future<Either<Failure, Map<String, dynamic>>> processVideo({
    required String videoId,
  }) async {
    if (!await networkInfo.isConnected) return const Left(NetworkFailure());
    try {
      final result = await remoteDataSource.processVideo(videoId);
      return Right(result);
    } on AppException catch (e) {
      return Left(_toFailure(e));
    }
  }

  @override
  Future<Either<Failure, VideoEntity>> getVideoStatus({
    required String videoId,
  }) async {
    if (!await networkInfo.isConnected) return const Left(NetworkFailure());
    try {
      final video = await remoteDataSource.getVideoStatus(videoId);
      return Right(video);
    } on AppException catch (e) {
      return Left(_toFailure(e));
    }
  }

  @override
  Future<Either<Failure, Unit>> deleteVideo({
    required String videoId,
    required String projectId,
  }) async {
    if (!await networkInfo.isConnected) return const Left(NetworkFailure());
    try {
      await remoteDataSource.deleteVideo(
        videoId: videoId,
        projectId: projectId,
      );
      return const Right(unit);
    } on AppException catch (e) {
      return Left(_toFailure(e));
    }
  }

  @override
  Future<Either<Failure, TaskEntity>> getTaskById(String taskId) async {
    if (!await networkInfo.isConnected) return const Left(NetworkFailure());
    try {
      final task = await remoteDataSource.getTaskById(taskId);
      return Right(task);
    } on AppException catch (e) {
      return Left(_toFailure(e));
    }
  }

  @override
  Future<Either<Failure, TaskEntity>> getTaskStatus(String taskId) async {
    if (!await networkInfo.isConnected) return const Left(NetworkFailure());
    try {
      final task = await remoteDataSource.getTaskStatus(taskId);
      return Right(task);
    } on AppException catch (e) {
      return Left(_toFailure(e));
    }
  }

  Failure _toFailure(AppException e) => switch (e) {
        NotFoundException() => NotFoundFailure(message: e.message),
        ConflictException() => ConflictFailure(message: e.message),
        NetworkException() => const NetworkFailure(),
        TimeoutException() => const TimeoutFailure(),
        FileTooLargeException() => const FileTooLargeFailure(),
        _ => ServerFailure(message: e.message),
      };
}
