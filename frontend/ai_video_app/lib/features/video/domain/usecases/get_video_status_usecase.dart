import 'package:dartz/dartz.dart';
import 'package:equatable/equatable.dart';
import '../../../../core/error/failures.dart';
import '../../../../core/usecases/usecase.dart';
import '../entities/video_entity.dart';
import '../repositories/video_repository.dart';

class GetVideoStatusUseCase
    implements UseCase<VideoEntity, GetVideoStatusParams> {
  const GetVideoStatusUseCase(this._repo);
  final VideoRepository _repo;

  @override
  Future<Either<Failure, VideoEntity>> call(GetVideoStatusParams p) =>
      _repo.getVideoStatus(videoId: p.videoId);
}

class GetVideoStatusParams extends Equatable {
  const GetVideoStatusParams({required this.videoId});
  final String videoId;

  @override
  List<Object> get props => [videoId];
}
