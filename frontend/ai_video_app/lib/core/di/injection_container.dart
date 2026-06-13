import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:get_it/get_it.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../network/api_client.dart';
import '../network/network_info.dart';

// ── Features
import '../../features/auth/data/datasources/auth_local_data_source.dart';
import '../../features/auth/data/datasources/auth_remote_data_source.dart';
import '../../features/auth/data/repositories/auth_repository_impl.dart';
import '../../features/auth/domain/repositories/auth_repository.dart';
import '../../features/auth/domain/usecases/login_usecase.dart';
import '../../features/auth/domain/usecases/register_usecase.dart';
import '../../features/auth/domain/usecases/logout_usecase.dart';
import '../../features/auth/domain/usecases/refresh_token_usecase.dart';
import '../../features/auth/presentation/bloc/auth_bloc.dart';

import '../../features/projects/data/datasources/project_remote_data_source.dart';
import '../../features/projects/data/repositories/project_repository_impl.dart';
import '../../features/projects/domain/repositories/project_repository.dart';
import '../../features/projects/domain/usecases/get_projects_usecase.dart';
import '../../features/projects/domain/usecases/create_projects_usecase.dart';
import '../../features/projects/domain/usecases/update_projects_usecase.dart';
import '../../features/projects/domain/usecases/delete_projects_usecase.dart';
import '../../features/projects/presentation/bloc/project_bloc.dart';

import '../../features/video/data/datasources/video_remote_data_source.dart';
import '../../features/video/data/repositories/video_repository_impl.dart';
import '../../features/video/domain/repositories/video_repository.dart';
import '../../features/video/domain/usecases/create_video_usecase.dart';
import '../../features/video/domain/usecases/upload_video_usecase.dart';
import '../../features/video/domain/usecases/process_video_usecase.dart';
import '../../features/video/domain/usecases/get_video_status_usecase.dart';
import '../../features/video/domain/usecases/get_videos_usecase.dart';
import '../../features/video/presentation/bloc/video_bloc.dart';

import '../../features/profile/data/datasources/profile_remote_data_source.dart';
import '../../features/profile/data/repositories/profile_repository_impl.dart';
import '../../features/profile/domain/repositories/profile_repository.dart';
import '../../features/profile/domain/usecases/get_profile_usecase.dart';
import '../../features/profile/domain/usecases/update_profile_usecase.dart';
import '../../features/profile/presentation/bloc/profile_bloc.dart';

/// Global service locator instance.
final GetIt sl = GetIt.instance;

