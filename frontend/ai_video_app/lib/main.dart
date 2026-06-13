import 'package:ai_video_saas/core/utils/app/app_bloc_observer.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import 'app.dart';
import 'core/di/injection_container.dart' as di;

Future<void> main() async {
  // Must be the very first call — inside the default zone
  WidgetsFlutterBinding.ensureInitialized();

  // Lock to portrait
  await SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
  ]);

  // Transparent status bar
  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      statusBarIconBrightness: Brightness.dark,
      statusBarBrightness: Brightness.light,
    ),
  );

  // Catch Flutter framework errors (widget build, layout, etc.)
  FlutterError.onError = (FlutterErrorDetails details) {
    FlutterError.presentError(details);
    if (kDebugMode) {
      debugPrint('FlutterError: ${details.exceptionAsString()}');
    }
  };

  // Catch async Dart errors outside the Flutter framework
  // Using PlatformDispatcher instead of runZonedGuarded — avoids zone mismatch
  PlatformDispatcher.instance.onError = (Object error, StackTrace stack) {
    if (kDebugMode) {
      debugPrint('PlatformDispatcher error: $error');
      debugPrint('$stack');
    }
    // In production: send to Sentry / Crashlytics here
    return true; // true = error handled, don't propagate
  };

  // Initialise GetIt dependency injection
  await di.init();

  // Attach BLoC observer for logging
  Bloc.observer = AppBlocObserver();

  // runApp in the SAME zone as ensureInitialized — no zone wrapping
  runApp(const App());
}
