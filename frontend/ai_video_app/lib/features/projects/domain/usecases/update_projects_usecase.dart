import 'package:dartz/dartz.dart';
import 'package:equatable/equatable.dart';
import '../../../../core/error/failures.dart';
import '../../../../core/usecases/usecase.dart';
import '../entities/project_entity.dart';
import '../repositories/project_repository.dart';

class UpdateProjectUseCase
    implements UseCase<ProjectEntity, UpdateProjectParams> {
  const UpdateProjectUseCase(this._repository);
  final ProjectRepository _repository;

  @override
  Future<Either<Failure, ProjectEntity>> call(UpdateProjectParams params) {
    return _repository.updateProject(
      id: params.id,
      name: params.name,
      description: params.description,
      defaultVoiceModel: params.defaultVoiceModel,
      defaultLanguage: params.defaultLanguage,
      defaultLlmModel: params.defaultLlmModel,
    );
  }
}

class UpdateProjectParams extends Equatable {
  const UpdateProjectParams({
    required this.id,
    this.name,
    this.description,
    this.defaultVoiceModel,
    this.defaultLanguage,
    this.defaultLlmModel,
  });
  final String id;
  final String? name;
  final String? description;
  final String? defaultVoiceModel;
  final String? defaultLanguage;
  final String? defaultLlmModel;

  @override
  List<Object?> get props => [
        id,
        name,
        description,
        defaultVoiceModel,
        defaultLanguage,
        defaultLlmModel
      ];
}
