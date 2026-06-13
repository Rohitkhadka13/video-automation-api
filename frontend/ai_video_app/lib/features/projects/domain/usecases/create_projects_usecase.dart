import 'package:dartz/dartz.dart';
import 'package:equatable/equatable.dart';
import '../../../../core/error/failures.dart';
import '../../../../core/usecases/usecase.dart';
import '../entities/project_entity.dart';
import '../repositories/project_repository.dart';

class CreateProjectUseCase
    implements UseCase<ProjectEntity, CreateProjectParams> {
  const CreateProjectUseCase(this._repository);
  final ProjectRepository _repository;

  @override
  Future<Either<Failure, ProjectEntity>> call(CreateProjectParams params) {
    return _repository.createProject(
      name: params.name,
      description: params.description,
      defaultVoiceModel: params.defaultVoiceModel,
      defaultLanguage: params.defaultLanguage,
      defaultLlmModel: params.defaultLlmModel,
    );
  }
}

class CreateProjectParams extends Equatable {
  const CreateProjectParams({
    required this.name,
    this.description,
    this.defaultVoiceModel = 'en_US-lessac-medium',
    this.defaultLanguage = 'en',
    this.defaultLlmModel = 'llama3',
  });
  final String name;
  final String? description;
  final String defaultVoiceModel;
  final String defaultLanguage;
  final String defaultLlmModel;

  @override
  List<Object?> get props =>
      [name, description, defaultVoiceModel, defaultLanguage, defaultLlmModel];
}
