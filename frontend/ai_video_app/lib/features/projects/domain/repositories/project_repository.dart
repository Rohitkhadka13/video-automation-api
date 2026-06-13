import 'package:dartz/dartz.dart';
import '../../../../core/error/failures.dart';
import '../entities/project_entity.dart';

abstract class ProjectRepository {
  Future<Either<Failure, List<ProjectEntity>>> getProjects({
    int skip = 0,
    int limit = 20,
  });

  Future<Either<Failure, ProjectEntity>> getProjectById(String id);

  Future<Either<Failure, ProjectEntity>> createProject({
    required String name,
    String? description,
    String defaultVoiceModel = 'en_US-lessac-medium',
    String defaultLanguage = 'en',
    String defaultLlmModel = 'llama3',
  });

  Future<Either<Failure, ProjectEntity>> updateProject({
    required String id,
    String? name,
    String? description,
    String? defaultVoiceModel,
    String? defaultLanguage,
    String? defaultLlmModel,
  });

  Future<Either<Failure, Unit>> deleteProject(String id);
}
