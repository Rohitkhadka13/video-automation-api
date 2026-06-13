import 'package:flutter/foundation.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:logger/logger.dart';

/// Global BLoC observer attached in main.dart via [Bloc.observer].
///
/// In debug mode: logs all events, transitions and errors with colour output.
/// In release mode: only logs errors (to be forwarded to crash reporting).
class AppBlocObserver extends BlocObserver {
  AppBlocObserver()
      : _logger = Logger(
          printer: PrettyPrinter(
            methodCount: 0,
            errorMethodCount: 8,
            lineLength: 80,
            colors: true,
            printEmojis: true,
          ),
          level: kDebugMode ? Level.debug : Level.error,
        );

  final Logger _logger;

  @override
  void onCreate(BlocBase<dynamic> bloc) {
    super.onCreate(bloc);
    if (kDebugMode) {
      _logger.d('🟢 onCreate -- ${bloc.runtimeType}');
    }
  }

  @override
  void onEvent(Bloc<dynamic, dynamic> bloc, Object? event) {
    super.onEvent(bloc, event);
    if (kDebugMode) {
      _logger.d('📨 onEvent -- ${bloc.runtimeType}\n$event');
    }
  }

  @override
  void onChange(BlocBase<dynamic> bloc, Change<dynamic> change) {
    super.onChange(bloc, change);
    if (kDebugMode) {
      _logger.d(
        '🔄 onChange -- ${bloc.runtimeType}\n'
        'current: ${change.currentState}\n'
        'next:    ${change.nextState}',
      );
    }
  }

  @override
  void onTransition(
    Bloc<dynamic, dynamic> bloc,
    Transition<dynamic, dynamic> transition,
  ) {
    super.onTransition(bloc, transition);
    if (kDebugMode) {
      _logger.d(
        '➡️  onTransition -- ${bloc.runtimeType}\n'
        'event:   ${transition.event}\n'
        'current: ${transition.currentState}\n'
        'next:    ${transition.nextState}',
      );
    }
  }

  @override
  void onError(BlocBase<dynamic> bloc, Object error, StackTrace stackTrace) {
    super.onError(bloc, error, stackTrace);
    _logger.e(
      '❌ onError -- ${bloc.runtimeType}',
      error: error,
      stackTrace: stackTrace,
    );
  }

  @override
  void onClose(BlocBase<dynamic> bloc) {
    super.onClose(bloc);
    if (kDebugMode) {
      _logger.d('🔴 onClose -- ${bloc.runtimeType}');
    }
  }
}
