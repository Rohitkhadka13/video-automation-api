import 'package:dartz/dartz.dart';
import 'package:equatable/equatable.dart';
import '../../../../core/error/failures.dart';
import '../../../../core/usecases/usecase.dart';
import '../repositories/project_repository.dart';

class DeleteProjectUseCase implements UseCase<Unit, DeleteProjectParams> {
  const DeleteProjectUseCase(this._repository);
  final ProjectRepository _repository;

  @override
  Future<Either<Failure, Unit>> call(DeleteProjectParams params) {
    return _repository.deleteProject(params.id);
  }
}

class DeleteProjectParams extends Equatable {
  const DeleteProjectParams({required this.id});
  final String id;

  @override
  List<Object> get props => [id];
}
