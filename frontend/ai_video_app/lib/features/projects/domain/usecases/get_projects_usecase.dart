import 'package:dartz/dartz.dart';
import 'package:equatable/equatable.dart';
import '../../../../core/error/failures.dart';
import '../../../../core/usecases/usecase.dart';
import '../entities/project_entity.dart';
import '../repositories/project_repository.dart';

class GetProjectsUseCase
    implements UseCase<List<ProjectEntity>, GetProjectsParams> {
  const GetProjectsUseCase(this._repository);
  final ProjectRepository _repository;

  @override
  Future<Either<Failure, List<ProjectEntity>>> call(GetProjectsParams params) {
    return _repository.getProjects(skip: params.skip, limit: params.limit);
  }
}

class GetProjectsParams extends Equatable {
  const GetProjectsParams({this.skip = 0, this.limit = 20});
  final int skip;
  final int limit;

  @override
  List<Object> get props => [skip, limit];
}