/// Registers all dependencies. Called once in [main] before [runApp].
Future<void> init() async {
  // ── External dependencies ──────────────────────────────────────────────────
  final sharedPreferences = await SharedPreferences.getInstance();
  sl.registerSingleton<SharedPreferences>(sharedPreferences);

  const secureStorage = FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
    iOptions: IOSOptions(
      accessibility: KeychainAccessibility.first_unlock_this_device,
    ),
  );
  sl.registerSingleton<FlutterSecureStorage>(secureStorage);

  sl.registerSingleton<Connectivity>(Connectivity());

  // ── Core — Network ─────────────────────────────────────────────────────────
  sl.registerSingleton<Dio>(
    createDio(secureStorage: sl<FlutterSecureStorage>()),
  );

  sl.registerSingleton<NetworkInfo>(
    NetworkInfoImpl(connectivity: sl<Connectivity>()),
  );

  // ══════════════════════════════════════════════════════════════════════════
  // FEATURE: AUTH
  // ══════════════════════════════════════════════════════════════════════════

  // Data sources
  sl.registerLazySingleton<AuthRemoteDataSource>(
    () => AuthRemoteDataSourceImpl(dio: sl<Dio>()),
  );
  sl.registerLazySingleton<AuthLocalDataSource>(
    () => AuthLocalDataSourceImpl(secureStorage: sl<FlutterSecureStorage>()),
  );

  // Repository
  sl.registerLazySingleton<AuthRepository>(
    () => AuthRepositoryImpl(
      remoteDataSource: sl<AuthRemoteDataSource>(),
      localDataSource: sl<AuthLocalDataSource>(),
      networkInfo: sl<NetworkInfo>(),
    ),
  );

  // Use cases
  sl.registerLazySingleton(() => LoginUseCase(sl<AuthRepository>()));
  sl.registerLazySingleton(() => RegisterUseCase(sl<AuthRepository>()));
  sl.registerLazySingleton(() => LogoutUseCase(sl<AuthRepository>()));
  sl.registerLazySingleton(() => RefreshTokenUseCase(sl<AuthRepository>()));

  // BLoC — factory so a new instance is created for each widget tree insertion
  sl.registerFactory(
    () => AuthBloc(
      loginUseCase: sl<LoginUseCase>(),
      registerUseCase: sl<RegisterUseCase>(),
      logoutUseCase: sl<LogoutUseCase>(),
      refreshTokenUseCase: sl<RefreshTokenUseCase>(),
      localDataSource: sl<AuthLocalDataSource>(),
    ),
  );

  // ══════════════════════════════════════════════════════════════════════════
  // FEATURE: PROJECTS
  // ══════════════════════════════════════════════════════════════════════════

  sl.registerLazySingleton<ProjectRemoteDataSource>(
    () => ProjectRemoteDataSourceImpl(dio: sl<Dio>()),
  );
  sl.registerLazySingleton<ProjectRepository>(
    () => ProjectRepositoryImpl(
      remoteDataSource: sl<ProjectRemoteDataSource>(),
      networkInfo: sl<NetworkInfo>(),
    ),
  );

  sl.registerLazySingleton(() => GetProjectsUseCase(sl<ProjectRepository>()));
  sl.registerLazySingleton(() => CreateProjectUseCase(sl<ProjectRepository>()));
  sl.registerLazySingleton(() => UpdateProjectUseCase(sl<ProjectRepository>()));
  sl.registerLazySingleton(() => DeleteProjectUseCase(sl<ProjectRepository>()));

  sl.registerFactory(
    () => ProjectBloc(
      getProjectsUseCase: sl<GetProjectsUseCase>(),
      createProjectUseCase: sl<CreateProjectUseCase>(),
      updateProjectUseCase: sl<UpdateProjectUseCase>(),
      deleteProjectUseCase: sl<DeleteProjectUseCase>(),
    ),
  );

  // ══════════════════════════════════════════════════════════════════════════
  // FEATURE: VIDEO
  // ══════════════════════════════════════════════════════════════════════════

  sl.registerLazySingleton<VideoRemoteDataSource>(
    () => VideoRemoteDataSourceImpl(dio: sl<Dio>()),
  );
  sl.registerLazySingleton<VideoRepository>(
    () => VideoRepositoryImpl(
      remoteDataSource: sl<VideoRemoteDataSource>(),
      networkInfo: sl<NetworkInfo>(),
    ),
  );

  sl.registerLazySingleton(() => GetVideosUseCase(sl<VideoRepository>()));
  sl.registerLazySingleton(() => CreateVideoUseCase(sl<VideoRepository>()));
  sl.registerLazySingleton(() => UploadVideoUseCase(sl<VideoRepository>()));
  sl.registerLazySingleton(() => ProcessVideoUseCase(sl<VideoRepository>()));
  sl.registerLazySingleton(() => GetVideoStatusUseCase(sl<VideoRepository>()));

  sl.registerFactory(
    () => VideoBloc(
      getVideosUseCase: sl<GetVideosUseCase>(),
      createVideoUseCase: sl<CreateVideoUseCase>(),
      uploadVideoUseCase: sl<UploadVideoUseCase>(),
      processVideoUseCase: sl<ProcessVideoUseCase>(),
      getVideoStatusUseCase: sl<GetVideoStatusUseCase>(),
    ),
  );

  // ══════════════════════════════════════════════════════════════════════════
  // FEATURE: PROFILE
  // ══════════════════════════════════════════════════════════════════════════

  sl.registerLazySingleton<ProfileRemoteDataSource>(
    () => ProfileRemoteDataSourceImpl(dio: sl<Dio>()),
  );
  sl.registerLazySingleton<ProfileRepository>(
    () => ProfileRepositoryImpl(
      remoteDataSource: sl<ProfileRemoteDataSource>(),
      networkInfo: sl<NetworkInfo>(),
    ),
  );

  sl.registerLazySingleton(() => GetProfileUseCase(sl<ProfileRepository>()));
  sl.registerLazySingleton(() => UpdateProfileUseCase(sl<ProfileRepository>()));

  sl.registerFactory(
    () => ProfileBloc(
      getProfileUseCase: sl<GetProfileUseCase>(),
      updateProfileUseCase: sl<UpdateProfileUseCase>(),
    ),
  );
}
