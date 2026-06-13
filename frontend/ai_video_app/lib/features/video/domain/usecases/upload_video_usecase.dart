import 'package:dartz/dartz.dart';
import 'package:equatable/equatable.dart';
import '../../../../core/error/failures.dart';
import '../../../../core/usecases/usecase.dart';
import '../entities/video_entity.dart';
import '../repositories/video_repository.dart';

class UploadVideoUseCase implements UseCase<VideoEntity, UploadVideoParams> {
  const UploadVideoUseCase(this._repo);
  final VideoRepository _repo;

  @override
  Future<Either<Failure, VideoEntity>> call(UploadVideoParams p) =>
      _repo.uploadVideo(
        videoId: p.videoId,
        filePath: p.filePath,
        mimeType: p.mimeType,
        onProgress: p.onProgress,
      );
}

class UploadVideoParams extends Equatable {
  const UploadVideoParams({
    required this.videoId,
    required this.filePath,
    required this.mimeType,
    this.onProgress,
  });
  final String videoId;
  final String filePath;
  final String mimeType;
  final void Function(int sent, int total)? onProgress;

  @override
  List<Object?> get props => [videoId, filePath, mimeType];
}
