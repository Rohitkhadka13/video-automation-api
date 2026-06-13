import 'package:dio/dio.dart';
import '../../../../core/constants/api_constants.dart';
import '../../../../core/error/exceptions.dart';
import '../models/token_model.dart';
import '../models/user_model.dart';

abstract class AuthRemoteDataSource {
  Future<({TokenModel tokens, UserModel user})> login({
    required String email,
    required String password,
  });

  Future<({TokenModel tokens, UserModel user})> register({
    required String email,
    required String password,
    required String fullName,
  });

  Future<void> logout();
  Future<TokenModel> refreshToken(String refreshToken);
  Future<UserModel> getMe();
}

class AuthRemoteDataSourceImpl implements AuthRemoteDataSource {
  const AuthRemoteDataSourceImpl({required this.dio});
  final Dio dio;

  @override
  Future<({TokenModel tokens, UserModel user})> login({
    required String email,
    required String password,
  }) async {
    try {
      // 1. Login → get tokens
      final loginResponse = await dio.post<Map<String, dynamic>>(
        ApiConstants.authLogin,
        data: {'email': email, 'password': password},
      );
      final tokens = TokenModel.fromJson(loginResponse.data!);

      // 2. Fetch user profile with the new access token
      final meResponse = await dio.get<Map<String, dynamic>>(
        ApiConstants.authMe,
        options: Options(
          headers: {'Authorization': 'Bearer ${tokens.accessToken}'},
        ),
      );
      final user = UserModel.fromJson(meResponse.data!);

      return (tokens: tokens, user: user);
    } on DioException catch (e) {
      throw _mapDioException(e);
    }
  }

  @override
  Future<({TokenModel tokens, UserModel user})> register({
    required String email,
    required String password,
    required String fullName,
  }) async {
    try {
      // 1. Register
      await dio.post<Map<String, dynamic>>(
        ApiConstants.users,
        data: {
          'email': email,
          'password': password,
          'full_name': fullName,
        },
      );

      // 2. Auto-login after registration
      return login(email: email, password: password);
    } on DioException catch (e) {
      throw _mapDioException(e);
    }
  }

  @override
  Future<void> logout() async {
    try {
      await dio.post<void>(ApiConstants.authLogout);
    } on DioException catch (e) {
      // Ignore 401 on logout — token may already be expired
      if (e.response?.statusCode != 401) {
        throw _mapDioException(e);
      }
    }
  }

  @override
  Future<TokenModel> refreshToken(String refreshToken) async {
    try {
      final response = await dio.post<Map<String, dynamic>>(
        ApiConstants.authRefresh,
        data: {'refresh_token': refreshToken},
      );
      return TokenModel.fromJson(response.data!);
    } on DioException catch (e) {
      throw _mapDioException(e);
    }
  }

  @override
  Future<UserModel> getMe() async {
    try {
      final response = await dio.get<Map<String, dynamic>>(ApiConstants.authMe);
      return UserModel.fromJson(response.data!);
    } on DioException catch (e) {
      throw _mapDioException(e);
    }
  }

  AppException _mapDioException(DioException e) {
    if (e.error is AppException) return e.error as AppException;
    return ServerException(
      message: e.message ?? 'Network error',
      statusCode: e.response?.statusCode,
    );
  }
}
