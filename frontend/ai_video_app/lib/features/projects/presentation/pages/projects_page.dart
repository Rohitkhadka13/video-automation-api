import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../../core/di/injection_container.dart';
import '../../../../core/widgets/app_snackbar.dart';
import '../../../../core/widgets/custom_button.dart';
import '../../../../core/widgets/custom_text_field.dart';
import '../../../../core/widgets/loading_widget.dart';
import '../../../../core/utils/validators.dart';
import '../bloc/project_bloc.dart';
import '../widgets/project_card.dart';

class ProjectsPage extends StatelessWidget {
  const ProjectsPage({super.key, this.openCreateDialog = false});
  final bool openCreateDialog;

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (_) => sl<ProjectBloc>()..add(const ProjectLoadEvent()),
      child: _ProjectsView(openCreateDialog: openCreateDialog),
    );
  }
}

class _ProjectsView extends StatefulWidget {
  const _ProjectsView({this.openCreateDialog = false});
  final bool openCreateDialog;

  @override
  State<_ProjectsView> createState() => _ProjectsViewState();
}

class _ProjectsViewState extends State<_ProjectsView> {
  final _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
    if (widget.openCreateDialog) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _showCreateDialog(context);
      });
    }
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (_scrollController.position.pixels >=
        _scrollController.position.maxScrollExtent - 200) {
      context.read<ProjectBloc>().add(const ProjectLoadMoreEvent());
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Projects'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_outlined),
            onPressed: () => context
                .read<ProjectBloc>()
                .add(const ProjectLoadEvent(refresh: true)),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _showCreateDialog(context),
        icon: const Icon(Icons.add),
        label: const Text('New Project'),
      ),
      body: BlocConsumer<ProjectBloc, ProjectState>(
        listenWhen: (prev, curr) =>
            prev.errorMessage != curr.errorMessage ||
            prev.successMessage != curr.successMessage,
        listener: (context, state) {
          if (state.errorMessage != null) {
            AppSnackbar.error(context, state.errorMessage!);
          }
          if (state.successMessage != null) {
            AppSnackbar.success(context, state.successMessage!);
          }
        },
        builder: (context, state) {
          if (state.status == ProjectStatus.loading && state.projects.isEmpty) {
            return const ShimmerList(count: 5, cardHeight: 140);
          }
          if (state.isEmpty) {
            return _EmptyState(
              onCreateTap: () => _showCreateDialog(context),
            );
          }
          return RefreshIndicator(
            onRefresh: () async => context
                .read<ProjectBloc>()
                .add(const ProjectLoadEvent(refresh: true)),
            child: ListView.builder(
              controller: _scrollController,
              padding: const EdgeInsets.only(bottom: 100),
              itemCount: state.projects.length + (state.hasMore ? 1 : 0),
              itemBuilder: (_, index) {
                if (index == state.projects.length) {
                  return const Padding(
                    padding: EdgeInsets.all(16),
                    child: Center(child: CircularProgressIndicator()),
                  );
                }
                final project = state.projects[index];
                return ProjectCard(
                  project: project,
                  onDelete: () =>
                      _confirmDelete(context, project.id, project.name),
                );
              },
            ),
          );
        },
      ),
    );
  }

  void _showCreateDialog(BuildContext context) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Theme.of(context).colorScheme.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (_) => BlocProvider.value(
        value: context.read<ProjectBloc>(),
        child: const _CreateProjectSheet(),
      ),
    );
  }

  void _confirmDelete(BuildContext ctx, String id, String name) {
    showDialog<void>(
      context: ctx,
      builder: (_) => AlertDialog(
        title: const Text('Delete project?'),
        content: Text(
          'This will permanently delete "$name" and all its videos.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(_).pop(),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              Navigator.of(_).pop();
              ctx.read<ProjectBloc>().add(ProjectDeleteEvent(id: id));
            },
            child: const Text('Delete', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
  }
}

class _CreateProjectSheet extends StatefulWidget {
  const _CreateProjectSheet();

  @override
  State<_CreateProjectSheet> createState() => _CreateProjectSheetState();
}

class _CreateProjectSheetState extends State<_CreateProjectSheet> {
  final _formKey = GlobalKey<FormState>();
  final _nameCtrl = TextEditingController();
  final _descCtrl = TextEditingController();

  @override
  void dispose() {
    _nameCtrl.dispose();
    _descCtrl.dispose();
    super.dispose();
  }

  void _submit() {
    if (!_formKey.currentState!.validate()) return;
    context.read<ProjectBloc>().add(ProjectCreateEvent(
          name: _nameCtrl.text.trim(),
          description:
              _descCtrl.text.trim().isEmpty ? null : _descCtrl.text.trim(),
        ));
    Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.fromLTRB(
        24,
        16,
        24,
        MediaQuery.of(context).viewInsets.bottom + 24,
      ),
      child: Form(
        key: _formKey,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Center(
              child: Container(
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: Theme.of(context).dividerColor,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            const SizedBox(height: 20),
            Text('New Project', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 24),
            AppTextField(
              label: 'Project name',
              hint: 'My awesome project',
              controller: _nameCtrl,
              prefixIcon: Icons.folder_outlined,
              validator: Validators.projectName,
              autofocus: true,
            ),
            const SizedBox(height: 16),
            AppTextField(
              label: 'Description (optional)',
              hint: 'What is this project about?',
              controller: _descCtrl,
              prefixIcon: Icons.notes,
              maxLines: 3,
            ),
            const SizedBox(height: 24),
            BlocBuilder<ProjectBloc, ProjectState>(
              builder: (context, state) => AppButton(
                label: 'Create Project',
                onPressed: _submit,
                isLoading: state.isCreating,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.onCreateTap});
  final VoidCallback onCreateTap;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.video_library_outlined,
                size: 80,
                color: Theme.of(context).colorScheme.onSurfaceVariant),
            const SizedBox(height: 16),
            Text('No projects yet',
                style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            Text(
              'Create your first project to start generating AI videos.',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
            ),
            const SizedBox(height: 24),
            AppButton(
              label: 'Create Project',
              onPressed: onCreateTap,
              width: 200,
            ),
          ],
        ),
      ),
    );
  }
}
