import 'package:equatable/equatable.dart';

/// Domain entity representing an authenticated user.
/// Immutable, no serialization logic — pure domain object.
class UserEntity extends Equatable {
  const UserEntity({
    required this.id,
    required this.email,
    required this.fullName,
    required this.role,
    required this.isActive,
    required this.isVerified,
    required this.createdAt,
    required this.updatedAt,
    this.avatarUrl,
    this.bio,
  });

  final String id;
  final String email;
  final String fullName;
  final String role;
  final bool isActive;
  final bool isVerified;
  final DateTime createdAt;
  final DateTime updatedAt;
  final String? avatarUrl;
  final String? bio;

  bool get isAdmin => role == 'admin';

  String get displayName {
    final parts = fullName.trim().split(' ');
    return parts.isNotEmpty ? parts.first : email.split('@').first;
  }

  String get initials {
    final parts = fullName.trim().split(' ');
    if (parts.length >= 2) {
      return '${parts.first[0]}${parts.last[0]}'.toUpperCase();
    }
    return fullName.isNotEmpty
        ? fullName[0].toUpperCase()
        : email[0].toUpperCase();
  }

  UserEntity copyWith({
    String? fullName,
    String? avatarUrl,
    String? bio,
  }) {
    return UserEntity(
      id: id,
      email: email,
      fullName: fullName ?? this.fullName,
      role: role,
      isActive: isActive,
      isVerified: isVerified,
      createdAt: createdAt,
      updatedAt: updatedAt,
      avatarUrl: avatarUrl ?? this.avatarUrl,
      bio: bio ?? this.bio,
    );
  }

  @override
  List<Object?> get props => [
        id,
        email,
        fullName,
        role,
        isActive,
        isVerified,
        createdAt,
        updatedAt,
        avatarUrl,
        bio,
      ];
}
