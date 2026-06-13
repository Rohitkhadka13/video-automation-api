import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:logger/logger.dart';

import '../constants/api_constants.dart';
import '../constants/app_constants.dart';
import '../error/exceptions.dart';

// =============================================================================
// AuthInterceptor — attaches JWT access token to every request
// =============================================================================

class AuthInterceptor extends Interceptor {
  AuthInterceptor({required this.secureStorage});

  final FlutterSecureStorage secureStorage;

  @override
  Future<void> onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    final token = await secureStorage.read(key: StorageKeys.accessToken);
    if (token != null && token.isNotEmpty) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }
}

// =============================================================================
// RefreshInterceptor — silently refreshes expired access tokens on 401
// =============================================================================

class RefreshInterceptor extends Interceptor {
  RefreshInterceptor({
    required this.dio,
    required this.secureStorage,
  });

  final Dio dio;
  final FlutterSecureStorage secureStorage;
  bool _isRefreshing = false;

  @override
  Future<void> onResponse(
    Response<dynamic> response,
    ResponseInterceptorHandler handler,
  ) async {
    if (response.statusCode == 401) {
      await _handleUnauthorized(response.requestOptions, handler);
      return;
    }
    handler.next(response);
  }

  @override
  Future<void> onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    if (err.response?.statusCode == 401 && !_isRefreshing) {
      await _handleUnauthorized(err.requestOptions, handler);
      return;
    }
    handler.next(err);
  }

  Future<void> _handleUnauthorized(
    RequestOptions originalRequest,
    dynamic handler,
  ) async {
    if (_isRefreshing) {
      handler.next(
        DioException(
          requestOptions: originalRequest,
          error: const TokenExpiredException(),
        ),
      );
      return;
    }

    _isRefreshing = true;

    try {
      final refreshToken =
          await secureStorage.read(key: StorageKeys.refreshToken);

      if (refreshToken == null || refreshToken.isEmpty) {
        throw const TokenExpiredException();
      }

      // Use a fresh Dio instance to avoid interceptor loop
      final refreshDio = Dio(
        BaseOptions(
          baseUrl: dio.options.baseUrl,
          connectTimeout: dio.options.connectTimeout,
          receiveTimeout: dio.options.receiveTimeout,
        ),
      );

      final response = await refreshDio.post<Map<String, dynamic>>(
        ApiConstants.authRefresh,
        data: {'refresh_token': refreshToken},
      );

      if (response.statusCode == 200 && response.data != null) {
        final data = response.data!;
        final newAccessToken = data['access_token'] as String;
        final newRefreshToken = data['refresh_token'] as String;

        // Persist new tokens
        await Future.wait([
          secureStorage.write(
            key: StorageKeys.accessToken,
            value: newAccessToken,
          ),
          secureStorage.write(
            key: StorageKeys.refreshToken,
            value: newRefreshToken,
          ),
        ]);

        // Retry original request with new token
        originalRequest.headers['Authorization'] = 'Bearer $newAccessToken';
        final retryResponse = await dio.fetch<dynamic>(originalRequest);
        handler.resolve(retryResponse);
      } else {
        throw const TokenExpiredException();
      }
    } catch (_) {
      // Clear stored tokens — force re-login
      await Future.wait([
        secureStorage.delete(key: StorageKeys.accessToken),
        secureStorage.delete(key: StorageKeys.refreshToken),
      ]);
      handler.next(
        DioException(
          requestOptions: originalRequest,
          error: const TokenExpiredException(),
        ),
      );
    } finally {
      _isRefreshing = false;
    }
  }
}

// =============================================================================
// LoggingInterceptor — pretty-prints requests/responses in debug mode
// =============================================================================

class LoggingInterceptor extends Interceptor {
  LoggingInterceptor()
      : _logger = Logger(
          printer: PrettyPrinter(
            methodCount: 0,
            errorMethodCount: 5,
            lineLength: 80,
            colors: true,
            printEmojis: true,
          ),
        );

