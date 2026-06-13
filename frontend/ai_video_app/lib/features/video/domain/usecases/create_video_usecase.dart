import 'package:dartz/dartz.dart';
import 'package:equatable/equatable.dart';
import '../../../../core/error/failures.dart';
import '../../../../core/usecases/usecase.dart';
import '../entities/video_entity.dart';
import '../repositories/video_repository.dart';

class CreateVideoUseCase implements UseCase<VideoEntity, CreateVideoParams> {
  const CreateVideoUseCase(this._repo);
  final VideoRepository _repo;

  @override
  Future<Either<Failure, VideoEntity>> call(CreateVideoParams p) =>
      _repo.createVideo(
        projectId: p.projectId,
        title: p.title,
        description: p.description,
        scriptPrompt: p.scriptPrompt,
        voiceModel: p.voiceModel,
        language: p.language,
      );
}

class CreateVideoParams extends Equatable {
  const CreateVideoParams({
    required this.projectId,
    required this.title,
    this.description,
    this.scriptPrompt,
    this.voiceModel,
    this.language,
  });
  final String projectId;
  final String title;
  final String? description;
  final String? scriptPrompt;
  final String? voiceModel;
  final String? language;

  @override
  List<Object?> get props =>
      [projectId, title, description, scriptPrompt, voiceModel, language];
}
