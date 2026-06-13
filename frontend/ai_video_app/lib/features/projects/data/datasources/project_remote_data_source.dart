import 'package:dio/dio.dart';
import '../../../../core/constants/api_constants.dart';
import '../../../../core/error/exceptions.dart';
import '../models/project_model.dart';

abstract class ProjectRemoteDataSource {
  Future<List<ProjectModel>> getProjects({int skip = 0, int limit = 20});
  Future<ProjectModel> getProjectById(String id);
  Future<ProjectModel> createProject(Map<String, dynamic> data);
  Future<ProjectModel> updateProject(String id, Map<String, dynamic> data);
  Future<void> deleteProject(String id);
}

class ProjectRemoteDataSourceImpl implements ProjectRemoteDataSource {
  const ProjectRemoteDataSourceImpl({required this.dio});
  final Dio dio;

  @override
  Future<List<ProjectModel>> getProjects({
    int skip = 0,
    int limit = 20,
  }) async {
    try {
      final response = await dio.get<Map<String, dynamic>>(
        ApiConstants.projects,
        queryParameters: {'skip': skip, 'limit': limit},
      );
      final items = response.data!['items'] as List<dynamic>;
      return items
          .map((e) => ProjectModel.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw _map(e);
    }
  }

  @override
  Future<ProjectModel> getProjectById(String id) async {
    try {
      final response = await dio.get<Map<String, dynamic>>(
        ApiConstants.projectById(id),
      );
      return ProjectModel.fromJson(response.data!);
    } on DioException catch (e) {
      throw _map(e);
    }
  }

  @override
  Future<ProjectModel> createProject(Map<String, dynamic> data) async {
    try {
      final response = await dio.post<Map<String, dynamic>>(
        ApiConstants.projects,
        data: data,
      );
      return ProjectModel.fromJson(response.data!);
    } on DioException catch (e) {
      throw _map(e);
    }
  }

  @override
  Future<ProjectModel> updateProject(
    String id,
    Map<String, dynamic> data,
  ) async {
    try {
      final response = await dio.patch<Map<String, dynamic>>(
        ApiConstants.projectById(id),
        data: data,
      );
      return ProjectModel.fromJson(response.data!);
    } on DioException catch (e) {
      throw _map(e);
    }
  }

  @override
  Future<void> deleteProject(String id) async {
    try {
      await dio.delete<void>(ApiConstants.projectById(id));
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
