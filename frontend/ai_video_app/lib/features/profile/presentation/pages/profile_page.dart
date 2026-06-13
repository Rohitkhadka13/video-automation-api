import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../../core/di/injection_container.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_text_styles.dart';
import '../../../../core/utils/extensions.dart';
import '../../../../core/utils/validators.dart';
import '../../../../core/widgets/app_snackbar.dart';
import '../../../../core/widgets/custom_button.dart';
import '../../../../core/widgets/custom_text_field.dart';
import '../../../../core/widgets/loading_widget.dart';
import '../../../auth/presentation/bloc/auth_bloc.dart';
import '../bloc/profile_bloc.dart';

class ProfilePage extends StatelessWidget {
  const ProfilePage({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (_) => sl<ProfileBloc>()..add(const ProfileLoadEvent()),
      child: const _ProfileView(),
    );
  }
}

class _ProfileView extends StatelessWidget {
  const _ProfileView();

  @override
  Widget build(BuildContext context) {
    return BlocConsumer<ProfileBloc, ProfileState>(
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
        if (state.isLoading) {
          return const Scaffold(body: LoadingWidget());
        }

        final profile = state.profile;

        return Scaffold(
          appBar: AppBar(
            title: const Text('Profile'),
            actions: [
              IconButton(
                icon: const Icon(Icons.refresh_outlined),
                onPressed: () =>
                    context.read<ProfileBloc>().add(const ProfileLoadEvent()),
              ),
            ],
          ),
          body: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              // Avatar card
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    children: [
                      // Avatar
                      profile?.avatarUrl != null
                          ? CircleAvatar(
                              radius: 40,
                              backgroundImage:
                                  NetworkImage(profile!.avatarUrl!),
                            )
                          : CircleAvatar(
                              radius: 40,
                              backgroundColor:
                                  AppColors.primary.withValues(alpha: 0.15),
                              child: Text(
                                profile?.initials ?? '?',
                                style: AppTextStyles.headlineSmall.copyWith(
                                  color: AppColors.primary,
                                ),
                              ),
                            ),
                      const SizedBox(height: 12),
                      Text(
                        profile?.fullName ?? '—',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 4),
                      Text(
                        profile?.email ?? '—',
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                              color: Theme.of(context)
                                  .colorScheme
                                  .onSurfaceVariant,
                            ),
                      ),
                      const SizedBox(height: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 12, vertical: 4),
                        decoration: BoxDecoration(
                          color: AppColors.primary.withValues(alpha: 0.1),
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: Text(
                          (profile?.role ?? 'user').toUpperCase(),
                          style: AppTextStyles.labelSmall.copyWith(
                            color: AppColors.primary,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),

              // Bio card
              if (profile?.bio != null && profile!.bio!.isNotEmpty)
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Bio',
                            style: Theme.of(context).textTheme.titleSmall),
                        const SizedBox(height: 8),
                        Text(profile.bio!,
                            style: Theme.of(context).textTheme.bodyMedium),
                      ],
                    ),
                  ),
                ),
              if (profile?.bio != null && profile!.bio!.isNotEmpty)
                const SizedBox(height: 16),

              // Account info
              Card(
                child: Column(
                  children: [
                    _InfoTile(
                      icon: Icons.verified_outlined,
                      label: 'Email verified',
                      value: profile?.isVerified == true ? 'Yes' : 'No',
                      valueColor: profile?.isVerified == true
                          ? AppColors.success
                          : AppColors.warning,
                    ),
                    _InfoTile(
                      icon: Icons.calendar_today_outlined,
                      label: 'Member since',
                      value: profile?.createdAt.formattedDate ?? '—',
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),

              // Edit profile button
              AppButton(
                label: 'Edit Profile',
                variant: ButtonVariant.outlined,
                prefixIcon: Icons.edit_outlined,
                onPressed: () => _showEditSheet(context, state),
              ),
              const SizedBox(height: 12),

              AppButton(
                label: 'Change Password',
                variant: ButtonVariant.outlined,
                prefixIcon: Icons.lock_reset_outlined,
                onPressed: () => _showPasswordSheet(context),
              ),
              const SizedBox(height: 12),

              // Logout
              AppButton(
                label: 'Sign Out',
                variant: ButtonVariant.danger,
                prefixIcon: Icons.logout_rounded,
                onPressed: () => _confirmLogout(context),
              ),
            ],
          ),
        );
      },
    );
  }

  void _showEditSheet(BuildContext context, ProfileState state) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Theme.of(context).colorScheme.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (_) => BlocProvider.value(
        value: context.read<ProfileBloc>(),
        child: _EditProfileSheet(profile: state.profile),
      ),
    );
  }

  void _showPasswordSheet(BuildContext context) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Theme.of(context).colorScheme.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (_) => BlocProvider.value(
        value: context.read<ProfileBloc>(),
        child: const _ChangePasswordSheet(),
      ),
    );
  }

  void _confirmLogout(BuildContext context) {
    showDialog<void>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Sign out?'),
        content: const Text('You will be signed out of your account.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(_).pop(),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              Navigator.of(_).pop();
              context.read<AuthBloc>().add(const AuthLogoutEvent());
            },
            child: const Text('Sign Out',
                style: TextStyle(color: AppColors.error)),
          ),
        ],
      ),
    );
  }
}

