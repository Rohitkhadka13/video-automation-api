import 'package:equatable/equatable.dart';

/// Base class for all domain-layer failures.
/// Use cases return [Either<Failure, T>] — UI maps these to user-facing messages.
abstract class Failure extends Equatable {
  const Failure({
    required this.message,
    this.code,
  });

  final String message;
  final String? code;

  @override
  List<Object?> get props => [message, code];

  @override
  String toString() => '$runtimeType(message: $message, code: $code)';
}

// ── Network failures ──────────────────────────────────────────────────────────

/// No internet connection available.
class NetworkFailure extends Failure {
  const NetworkFailure({
    super.message = 'No internet connection. Please check your network.',
    super.code,
  });
}

/// Request timed out.
class TimeoutFailure extends Failure {
  const TimeoutFailure({
    super.message = 'Request timed out. Please try again.',
    super.code,
  });
}

/// Server returned an unexpected error (5xx).
class ServerFailure extends Failure {
  const ServerFailure({
    required super.message,
    super.code,
    this.statusCode,
  });

  final int? statusCode;

  @override
  List<Object?> get props => [...super.props, statusCode];
}

// ── Auth failures ─────────────────────────────────────────────────────────────

/// Invalid credentials on login.
class AuthFailure extends Failure {
  const AuthFailure({
    super.message = 'Invalid email or password.',
    super.code,
  });
}

/// Access or refresh token has expired.
class TokenExpiredFailure extends Failure {
  const TokenExpiredFailure({
    super.message = 'Your session has expired. Please log in again.',
    super.code,
  });
}

/// User is not authenticated.
class UnauthenticatedFailure extends Failure {
  const UnauthenticatedFailure({
    super.message = 'Please log in to continue.',
    super.code,
  });
}

/// User does not have permission to perform the action.
class UnauthorizedFailure extends Failure {
  const UnauthorizedFailure({
    super.message = 'You do not have permission to perform this action.',
    super.code,
  });
}

// ── Resource failures ─────────────────────────────────────────────────────────

/// Requested resource was not found.
class NotFoundFailure extends Failure {
  const NotFoundFailure({
    super.message = 'The requested resource was not found.',
    super.code,
    this.resource,
  });

  final String? resource;

  @override
  List<Object?> get props => [...super.props, resource];
}

/// Resource already exists (e.g. duplicate email).
class ConflictFailure extends Failure {
  const ConflictFailure({
    required super.message,
    super.code,
  });
}

// ── Validation failures ───────────────────────────────────────────────────────

/// Request payload failed server-side validation.
class ValidationFailure extends Failure {
  const ValidationFailure({
    required super.message,
    super.code,
    this.fieldErrors,
  });

  /// Map of field name → list of error messages.
  final Map<String, List<String>>? fieldErrors;

  @override
  List<Object?> get props => [...super.props, fieldErrors];
}

/// Uploaded file is too large.
class FileTooLargeFailure extends Failure {
  const FileTooLargeFailure({
    super.message = 'File is too large. Maximum size is 500 MB.',
    super.code,
  });
}

/// Uploaded file type is not supported.
class InvalidFileTypeFailure extends Failure {
  const InvalidFileTypeFailure({
    super.message = 'File type not supported.',
    super.code,
  });
}

// ── Rate limit ────────────────────────────────────────────────────────────────

/// Too many requests — rate limit exceeded.
class RateLimitFailure extends Failure {
  const RateLimitFailure({
    super.message = 'Too many requests. Please wait a moment and try again.',
    super.code,
    this.retryAfterSeconds,
  });

  final int? retryAfterSeconds;

  @override
  List<Object?> get props => [...super.props, retryAfterSeconds];
}

// ── Local storage failures ────────────────────────────────────────────────────

/// Cache read/write failure.
class CacheFailure extends Failure {
  const CacheFailure({
    super.message = 'Local storage error. Please try again.',
    super.code,
  });
}

// ── Unexpected failure ────────────────────────────────────────────────────────

/// Catch-all for unhandled errors.
class UnexpectedFailure extends Failure {
  const UnexpectedFailure({
    super.message = 'An unexpected error occurred. Please try again.',
    super.code,
  });
}
