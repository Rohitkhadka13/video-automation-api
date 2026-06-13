import 'package:dartz/dartz.dart';
import '../../../../core/error/failures.dart';
import '../entities/user_entity.dart';

/// Abstract auth repository contract.
/// Implemented in the data layer — domain layer never imports data layer.
abstract class AuthRepository {
  /// Login with email and password.
  /// Returns [UserEntity] on success, [Failure] on error.
  Future<Either<Failure, UserEntity>> login({
    required String email,
    required String password,
  });

  /// Register a new account.
  Future<Either<Failure, UserEntity>> register({
    required String email,
    required String password,
    required String fullName,
  });

  /// Logout and clear stored tokens.
  Future<Either<Failure, Unit>> logout();

  /// Silently refresh the access token using the stored refresh token.
  Future<Either<Failure, Unit>> refreshToken();

  /// Return the currently authenticated user from local cache.
  /// Returns null if not authenticated.
  Future<Either<Failure, UserEntity?>> getCurrentUser();

  /// True if a valid access token is stored locally.
  Future<bool> isAuthenticated();
}
