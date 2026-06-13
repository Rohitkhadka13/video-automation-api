import 'package:dartz/dartz.dart';
import 'package:equatable/equatable.dart';
import '../../../../core/error/failures.dart';
import '../../../../core/usecases/usecase.dart';
import '../repositories/video_repository.dart';

class ProcessVideoUseCase
    implements UseCase<Map<String, dynamic>, ProcessVideoParams> {
  const ProcessVideoUseCase(this._repo);
  final VideoRepository _repo;

  @override
  Future<Either<Failure, Map<String, dynamic>>> call(ProcessVideoParams p) =>
      _repo.processVideo(videoId: p.videoId);
}

class ProcessVideoParams extends Equatable {
  const ProcessVideoParams({required this.videoId});
  final String videoId;

  @override
  List<Object> get props => [videoId];
}
