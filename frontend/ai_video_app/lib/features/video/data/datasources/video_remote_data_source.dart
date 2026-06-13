import 'package:dio/dio.dart';
import '../../../../core/constants/api_constants.dart';
import '../../../../core/error/exceptions.dart';
import '../models/task_model.dart';
import '../models/video_model.dart';

abstract class VideoRemoteDataSource {
  Future<List<VideoModel>> getVideos({
    required String projectId,
    int skip = 0,
    int limit = 20,
    List<String>? statusFilter,
  });
  Future<VideoModel> getVideoById({
    required String videoId,
    required String projectId,
  });
  Future<VideoModel> createVideo(String projectId, Map<String, dynamic> data);
  Future<VideoModel> uploadVideo({
    required String videoId,
    required String filePath,
    required String mimeType,
    void Function(int, int)? onProgress,
  });
  Future<Map<String, dynamic>> processVideo(String videoId);
  Future<VideoModel> getVideoStatus(String videoId);
  Future<void> deleteVideo(
      {required String videoId, required String projectId});
  Future<TaskModel> getTaskById(String taskId);
  Future<TaskModel> getTaskStatus(String taskId);
}

class VideoRemoteDataSourceImpl implements VideoRemoteDataSource {
  const VideoRemoteDataSourceImpl({required this.dio});
  final Dio dio;

  @override
  Future<List<VideoModel>> getVideos({
    required String projectId,
    int skip = 0,
    int limit = 20,
    List<String>? statusFilter,
  }) async {
    try {
      final response = await dio.get<Map<String, dynamic>>(
        ApiConstants.listVideos(projectId),
        queryParameters: {
          'skip': skip,
          'limit': limit,
          if (statusFilter != null) 'status_filter': statusFilter,
        },
      );
      final items = response.data!['items'] as List<dynamic>;
      return items
          .map((e) => VideoModel.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw _map(e);
    }
  }

  @override
  Future<VideoModel> getVideoById({
    required String videoId,
    required String projectId,
  }) async {
    try {
      final response = await dio.get<Map<String, dynamic>>(
        ApiConstants.videoById(videoId),
        queryParameters: {'project_id': projectId},
      );
      return VideoModel.fromJson(response.data!);
    } on DioException catch (e) {
      throw _map(e);
    }
  }

  @override
  Future<VideoModel> createVideo(
    String projectId,
    Map<String, dynamic> data,
  ) async {
    try {
      final response = await dio.post<Map<String, dynamic>>(
        ApiConstants.projectVideos(projectId),
        data: data,
      );
      return VideoModel.fromJson(response.data!);
    } on DioException catch (e) {
      throw _map(e);
    }
  }

  @override
  Future<VideoModel> uploadVideo({
    required String videoId,
    required String filePath,
    required String mimeType,
    void Function(int, int)? onProgress,
  }) async {
    try {
      final formData = FormData.fromMap({
        'file': await MultipartFile.fromFile(filePath,
            contentType: DioMediaType.parse(mimeType)),
      });
      final response = await dio.post<Map<String, dynamic>>(
        ApiConstants.uploadVideo(videoId),
        data: formData,
        options: Options(
          sendTimeout: ApiConstants.uploadTimeout,
          receiveTimeout: ApiConstants.uploadTimeout,
        ),
        onSendProgress: onProgress,
      );
      return VideoModel.fromJson(response.data!);
    } on DioException catch (e) {
      throw _map(e);
    }
  }

  @override
  Future<Map<String, dynamic>> processVideo(String videoId) async {
    try {
      final response = await dio.post<Map<String, dynamic>>(
        ApiConstants.processVideo(videoId),
        data: {},
      );
      return response.data!;
    } on DioException catch (e) {
      throw _map(e);
    }
  }

  @override
  Future<VideoModel> getVideoStatus(String videoId) async {
    try {
      final response = await dio.get<Map<String, dynamic>>(
        ApiConstants.videoStatus(videoId),
      );
      return VideoModel.fromJson(response.data!);
    } on DioException catch (e) {
      throw _map(e);
    }
  }

  @override
  Future<void> deleteVideo({
    required String videoId,
    required String projectId,
  }) async {
    try {
      await dio.delete<void>(
        ApiConstants.deleteVideo(videoId),
        queryParameters: {'project_id': projectId},
      );
    } on DioException catch (e) {
      throw _map(e);
    }
  }

  @override
  Future<TaskModel> getTaskById(String taskId) async {
    try {
      final response = await dio.get<Map<String, dynamic>>(
        ApiConstants.taskById(taskId),
      );
      return TaskModel.fromJson(response.data!);
    } on DioException catch (e) {
      throw _map(e);
    }
  }

  @override
  Future<TaskModel> getTaskStatus(String taskId) async {
    try {
      final response = await dio.get<Map<String, dynamic>>(
        ApiConstants.taskStatus(taskId),
      );
      return TaskModel.fromJson(response.data!);
    } on DioException catch (e) {
      throw _map(e);
    }
  }

  AppException _map(DioException e) {
    if (e.error is AppException) return e.error as AppException;
    return ServerException(
      message: e.message ?? 'Network error',
      statusCode: e.response?.statusCode,
    );
  }
}
