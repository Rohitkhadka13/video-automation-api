# AI Video SaaS — Flutter Frontend

Production-ready Flutter application for the AI Video Automation SaaS platform.

## Tech Stack

| Package | Purpose |
|---|---|
| `flutter_bloc` | State management |
| `go_router` | Declarative navigation with auth guards |
| `get_it` | Dependency injection (service locator) |
| `dio` | HTTP client with JWT interceptors |
| `dartz` | Functional programming (`Either<Failure, T>`) |
| `flutter_secure_storage` | JWT token storage (Keychain / Keystore) |
| `json_annotation` | JSON serialization |
| `file_picker` | Cross-platform video file selection |
| `cached_network_image` | Thumbnail caching |
| `shimmer` | Skeleton loading states |
| `percent_indicator` | Upload / processing progress bars |
| `connectivity_plus` | Offline detection |

---

## Architecture

Feature-first Clean Architecture with 3 strict layers per feature:

```
lib/
├── main.dart                        # Entry point — DI init, BLoC observer
├── app.dart                         # Root widget — router, theme, global BLoCs
│
├── core/                            # Shared across all features
│   ├── constants/                   # API endpoints, app constants, storage keys
│   ├── di/injection_container.dart  # GetIt registrations
│   ├── error/                       # Failures (domain) + Exceptions (data)
│   ├── network/                     # Dio client + interceptors + NetworkInfo
│   ├── router/                      # GoRouter config + route names
│   ├── theme/                       # Colors, text styles, MaterialApp theme
│   ├── usecases/                    # UseCase / NoParamsUseCase base contracts
│   ├── utils/                       # Extensions, validators, BLoC observer
│   └── widgets/                     # AppButton, AppTextField, LoadingWidget, AppSnackbar
│
└── features/
    ├── auth/                        # Login, register, JWT refresh, logout
    ├── projects/                    # Project CRUD
    ├── video/                       # Upload → AI process → poll → complete
    └── profile/                     # View/edit profile, change password
```

Each feature follows the same internal structure:

```
feature/
├── domain/           # Pure Dart — no Flutter, no Dio
│   ├── entities/     # Immutable Equatable value objects
│   ├── repositories/ # Abstract interfaces (contracts)
│   └── usecases/     # Single-responsibility use cases returning Either<Failure, T>
├── data/             # Framework-aware — Dio, json_serializable
│   ├── models/       # JSON models extending domain entities (.dart + .g.dart)
│   ├── datasources/  # Remote (Dio) + Local (SecureStorage) data sources
│   └── repositories/ # Implements domain interfaces, catches exceptions → failures
└── presentation/     # Flutter widgets
    ├── bloc/         # Event + State + Bloc (part files)
    ├── pages/        # Full screens (one per route)
    └── widgets/      # Reusable feature-scoped widgets
```

---

## Setup

### 1 — Prerequisites

```bash
flutter --version   # 3.22.0+
dart --version      # 3.3.0+
```

### 2 — Install dependencies

```bash
flutter pub get
```

### 3 — Configure API URL

Edit `lib/core/constants/api_constants.dart`:

```dart
// Local Docker backend
static const String baseUrlDev = 'http://localhost:8000/api/v1';

// Real device on same WiFi
static const String baseUrlDev = 'http://192.168.1.x:8000/api/v1';
```

### 4 — Add Inter fonts

Download from https://fonts.google.com/specimen/Inter and place in `assets/fonts/`:

```
assets/fonts/Inter-Regular.ttf
assets/fonts/Inter-Medium.ttf
assets/fonts/Inter-SemiBold.ttf
assets/fonts/Inter-Bold.ttf
```

### 5 — Run

```bash
flutter run                    # default device
flutter run -d "iPhone 15"    # iOS simulator
flutter run -d chrome          # web
flutter run --release          # production build
```

---

## Platform Permissions

### iOS — `ios/Runner/Info.plist`

```xml
<key>NSPhotoLibraryUsageDescription</key>
<string>Select videos from your library</string>
<key>NSCameraUsageDescription</key>
<string>Record videos</string>
<key>NSMicrophoneUsageDescription</key>
<string>Record audio</string>
```

### Android — `android/app/src/main/AndroidManifest.xml`

```xml
<uses-permission android:name="android.permission.INTERNET"/>
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE"/>
<uses-permission android:name="android.permission.READ_MEDIA_VIDEO"/>
```

---

## Key Patterns

### Error handling — `Either<Failure, T>`

```dart
// Use case returns Either
final result = await loginUseCase(LoginParams(email: email, password: password));

result.fold(
  (failure) => emit(state.copyWith(errorMessage: failure.message)),
  (user)    => emit(state.copyWith(status: AuthStatus.authenticated, user: user)),
);
```

### BLoC — event dispatch

```dart
// From any widget with BLoC access:
context.read<ProjectBloc>().add(const ProjectLoadEvent());
context.read<VideoBloc>().add(VideoProcessEvent(videoId: video.id));
```

### Dependency injection — GetIt

```dart
// Register (injection_container.dart)
sl.registerFactory(() => AuthBloc(loginUseCase: sl(), ...));

// Resolve (in widget)
BlocProvider(create: (_) => sl<AuthBloc>())
```

### Navigation — GoRouter

```dart
context.go(RouteNames.projects);
context.push(RouteNames.videoDetailPath(projectId, videoId));
context.pop();
```

---

## Video Processing Flow

```
User selects file
      ↓
VideoCreateEvent → POST /projects/{id}/videos     → video.status = pending
      ↓
VideoUploadEvent → POST /videos/{id}/upload       → video.status = uploaded
      ↓
VideoProcessEvent → POST /videos/{id}/process     → returns task_id (202)
      ↓
Timer polls GET /videos/{id}/status every 3s
      ↓
status = completed → show thumbnail + output URL
status = failed    → show error message + retry button
```

---

## Build

```bash
# Android APK
flutter build apk --release

# Android App Bundle
flutter build appbundle --release

# iOS (requires Xcode + Apple Developer account)
flutter build ios --release

# Web
flutter build web --release
```