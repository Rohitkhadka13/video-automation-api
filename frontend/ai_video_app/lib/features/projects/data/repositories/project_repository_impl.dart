import 'package:dartz/dartz.dart';
import '../../../../core/error/exceptions.dart';
import '../../../../core/error/failures.dart';
import '../../../../core/network/network_info.dart';
import '../../domain/entities/project_entity.dart';
import '../../domain/repositories/project_repository.dart';
import '../datasources/project_remote_data_source.dart';

class ProjectRepositoryImpl implements ProjectRepository {
  const ProjectRepositoryImpl({
    required this.remoteDataSource,
    required this.networkInfo,
  });

  final ProjectRemoteDataSource remoteDataSource;
  final NetworkInfo networkInfo;

  @override
  Future<Either<Failure, List<ProjectEntity>>> getProjects({
    int skip = 0,
    int limit = 20,
  }) async {
    if (!await networkInfo.isConnected) return const Left(NetworkFailure());
    try {
      final projects =
          await remoteDataSource.getProjects(skip: skip, limit: limit);
      return Right(projects);
    } on NotFoundException {
      return const Right([]);
    } on AppException catch (e) {
      return Left(_toFailure(e));
    }
  }

  @override
  Future<Either<Failure, ProjectEntity>> getProjectById(String id) async {
    if (!await networkInfo.isConnected) return const Left(NetworkFailure());
    try {
      final project = await remoteDataSource.getProjectById(id);
      return Right(project);
    } on AppException catch (e) {
      return Left(_toFailure(e));
    }
  }

  @override
  Future<Either<Failure, ProjectEntity>> createProject({
    required String name,
    String? description,
    String defaultVoiceModel = 'en_US-lessac-medium',
    String defaultLanguage = 'en',
    String defaultLlmModel = 'llama3',
  }) async {
    if (!await networkInfo.isConnected) return const Left(NetworkFailure());
    try {
      final project = await remoteDataSource.createProject({
        'name': name,
        if (description != null) 'description': description,
        'default_voice_model': defaultVoiceModel,
        'default_language': defaultLanguage,
        'default_llm_model': defaultLlmModel,
      });
      return Right(project);
    } on AppException catch (e) {
      return Left(_toFailure(e));
    }
  }

  @override
  Future<Either<Failure, ProjectEntity>> updateProject({
    required String id,
    String? name,
    String? description,
    String? defaultVoiceModel,
    String? defaultLanguage,
    String? defaultLlmModel,
  }) async {
    if (!await networkInfo.isConnected) return const Left(NetworkFailure());
    try {
      final data = <String, dynamic>{
        if (name != null) 'name': name,
        if (description != null) 'description': description,
        if (defaultVoiceModel != null) 'default_voice_model': defaultVoiceModel,
        if (defaultLanguage != null) 'default_language': defaultLanguage,
        if (defaultLlmModel != null) 'default_llm_model': defaultLlmModel,
      };
      final project = await remoteDataSource.updateProject(id, data);
      return Right(project);
    } on AppException catch (e) {
      return Left(_toFailure(e));
    }
  }

  @override
  Future<Either<Failure, Unit>> deleteProject(String id) async {
    if (!await networkInfo.isConnected) return const Left(NetworkFailure());
    try {
      await remoteDataSource.deleteProject(id);
      return const Right(unit);
    } on AppException catch (e) {
      return Left(_toFailure(e));
    }
  }

  Failure _toFailure(AppException e) {
    return switch (e) {
      NotFoundException() => NotFoundFailure(message: e.message),
      ConflictException() => ConflictFailure(message: e.message),
      NetworkException() => const NetworkFailure(),
      TimeoutException() => const TimeoutFailure(),
      _ => ServerFailure(message: e.message),
    };
  }
}