// =============================================================================
// Edit Profile Bottom Sheet
// =============================================================================

class _EditProfileSheet extends StatefulWidget {
  const _EditProfileSheet({this.profile});
  final dynamic profile;

  @override
  State<_EditProfileSheet> createState() => _EditProfileSheetState();
}

class _EditProfileSheetState extends State<_EditProfileSheet> {
  final _formKey = GlobalKey<FormState>();
  late final _nameCtrl = TextEditingController(
    text: widget.profile?.fullName ?? '',
  );
  late final _bioCtrl = TextEditingController(
    text: widget.profile?.bio ?? '',
  );

  @override
  void dispose() {
    _nameCtrl.dispose();
    _bioCtrl.dispose();
    super.dispose();
  }

  void _submit() {
    if (!_formKey.currentState!.validate()) return;
    context.read<ProfileBloc>().add(ProfileUpdateEvent(
          fullName: _nameCtrl.text.trim(),
          bio: _bioCtrl.text.trim().isEmpty ? null : _bioCtrl.text.trim(),
        ));
    Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.fromLTRB(
          24, 16, 24, MediaQuery.of(context).viewInsets.bottom + 24),
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
            Text('Edit Profile', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 24),
            AppTextField(
              label: 'Full name',
              controller: _nameCtrl,
              prefixIcon: Icons.person_outline,
              validator: Validators.fullName,
              autofocus: true,
            ),
            const SizedBox(height: 16),
            AppTextField(
              label: 'Bio (optional)',
              hint: 'Tell us about yourself',
              controller: _bioCtrl,
              prefixIcon: Icons.notes,
              maxLines: 4,
              maxLength: 1000,
            ),
            const SizedBox(height: 24),
            BlocBuilder<ProfileBloc, ProfileState>(
              builder: (context, state) => AppButton(
                label: 'Save Changes',
                onPressed: _submit,
                isLoading: state.isUpdating,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// =============================================================================
// Change Password Bottom Sheet
// =============================================================================

class _ChangePasswordSheet extends StatefulWidget {
  const _ChangePasswordSheet();

  @override
  State<_ChangePasswordSheet> createState() => _ChangePasswordSheetState();
}

class _ChangePasswordSheetState extends State<_ChangePasswordSheet> {
  final _formKey = GlobalKey<FormState>();
  final _currentCtrl = TextEditingController();
  final _newCtrl = TextEditingController();
  final _confirmCtrl = TextEditingController();

  @override
  void dispose() {
    _currentCtrl.dispose();
    _newCtrl.dispose();
    _confirmCtrl.dispose();
    super.dispose();
  }

  void _submit() {
    if (!_formKey.currentState!.validate()) return;
    context.read<ProfileBloc>().add(ProfileChangePasswordEvent(
          currentPassword: _currentCtrl.text,
          newPassword: _newCtrl.text,
        ));
    Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.fromLTRB(
          24, 16, 24, MediaQuery.of(context).viewInsets.bottom + 24),
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
            Text('Change Password',
                style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 24),
            AppTextField(
              label: 'Current password',
              controller: _currentCtrl,
              prefixIcon: Icons.lock_outline,
              isPassword: true,
              validator: (v) => v == null || v.isEmpty ? 'Required' : null,
              textInputAction: TextInputAction.next,
            ),
            const SizedBox(height: 16),
            AppTextField(
              label: 'New password',
              controller: _newCtrl,
              prefixIcon: Icons.lock_reset_outlined,
              isPassword: true,
              validator: Validators.password,
              textInputAction: TextInputAction.next,
            ),
            const SizedBox(height: 16),
            AppTextField(
              label: 'Confirm new password',
              controller: _confirmCtrl,
              prefixIcon: Icons.lock_outline,
              isPassword: true,
              validator: Validators.confirmPassword(_newCtrl.text),
              textInputAction: TextInputAction.done,
              onSubmitted: (_) => _submit(),
            ),
            const SizedBox(height: 24),
            BlocBuilder<ProfileBloc, ProfileState>(
              builder: (context, state) => AppButton(
                label: 'Update Password',
                onPressed: _submit,
                isLoading: state.isUpdating,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// =============================================================================
// Helper widget
// =============================================================================

class _InfoTile extends StatelessWidget {
  const _InfoTile({
    required this.icon,
    required this.label,
    required this.value,
    this.valueColor,
  });

  final IconData icon;
  final String label;
  final String value;
  final Color? valueColor;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Icon(icon, color: AppColors.primary, size: 20),
      title: Text(label, style: Theme.of(context).textTheme.bodyMedium),
      trailing: Text(
        value,
        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              fontWeight: FontWeight.w600,
              color: valueColor,
            ),
      ),
    );
  }
}
