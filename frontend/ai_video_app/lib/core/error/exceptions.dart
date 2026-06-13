/// Base class for all data-layer exceptions.
/// These are thrown by [RemoteDataSource] and [LocalDataSource] classes.
/// Repositories catch them and convert to [Failure] types for use cases.
abstract class AppException implements Exception {
  const AppException({
    required this.message,
    this.code,
  });

  final String message;
  final String? code;

  @override
  String toString() => '$runtimeType(message: $message, code: $code)';
}

// ── Network exceptions ────────────────────────────────────────────────────────

class NetworkException extends AppException {
  const NetworkException({
    super.message = 'No internet connection.',
    super.code,
  });
}

class TimeoutException extends AppException {
  const TimeoutException({
    super.message = 'Request timed out.',
    super.code,
  });
}

class ServerException extends AppException {
  const ServerException({
    required super.message,
    super.code,
    this.statusCode,
  });

  final int? statusCode;
}

// ── Auth exceptions ───────────────────────────────────────────────────────────

class UnauthorizedException extends AppException {
  const UnauthorizedException({
    super.message = 'Unauthorized.',
    super.code,
  });
}

class ForbiddenException extends AppException {
  const ForbiddenException({
    super.message = 'Forbidden.',
    super.code,
  });
}

class TokenExpiredException extends AppException {
  const TokenExpiredException({
    super.message = 'Token has expired.',
    super.code,
  });
}

// ── Resource exceptions ───────────────────────────────────────────────────────

class NotFoundException extends AppException {
  const NotFoundException({
    super.message = 'Resource not found.',
    super.code,
  });
}

class ConflictException extends AppException {
  const ConflictException({
    required super.message,
    super.code,
  });
}

// ── Validation exceptions ─────────────────────────────────────────────────────

class ValidationException extends AppException {
  const ValidationException({
    required super.message,
    super.code,
    this.fieldErrors,
  });

  final Map<String, List<String>>? fieldErrors;
}

class FileTooLargeException extends AppException {
  const FileTooLargeException({
    super.message = 'File exceeds maximum allowed size.',
    super.code,
  });
}

class InvalidFileTypeException extends AppException {
  const InvalidFileTypeException({
    super.message = 'File type not supported.',
    super.code,
  });
}

// ── Rate limit ────────────────────────────────────────────────────────────────

class RateLimitException extends AppException {
  const RateLimitException({
    super.message = 'Rate limit exceeded.',
    super.code,
    this.retryAfterSeconds,
  });

  final int? retryAfterSeconds;
}

// ── Cache exceptions ──────────────────────────────────────────────────────────

class CacheException extends AppException {
  const CacheException({
    super.message = 'Local cache error.',
    super.code,
  });
}

// ── Parse exceptions ──────────────────────────────────────────────────────────

class ParseException extends AppException {
  const ParseException({
    super.message = 'Failed to parse server response.',
    super.code,
  });
}
