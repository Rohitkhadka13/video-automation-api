import 'package:equatable/equatable.dart';

class ProfileEntity extends Equatable {
  const ProfileEntity({
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

  String get initials {
    final parts = fullName.trim().split(' ');
    if (parts.length >= 2) {
      return '${parts.first[0]}${parts.last[0]}'.toUpperCase();
    }
    return fullName.isNotEmpty
        ? fullName[0].toUpperCase()
        : email[0].toUpperCase();
  }

  ProfileEntity copyWith({
    String? fullName,
    String? avatarUrl,
    String? bio,
  }) =>
      ProfileEntity(
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
