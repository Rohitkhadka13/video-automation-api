part of 'profile_bloc.dart';

abstract class ProfileEvent extends Equatable {
  const ProfileEvent();
  @override
  List<Object?> get props => [];
}

class ProfileLoadEvent extends ProfileEvent {
  const ProfileLoadEvent();
}

class ProfileUpdateEvent extends ProfileEvent {
  const ProfileUpdateEvent({this.fullName, this.bio, this.avatarUrl});
  final String? fullName;
  final String? bio;
  final String? avatarUrl;
  @override
  List<Object?> get props => [fullName, bio, avatarUrl];
}

class ProfileChangePasswordEvent extends ProfileEvent {
  const ProfileChangePasswordEvent({
    required this.currentPassword,
    required this.newPassword,
  });
  final String currentPassword;
  final String newPassword;
  @override
  List<Object> get props => [currentPassword, newPassword];
}
