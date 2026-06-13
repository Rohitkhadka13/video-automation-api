import 'package:dartz/dartz.dart';
import 'package:equatable/equatable.dart';
import '../../../../core/error/failures.dart';
import '../../../../core/usecases/usecase.dart';
import '../entities/video_entity.dart';
import '../repositories/video_repository.dart';

class GetVideosUseCase implements UseCase<List<VideoEntity>, GetVideosParams> {
  const GetVideosUseCase(this._repo);
  final VideoRepository _repo;

  @override
  Future<Either<Failure, List<VideoEntity>>> call(GetVideosParams p) =>
      _repo.getVideos(
        projectId: p.projectId,
        skip: p.skip,
        limit: p.limit,
        statusFilter: p.statusFilter,
      );
}

class GetVideosParams extends Equatable {
  const GetVideosParams({
    required this.projectId,
    this.skip = 0,
    this.limit = 20,
    this.statusFilter,
  });
  final String projectId;
  final int skip;
  final int limit;
  final List<String>? statusFilter;

  @override
  List<Object?> get props => [projectId, skip, limit, statusFilter];
}
