import 'package:dio/dio.dart';
import '../../../../core/constants/api_constants.dart';
import '../../../../core/error/exceptions.dart';
import '../models/profile_model.dart';

abstract class ProfileRemoteDataSource {
  Future<ProfileModel> getProfile();
  Future<ProfileModel> updateProfile(Map<String, dynamic> data);
  Future<void> changePassword({
    required String currentPassword,
    required String newPassword,
  });
}

class ProfileRemoteDataSourceImpl implements ProfileRemoteDataSource {
  const ProfileRemoteDataSourceImpl({required this.dio});
  final Dio dio;

  @override
  Future<ProfileModel> getProfile() async {
    try {
      final response =
          await dio.get<Map<String, dynamic>>(ApiConstants.usersMe);
      return ProfileModel.fromJson(response.data!);
    } on DioException catch (e) {
      throw _map(e);
    }
  }

  @override
  Future<ProfileModel> updateProfile(Map<String, dynamic> data) async {
    try {
      final response = await dio.patch<Map<String, dynamic>>(
        ApiConstants.usersMe,
        data: data,
      );
      return ProfileModel.fromJson(response.data!);
    } on DioException catch (e) {
      throw _map(e);
    }
  }

  @override
  Future<void> changePassword({
    required String currentPassword,
    required String newPassword,
  }) async {
    try {
      await dio.post<void>(
        ApiConstants.userPassword,
        data: {
          'current_password': currentPassword,
          'new_password': newPassword,
        },
      );
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
