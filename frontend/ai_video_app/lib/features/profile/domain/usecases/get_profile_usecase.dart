import 'package:dartz/dartz.dart';
import '../../../../core/error/failures.dart';
import '../../../../core/usecases/usecase.dart';
import '../entities/profile_entity.dart';
import '../repositories/profile_repository.dart';

class GetProfileUseCase implements NoParamsUseCase<ProfileEntity> {
  const GetProfileUseCase(this._repo);
  final ProfileRepository _repo;

  @override
  Future<Either<Failure, ProfileEntity>> call() => _repo.getProfile();
}
