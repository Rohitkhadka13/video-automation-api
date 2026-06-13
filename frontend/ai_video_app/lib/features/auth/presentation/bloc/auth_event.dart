part of 'auth_bloc.dart';

abstract class AuthEvent extends Equatable {
  const AuthEvent();
  @override
  List<Object?> get props => [];
}

/// Check if a valid token exists in secure storage (called on app start).
class AuthCheckStatusEvent extends AuthEvent {
  const AuthCheckStatusEvent();
}

/// User submitted the login form.
class AuthLoginEvent extends AuthEvent {
  const AuthLoginEvent({required this.email, required this.password});
  final String email;
  final String password;

  @override
  List<Object> get props => [email, password];
}

/// User submitted the registration form.
class AuthRegisterEvent extends AuthEvent {
  const AuthRegisterEvent({
    required this.email,
    required this.password,
    required this.fullName,
  });
  final String email;
  final String password;
  final String fullName;

  @override
  List<Object> get props => [email, password, fullName];
}

/// User tapped logout.
class AuthLogoutEvent extends AuthEvent {
  const AuthLogoutEvent();
}

/// User profile was updated externally — refresh local cache.
class AuthUserUpdatedEvent extends AuthEvent {
  const AuthUserUpdatedEvent({required this.user});
  final UserEntity user;

  @override
  List<Object> get props => [user];
}
