import 'dart:convert';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../../../../core/constants/app_constants.dart';
import '../../../../core/error/exceptions.dart';
import '../models/user_model.dart';

abstract class AuthLocalDataSource {
  Future<void> saveTokens({
    required String accessToken,
    required String refreshToken,
  });
  Future<void> saveUser(UserModel user);
  Future<String?> getAccessToken();
  Future<String?> getRefreshToken();
  Future<UserModel?> getCachedUser();
  Future<void> clearAll();
}

class AuthLocalDataSourceImpl implements AuthLocalDataSource {
  const AuthLocalDataSourceImpl({required this.secureStorage});
  final FlutterSecureStorage secureStorage;

  @override
  Future<void> saveTokens({
    required String accessToken,
    required String refreshToken,
  }) async {
    try {
      await Future.wait([
        secureStorage.write(key: StorageKeys.accessToken, value: accessToken),
        secureStorage.write(key: StorageKeys.refreshToken, value: refreshToken),
      ]);
    } catch (e) {
      throw CacheException(message: 'Failed to save tokens: $e');
    }
  }

  @override
  Future<void> saveUser(UserModel user) async {
    try {
      final json = jsonEncode(user.toJson());
      await secureStorage.write(key: _userKey, value: json);
    } catch (e) {
      throw CacheException(message: 'Failed to save user: $e');
    }
  }

  @override
  Future<String?> getAccessToken() async {
    try {
      return await secureStorage.read(key: StorageKeys.accessToken);
    } catch (e) {
      return null;
    }
  }

  @override
  Future<String?> getRefreshToken() async {
    try {
      return await secureStorage.read(key: StorageKeys.refreshToken);
    } catch (e) {
      return null;
    }
  }

  @override
  Future<UserModel?> getCachedUser() async {
    try {
      final json = await secureStorage.read(key: _userKey);
      if (json == null) return null;
      return UserModel.fromJson(jsonDecode(json) as Map<String, dynamic>);
    } catch (e) {
      return null;
    }
  }

  @override
  Future<void> clearAll() async {
    try {
      await Future.wait([
        secureStorage.delete(key: StorageKeys.accessToken),
        secureStorage.delete(key: StorageKeys.refreshToken),
        secureStorage.delete(key: _userKey),
      ]);
    } catch (e) {
      throw CacheException(message: 'Failed to clear auth data: $e');
    }
  }

  static const String _userKey = 'cached_user';
}
