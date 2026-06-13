part of 'project_bloc.dart';

abstract class ProjectEvent extends Equatable {
  const ProjectEvent();
  @override
  List<Object?> get props => [];
}

class ProjectLoadEvent extends ProjectEvent {
  const ProjectLoadEvent({this.refresh = false});
  final bool refresh;
  @override
  List<Object> get props => [refresh];
}

class ProjectLoadMoreEvent extends ProjectEvent {
  const ProjectLoadMoreEvent();
}

class ProjectCreateEvent extends ProjectEvent {
  const ProjectCreateEvent({
    required this.name,
    this.description,
    this.defaultVoiceModel = 'en_US-lessac-medium',
    this.defaultLanguage = 'en',
    this.defaultLlmModel = 'llama3',
  });
  final String name;
  final String? description;
  final String defaultVoiceModel;
  final String defaultLanguage;
  final String defaultLlmModel;

  @override
  List<Object?> get props =>
      [name, description, defaultVoiceModel, defaultLanguage, defaultLlmModel];
}

class ProjectUpdateEvent extends ProjectEvent {
  const ProjectUpdateEvent({
    required this.id,
    this.name,
    this.description,
    this.defaultVoiceModel,
    this.defaultLanguage,
    this.defaultLlmModel,
  });
  final String id;
  final String? name;
  final String? description;
  final String? defaultVoiceModel;
  final String? defaultLanguage;
  final String? defaultLlmModel;

  @override
  List<Object?> get props => [
        id,
        name,
        description,
        defaultVoiceModel,
        defaultLanguage,
        defaultLlmModel
      ];
}

class ProjectDeleteEvent extends ProjectEvent {
  const ProjectDeleteEvent({required this.id});
  final String id;
  @override
  List<Object> get props => [id];
}
