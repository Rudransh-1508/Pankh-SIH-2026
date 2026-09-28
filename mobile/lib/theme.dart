import 'package:flutter/material.dart';

/// Colours drawn from Gond painting: peacock, leaf and turmeric on a cool paper ground.
abstract final class PankhColors {
  static const ink = Color(0xFF1B2A4A);
  static const inkSoft = Color(0xFF4A5670);
  static const peacock = Color(0xFF0E6F78);
  static const peacockDeep = Color(0xFF0A545B);
  static const peacockMist = Color(0xFFE1EFEF);
  static const turmeric = Color(0xFFE9A800);
  static const turmericMist = Color(0xFFFBF0CF);
  static const leaf = Color(0xFF2F7D4F);
  static const leafMist = Color(0xFFE2F0E7);
  static const laterite = Color(0xFFB3412E);
  static const lateriteMist = Color(0xFFF6E4E0);
  static const paper = Color(0xFFF5F7F6);
  static const card = Color(0xFFFFFFFF);
  static const line = Color(0xFFDCE3E1);
}

abstract final class PankhSpace {
  static const xs = 4.0;
  static const sm = 8.0;
  static const md = 16.0;
  static const lg = 24.0;
  static const xl = 32.0;
  static const gutter = 20.0;
}

const _body = 'NotoSans';
const _display = 'Baloo2';
const _fallback = ['NotoSansDevanagari'];

TextStyle _text(String family, double size, FontWeight weight, double height, Color color) =>
    TextStyle(
      fontFamily: family,
      fontFamilyFallback: _fallback,
      fontSize: size,
      fontWeight: weight,
      height: height,
      color: color,
    );

ThemeData pankhTheme() {
  final textTheme = TextTheme(
    displaySmall: _text(_display, 32, FontWeight.w700, 1.12, PankhColors.ink),
    headlineMedium: _text(_display, 28, FontWeight.w700, 1.18, PankhColors.ink),
    headlineSmall: _text(_display, 24, FontWeight.w700, 1.2, PankhColors.ink),
    titleLarge: _text(_display, 21, FontWeight.w700, 1.2, PankhColors.ink),
    titleMedium: _text(_body, 17, FontWeight.w600, 1.3, PankhColors.ink),
    titleSmall: _text(_body, 15, FontWeight.w600, 1.3, PankhColors.ink),
    bodyLarge: _text(_body, 17, FontWeight.w400, 1.45, PankhColors.ink),
    bodyMedium: _text(_body, 15, FontWeight.w400, 1.45, PankhColors.inkSoft),
    bodySmall: _text(_body, 13, FontWeight.w400, 1.4, PankhColors.inkSoft),
    labelLarge: _text(_body, 17, FontWeight.w600, 1.2, PankhColors.ink),
    labelMedium: _text(_body, 13, FontWeight.w600, 1.2, PankhColors.inkSoft),
  );

  final colors = ColorScheme.fromSeed(
    seedColor: PankhColors.peacock,
    primary: PankhColors.peacock,
    onPrimary: Colors.white,
    secondary: PankhColors.turmeric,
    error: PankhColors.laterite,
    surface: PankhColors.paper,
    onSurface: PankhColors.ink,
  );

  final buttonShape = RoundedRectangleBorder(borderRadius: BorderRadius.circular(16));

  return ThemeData(
    useMaterial3: true,
    colorScheme: colors,
    scaffoldBackgroundColor: PankhColors.paper,
    fontFamily: _body,
    fontFamilyFallback: _fallback,
    textTheme: textTheme,
    appBarTheme: AppBarTheme(
      backgroundColor: PankhColors.paper,
      foregroundColor: PankhColors.ink,
      elevation: 0,
      scrolledUnderElevation: 0,
      centerTitle: false,
      titleTextStyle: textTheme.titleMedium,
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        minimumSize: const Size.fromHeight(58),
        shape: buttonShape,
        textStyle: textTheme.labelLarge,
        backgroundColor: PankhColors.peacock,
        foregroundColor: Colors.white,
        disabledBackgroundColor: PankhColors.line,
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        minimumSize: const Size.fromHeight(58),
        shape: buttonShape,
        textStyle: textTheme.labelLarge,
        foregroundColor: PankhColors.ink,
        side: const BorderSide(color: PankhColors.line, width: 1.5),
        backgroundColor: PankhColors.card,
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        minimumSize: const Size(48, 48),
        foregroundColor: PankhColors.peacockDeep,
        textStyle: textTheme.titleSmall,
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: PankhColors.card,
      contentPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 18),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: PankhColors.line, width: 1.5),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: PankhColors.line, width: 1.5),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: PankhColors.peacock, width: 2),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: PankhColors.laterite, width: 1.5),
      ),
    ),
    dividerTheme: const DividerThemeData(color: PankhColors.line, space: 1, thickness: 1),
    snackBarTheme: SnackBarThemeData(
      behavior: SnackBarBehavior.floating,
      backgroundColor: PankhColors.ink,
      contentTextStyle: textTheme.bodyMedium?.copyWith(color: Colors.white),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
    ),
  );
}
