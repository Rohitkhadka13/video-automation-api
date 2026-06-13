import 'package:equatable/equatable.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../domain/entities/project_entity.dart';
import '../../domain/usecases/create_projects_usecase.dart';
import '../../domain/usecases/delete_projects_usecase.dart';
import '../../domain/usecases/get_projects_usecase.dart';
import '../../domain/usecases/update_projects_usecase.dart';

part 'project_event.dart';
part 'project_state.dart';

class ProjectBloc extends Bloc<ProjectEvent, ProjectState> {
  ProjectBloc({
    required this.getProjectsUseCase,
    required this.createProjectUseCase,
    required this.updateProjectUseCase,
    required this.deleteProjectUseCase,
  }) : super(const ProjectState()) {
    on<ProjectLoadEvent>(_onLoad);
    on<ProjectLoadMoreEvent>(_onLoadMore);
    on<ProjectCreateEvent>(_onCreate);
    on<ProjectUpdateEvent>(_onUpdate);
    on<ProjectDeleteEvent>(_onDelete);
  }

  final GetProjectsUseCase getProjectsUseCase;
  final CreateProjectUseCase createProjectUseCase;
  final UpdateProjectUseCase updateProjectUseCase;
  final DeleteProjectUseCase deleteProjectUseCase;

  static const int _pageSize = 20;

  Future<void> _onLoad(
      ProjectLoadEvent event, Emitter<ProjectState> emit) async {
    if (event.refresh) {
      emit(state.copyWith(
        status: ProjectStatus.loading,
        projects: [],
        currentPage: 0,
        hasMore: true,
        clearError: true,
      ));
    } else {
      emit(state.copyWith(status: ProjectStatus.loading, clearError: true));
    }

    final result = await getProjectsUseCase(
      const GetProjectsParams(skip: 0, limit: _pageSize),
    );

    result.fold(
      (failure) => emit(state.copyWith(
        status: ProjectStatus.failure,
        errorMessage: failure.message,
      )),
      (projects) => emit(state.copyWith(
        status: ProjectStatus.loaded,
        projects: projects,
        hasMore: projects.length >= _pageSize,
        currentPage: 1,
      )),
    );
  }

  Future<void> _onLoadMore(
    ProjectLoadMoreEvent event,
    Emitter<ProjectState> emit,
  ) async {
    if (!state.hasMore || state.isLoading) return;

    final result = await getProjectsUseCase(
      GetProjectsParams(skip: state.currentPage * _pageSize, limit: _pageSize),
    );

    result.fold(
      (failure) => emit(state.copyWith(
        status: ProjectStatus.failure,
        errorMessage: failure.message,
      )),
      (newProjects) => emit(state.copyWith(
        status: ProjectStatus.loaded,
        projects: [...state.projects, ...newProjects],
        hasMore: newProjects.length >= _pageSize,
        currentPage: state.currentPage + 1,
      )),
    );
  }

  Future<void> _onCreate(
    ProjectCreateEvent event,
    Emitter<ProjectState> emit,
  ) async {
    emit(state.copyWith(status: ProjectStatus.creating, clearError: true));

    final result = await createProjectUseCase(CreateProjectParams(
      name: event.name,
      description: event.description,
      defaultVoiceModel: event.defaultVoiceModel,
      defaultLanguage: event.defaultLanguage,
      defaultLlmModel: event.defaultLlmModel,
    ));

    result.fold(
      (failure) => emit(state.copyWith(
        status: ProjectStatus.failure,
        errorMessage: failure.message,
      )),
      (project) => emit(state.copyWith(
        status: ProjectStatus.success,
        projects: [project, ...state.projects],
        successMessage: 'Project "${project.name}" created successfully',
      )),
    );
  }

  Future<void> _onUpdate(
    ProjectUpdateEvent event,
    Emitter<ProjectState> emit,
  ) async {
    emit(state.copyWith(status: ProjectStatus.creating, clearError: true));

    final result = await updateProjectUseCase(UpdateProjectParams(
      id: event.id,
      name: event.name,
      description: event.description,
      defaultVoiceModel: event.defaultVoiceModel,
      defaultLanguage: event.defaultLanguage,
      defaultLlmModel: event.defaultLlmModel,
    ));

    result.fold(
      (failure) => emit(state.copyWith(
        status: ProjectStatus.failure,
        errorMessage: failure.message,
      )),
      (updated) => emit(state.copyWith(
        status: ProjectStatus.success,
        projects: state.projects
            .map((p) => p.id == updated.id ? updated : p)
            .toList(),
        successMessage: 'Project updated',
      )),
    );
  }

  Future<void> _onDelete(
    ProjectDeleteEvent event,
    Emitter<ProjectState> emit,
  ) async {
    final result =
        await deleteProjectUseCase(DeleteProjectParams(id: event.id));

    result.fold(
      (failure) => emit(state.copyWith(
        status: ProjectStatus.failure,
        errorMessage: failure.message,
      )),
      (_) => emit(state.copyWith(
        status: ProjectStatus.success,
        projects: state.projects.where((p) => p.id != event.id).toList(),
        successMessage: 'Project deleted',
      )),
    );
  }
}
