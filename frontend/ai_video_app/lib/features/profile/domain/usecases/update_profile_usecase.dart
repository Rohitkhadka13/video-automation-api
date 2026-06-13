import 'package:dartz/dartz.dart';
import 'package:equatable/equatable.dart';
import '../../../../core/error/failures.dart';
import '../../../../core/usecases/usecase.dart';
import '../entities/profile_entity.dart';
import '../repositories/profile_repository.dart';

class UpdateProfileUseCase
    implements UseCase<ProfileEntity, UpdateProfileParams> {
  const UpdateProfileUseCase(this._repo);
  final ProfileRepository _repo;

  @override
  Future<Either<Failure, ProfileEntity>> call(UpdateProfileParams p) =>
      _repo.updateProfile(
        fullName: p.fullName,
        bio: p.bio,
        avatarUrl: p.avatarUrl,
      );
}

class UpdateProfileParams extends Equatable {
  const UpdateProfileParams({this.fullName, this.bio, this.avatarUrl});
  final String? fullName;
  final String? bio;
  final String? avatarUrl;

  @override
  List<Object?> get props => [fullName, bio, avatarUrl];
}
