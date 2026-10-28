import 'package:flutter/material.dart';
import 'package:kin_ui/kin_ui.dart';

abstract final class PicoTheme {
  // Explicit roles keep generated Material tints out of the interface.
  static const canvas = Color(0xFFF5F1EE);
  static const surface = Color(0xFFFFFAF7);
  static const ink = Color(0xFF2B2220);
  static const muted = Color(0xFF746763);
  static const accent = Color(0xFFB83835);
  static const accentDeep = Color(0xFF962C30);
  static const accentSoft = Color(0xFFE7786E);
  static const accentContainer = Color(0xFFF7E3DE);
  static const divider = Color(0xFFE6D8D2);
  static const drawer = Color(0xFF231F1E);
  static const drawerMuted = Color(0xFFC1B2AD);
  static const placeholder = Color(0xFF8A7A74);
  static const success = Color(0xFF74936B);

  static const signal = accentDeep;
  static const brandGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [accentDeep, accent, accentSoft],
  );
  static const actionGradient = LinearGradient(colors: [accent, accentDeep]);
  static const haloGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [canvas, accentContainer, surface],
  );

  static ThemeData get dark {
    final base = light;
    const colors = ColorScheme.dark(
      primary: accentSoft,
      onPrimary: Color(0xFF231F1E),
      primaryContainer: Color(0xFF49302D),
      onPrimaryContainer: Color(0xFFF7E3DE),
      secondary: accentSoft,
      onSecondary: Color(0xFF231F1E),
      secondaryContainer: Color(0xFF49302D),
      onSecondaryContainer: Color(0xFFF7E3DE),
      surface: Color(0xFF2C2725),
      onSurface: Color(0xFFF5F1EE),
      onSurfaceVariant: Color(0xFFC1B2AD),
      outline: Color(0xFF514440),
      outlineVariant: Color(0xFF453B37),
      surfaceTint: Colors.transparent,
      error: Color(0xFFFFB4AB),
      onError: Color(0xFF690005),
    );
    return base.copyWith(
      brightness: Brightness.dark,
      colorScheme: colors,
      scaffoldBackgroundColor: const Color(0xFF1F1B19),
      canvasColor: const Color(0xFF1F1B19),
      textTheme: base.textTheme.apply(
        bodyColor: colors.onSurface,
        displayColor: colors.onSurface,
      ),
      dividerColor: colors.outlineVariant,
      appBarTheme: const AppBarTheme(
        backgroundColor: Color(0xFF1F1B19),
        surfaceTintColor: Colors.transparent,
        elevation: 0,
      ),
      inputDecorationTheme: base.inputDecorationTheme.copyWith(
        fillColor: colors.surface,
      ),
      extensions: const [
        KinTheme(
          primary: accentSoft,
          primaryContainer: Color(0xFF49302D),
          surface: Color(0xFF1F1B19),
          surfaceVariant: Color(0xFF2C2725),
          onSurface: Color(0xFFF5F1EE),
          onSurfaceVariant: Color(0xFFC1B2AD),
          outline: Color(0xFF514440),
          destructive: Color(0xFFFFB4AB),
          success: success,
        ),
      ],
    );
  }

  static ThemeData get light {
    const colors = ColorScheme.light(
      primary: accent,
      onPrimary: Colors.white,
      primaryContainer: accentContainer,
      onPrimaryContainer: ink,
      secondary: accent,
      onSecondary: Colors.white,
      secondaryContainer: accentContainer,
      onSecondaryContainer: ink,
      tertiary: muted,
      onTertiary: Colors.white,
      tertiaryContainer: surface,
      onTertiaryContainer: ink,
      surface: surface,
      onSurface: ink,
      onSurfaceVariant: muted,
      surfaceDim: canvas,
      surfaceBright: surface,
      surfaceContainerLowest: surface,
      surfaceContainerLow: surface,
      surfaceContainer: surface,
      surfaceContainerHigh: surface,
      surfaceContainerHighest: surface,
      outline: divider,
      outlineVariant: divider,
      surfaceTint: Colors.transparent,
      error: Color(0xFFB3261E),
      onError: Colors.white,
    );
    final base = ThemeData(useMaterial3: true, colorScheme: colors);
    return base.copyWith(
      scaffoldBackgroundColor: canvas,
      canvasColor: canvas,
      textTheme: base.textTheme.apply(
        fontFamily: 'DM Sans',
        bodyColor: ink,
        displayColor: ink,
      ),
      dividerColor: divider,
      splashColor: const Color(0x14B83835),
      highlightColor: const Color(0x0AB83835),
      appBarTheme: const AppBarTheme(
        backgroundColor: canvas,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        scrolledUnderElevation: 0,
      ),
      dialogTheme: const DialogThemeData(
        backgroundColor: surface,
        surfaceTintColor: Colors.transparent,
      ),
      bottomSheetTheme: const BottomSheetThemeData(
        backgroundColor: surface,
        surfaceTintColor: Colors.transparent,
      ),
      chipTheme: ChipThemeData(
        backgroundColor: surface,
        selectedColor: accentContainer,
        surfaceTintColor: Colors.transparent,
        side: const BorderSide(color: divider),
        labelStyle: const TextStyle(color: ink),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: surface,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(32),
          borderSide: BorderSide.none,
        ),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 18,
          vertical: 14,
        ),
      ),
      extensions: const [
        KinTheme(
          primary: accent,
          primaryContainer: accentContainer,
          surface: canvas,
          surfaceVariant: surface,
          onSurface: ink,
          onSurfaceVariant: muted,
          outline: divider,
          destructive: Color(0xFFB3261E),
          success: success,
        ),
      ],
    );
  }
}