  final Logger _logger;

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    if (kDebugMode) {
      _logger.d(
        '📤 ${options.method} ${options.uri}\n'
        'Headers: ${options.headers}\n'
        'Data: ${options.data}',
      );
    }
    handler.next(options);
  }

  @override
  void onResponse(
    Response<dynamic> response,
    ResponseInterceptorHandler handler,
  ) {
    if (kDebugMode) {
      _logger.d(
        '📥 ${response.statusCode} ${response.requestOptions.uri}\n'
        'Data: ${response.data}',
      );
    }
    handler.next(response);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    if (kDebugMode) {
      _logger.e(
        '❌ ${err.response?.statusCode} ${err.requestOptions.uri}\n'
        '${err.message}',
        error: err,
        stackTrace: err.stackTrace,
      );
    }
    handler.next(err);
  }
}

// =============================================================================
// ErrorInterceptor — maps HTTP status codes → typed AppExceptions
// =============================================================================

class ErrorInterceptor extends Interceptor {
  @override
  void onResponse(
    Response<dynamic> response,
    ResponseInterceptorHandler handler,
  ) {
    final status = response.statusCode ?? 0;

    if (status >= 200 && status < 300) {
      handler.next(response);
      return;
    }

    final message = _extractMessage(response.data);

    final exception = switch (status) {
      400 => ValidationException(message: message, code: status.toString()),
      401 => UnauthorizedException(message: message, code: status.toString()),
      403 => ForbiddenException(message: message, code: status.toString()),
      404 => NotFoundException(message: message, code: status.toString()),
      409 => ConflictException(message: message, code: status.toString()),
      413 => const FileTooLargeException(),
      422 => ValidationException(
          message: message,
          code: status.toString(),
          fieldErrors: _extractFieldErrors(response.data),
        ),
      429 => RateLimitException(
          message: message,
          code: status.toString(),
          retryAfterSeconds: _extractRetryAfter(response.headers),
        ),
      >= 500 => ServerException(
          message: message,
          code: status.toString(),
          statusCode: status,
        ),
      _ => ServerException(
          message: message,
          statusCode: status,
        ),
    };

    handler.reject(
      DioException(
        requestOptions: response.requestOptions,
        response: response,
        error: exception,
        type: DioExceptionType.badResponse,
      ),
      true,
    );
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    // If already mapped to an AppException, pass through
    if (err.error is AppException) {
      handler.next(err);
      return;
    }

    final exception = switch (err.type) {
      DioExceptionType.connectionTimeout ||
      DioExceptionType.sendTimeout ||
      DioExceptionType.receiveTimeout =>
        const TimeoutException(),
      DioExceptionType.connectionError => const NetworkException(),
      _ => ServerException(
          message: err.message ?? 'Unexpected error',
          statusCode: err.response?.statusCode,
        ),
    };

    handler.next(
      DioException(
        requestOptions: err.requestOptions,
        response: err.response,
        error: exception,
        type: err.type,
      ),
    );
  }

  String _extractMessage(dynamic data) {
    if (data is Map<String, dynamic>) {
      return (data['detail'] as String?) ??
          (data['message'] as String?) ??
          'An error occurred';
    }
    return 'An error occurred';
  }

  Map<String, List<String>>? _extractFieldErrors(dynamic data) {
    if (data is Map<String, dynamic> && data['errors'] is List) {
      final errors = <String, List<String>>{};
      for (final e in data['errors'] as List) {
        if (e is Map<String, dynamic>) {
          final field = e['field'] as String? ?? 'general';
          final message = e['message'] as String? ?? '';
          errors.putIfAbsent(field, () => []).add(message);
        }
      }
      return errors.isEmpty ? null : errors;
    }
    return null;
  }

  int? _extractRetryAfter(Headers headers) {
    final value = headers.value('Retry-After');
    return value != null ? int.tryParse(value) : null;
  }
}
