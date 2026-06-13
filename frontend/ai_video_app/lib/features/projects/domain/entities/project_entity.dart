import 'package:equatable/equatable.dart';

class ProjectEntity extends Equatable {
  const ProjectEntity({
    required this.id,
    required this.name,
    required this.slug,
    required this.ownerId,
    required this.defaultVoiceModel,
    required this.defaultLanguage,
    required this.defaultLlmModel,
    required this.videoCount,
    required this.createdAt,
    required this.updatedAt,
    this.description,
  });

  final String id;
  final String name;
  final String slug;
  final String ownerId;
  final String defaultVoiceModel;
  final String defaultLanguage;
  final String defaultLlmModel;
  final int videoCount;
  final DateTime createdAt;
  final DateTime updatedAt;
  final String? description;

  bool get hasVideos => videoCount > 0;

  ProjectEntity copyWith({
    String? name,
    String? description,
    String? defaultVoiceModel,
    String? defaultLanguage,
    String? defaultLlmModel,
    int? videoCount,
  }) {
    return ProjectEntity(
      id: id,
      name: name ?? this.name,
      slug: slug,
      ownerId: ownerId,
      defaultVoiceModel: defaultVoiceModel ?? this.defaultVoiceModel,
      defaultLanguage: defaultLanguage ?? this.defaultLanguage,
      defaultLlmModel: defaultLlmModel ?? this.defaultLlmModel,
      videoCount: videoCount ?? this.videoCount,
      createdAt: createdAt,
      updatedAt: updatedAt,
      description: description ?? this.description,
    );
  }

  @override
  List<Object?> get props => [
        id,
        name,
        slug,
        ownerId,
        defaultVoiceModel,
        defaultLanguage,
        defaultLlmModel,
        videoCount,
        createdAt,
        updatedAt,
        description,
      ];
}
