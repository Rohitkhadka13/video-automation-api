/// Form field validators used with [TextFormField.validator].
/// All methods return null on success, or an error string on failure.
abstract final class Validators {
  Validators._();

  // ── Basic ─────────────────────────────────────────────────────────────────

  static String? required(String? value, {String fieldName = 'This field'}) {
    if (value == null || value.trim().isEmpty) {
      return '$fieldName is required';
    }
    return null;
  }

  static String? minLength(String? value, int min,
      {String fieldName = 'Value'}) {
    if (value != null && value.isNotEmpty && value.length < min) {
      return '$fieldName must be at least $min characters';
    }
    return null;
  }

  static String? maxLength(String? value, int max,
      {String fieldName = 'Value'}) {
    if (value != null && value.length > max) {
      return '$fieldName must not exceed $max characters';
    }
    return null;
  }

  // ── Auth ──────────────────────────────────────────────────────────────────

  static String? email(String? value) {
    if (value == null || value.trim().isEmpty) {
      return 'Email is required';
    }
    final regex = RegExp(
      r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$',
    );
    if (!regex.hasMatch(value.trim())) {
      return 'Please enter a valid email address';
    }
    return null;
  }

  static String? password(String? value) {
    if (value == null || value.isEmpty) return 'Password is required';
    if (value.length < 8) return 'Password must be at least 8 characters';
    if (!value.contains(RegExp(r'[A-Z]'))) {
      return 'Password must contain at least one uppercase letter';
    }
    if (!value.contains(RegExp(r'[0-9]'))) {
      return 'Password must contain at least one number';
    }
    return null;
  }

  static String? Function(String?) confirmPassword(String? original) {
    return (String? value) {
      if (value == null || value.isEmpty) return 'Please confirm your password';
      if (value != original) return 'Passwords do not match';
      return null;
    };
  }

  // ── Content ───────────────────────────────────────────────────────────────

  static String? projectName(String? value) {
    final req = required(value, fieldName: 'Project name');
    if (req != null) return req;
    return maxLength(value, 255, fieldName: 'Project name');
  }

  static String? videoTitle(String? value) {
    final req = required(value, fieldName: 'Video title');
    if (req != null) return req;
    return maxLength(value, 500, fieldName: 'Video title');
  }

  static String? fullName(String? value) {
    final req = required(value, fieldName: 'Full name');
    if (req != null) return req;
    return maxLength(value, 255, fieldName: 'Full name');
  }

  static String? optionalUrl(String? value) {
    if (value == null || value.trim().isEmpty) return null;
    final uri = Uri.tryParse(value.trim());
    if (uri == null || (!uri.isScheme('http') && !uri.isScheme('https'))) {
      return 'Please enter a valid URL';
    }
    return null;
  }

  // ── Compose validators ─────────────────────────────────────────────────────

  /// Chain multiple validators — returns the first non-null error.
  static String? Function(String?) compose(
    List<String? Function(String?)> validators,
  ) {
    return (String? value) {
      for (final validator in validators) {
        final error = validator(value);
        if (error != null) return error;
      }
      return null;
    };
  }
}
