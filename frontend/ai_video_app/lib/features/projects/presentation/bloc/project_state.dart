part of 'project_bloc.dart';

enum ProjectStatus { initial, loading, loaded, creating, success, failure }

class ProjectState extends Equatable {
  const ProjectState({
    this.status = ProjectStatus.initial,
    this.projects = const [],
    this.errorMessage,
    this.hasMore = true,
    this.currentPage = 0,
    this.successMessage,
  });

  final ProjectStatus status;
  final List<ProjectEntity> projects;
  final String? errorMessage;
  final bool hasMore;
  final int currentPage;
  final String? successMessage;

  bool get isLoading => status == ProjectStatus.loading;
  bool get isCreating => status == ProjectStatus.creating;
  bool get isEmpty => projects.isEmpty && status == ProjectStatus.loaded;

  ProjectState copyWith({
    ProjectStatus? status,
    List<ProjectEntity>? projects,
    String? errorMessage,
    bool? hasMore,
    int? currentPage,
    String? successMessage,
    bool clearError = false,
    bool clearSuccess = false,
  }) {
    return ProjectState(
      status: status ?? this.status,
      projects: projects ?? this.projects,
      errorMessage: clearError ? null : (errorMessage ?? this.errorMessage),
      hasMore: hasMore ?? this.hasMore,
      currentPage: currentPage ?? this.currentPage,
      successMessage:
          clearSuccess ? null : (successMessage ?? this.successMessage),
    );
  }

  @override
  List<Object?> get props =>
      [status, projects, errorMessage, hasMore, currentPage, successMessage];
}
