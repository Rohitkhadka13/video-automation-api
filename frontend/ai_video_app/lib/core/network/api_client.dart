import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../constants/api_constants.dart';
import 'dio_interceptors.dart';

/// Creates and configures the Dio HTTP client singleton.
/// Registered in GetIt and injected into all data sources.
///
/// Interceptors applied (in order):
///   1. [AuthInterceptor]     — attaches Bearer token to every request
///   2. [RefreshInterceptor]  — silently refreshes expired tokens (401 handling)
///   3. [LoggingInterceptor]  — logs requests/responses in debug mode
///   4. [ErrorInterceptor]    — maps DioException → typed AppException
Dio createDio({required FlutterSecureStorage secureStorage}) {
  final dio = Dio(
    BaseOptions(
      baseUrl: kDebugMode ? ApiConstants.baseUrlDev : ApiConstants.baseUrlProd,
      connectTimeout: ApiConstants.connectTimeout,
      receiveTimeout: ApiConstants.receiveTimeout,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-Client-Type': 'flutter',
        'X-App-Version': '1.0.0',
      },
      validateStatus: (status) {
        // Accept all status codes — let ErrorInterceptor map them to exceptions.
        return status != null && status < 600;
      },
    ),
  );

  // Add interceptors — order matters
  dio.interceptors.addAll([
    AuthInterceptor(secureStorage: secureStorage),
    RefreshInterceptor(dio: dio, secureStorage: secureStorage),
    if (kDebugMode) LoggingInterceptor(),
    ErrorInterceptor(),
  ]);

  return dio;
}

/// Separate Dio instance used exclusively for token refresh requests.
/// Does NOT have AuthInterceptor or RefreshInterceptor to avoid circular calls.
Dio createRefreshDio() {
  return Dio(
    BaseOptions(
      baseUrl: kDebugMode ? ApiConstants.baseUrlDev : ApiConstants.baseUrlProd,
      connectTimeout: ApiConstants.connectTimeout,
      receiveTimeout: ApiConstants.receiveTimeout,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    ),
  );
}
