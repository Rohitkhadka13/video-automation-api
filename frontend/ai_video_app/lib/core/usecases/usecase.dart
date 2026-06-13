import 'package:dartz/dartz.dart';
import 'package:equatable/equatable.dart';

import '../error/failures.dart';

/// Generic use case contract for use cases that accept parameters.
///
/// Type parameters:
///   [Type]   — the success return type
///   [Params] — the input parameters class
///
/// Usage:
///   class LoginUseCase implements UseCase<UserEntity, LoginParams> {
///     @override
///     Future<Either<Failure, UserEntity>> call(LoginParams params) async { ... }
///   }
abstract class UseCase<Type, Params> {
  Future<Either<Failure, Type>> call(Params params);
}

/// Use case contract for use cases that take NO parameters.
///
/// Usage:
///   class GetProfileUseCase implements NoParamsUseCase<ProfileEntity> {
///     @override
///     Future<Either<Failure, ProfileEntity>> call() async { ... }
///   }
abstract class NoParamsUseCase<Type> {
  Future<Either<Failure, Type>> call();
}

/// Use case contract for streaming use cases (e.g. real-time polling).
abstract class StreamUseCase<Type, Params> {
  Stream<Either<Failure, Type>> call(Params params);
}

/// Sentinel class for use cases that accept no parameters.
/// Use with [UseCase<Type, NoParams>].
class NoParams extends Equatable {
  const NoParams();

  @override
  List<Object?> get props => [];
}
