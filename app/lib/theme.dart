import 'package:flutter/material.dart';

/// App 色票與主題。色值對齊 web/src/styles.css（暖紙底 + 溫暖金），
/// 讓 App 與公開網站同一個視覺調性。
class Palette {
  final Color bg; // 頁面底
  final Color panel; // 卡片 / 面板
  final Color border; // 邊框
  final Color text; // 主文字
  final Color muted; // 次要文字
  final Color chip; // 淡底標籤 / 引言底
  final Color accent; // 溫暖金
  final Color accentText; // 連結文字（深一階）

  const Palette({
    required this.bg,
    required this.panel,
    required this.border,
    required this.text,
    required this.muted,
    required this.chip,
    required this.accent,
    required this.accentText,
  });

  static const light = Palette(
    bg: Color(0xFFFAF7F2),
    panel: Color(0xFFFFFFFF),
    border: Color(0xFFE7E0D5),
    text: Color(0xFF2B2620),
    muted: Color(0xFF8A8578),
    chip: Color(0xFFF1EBE1),
    accent: Color(0xFFB9852B),
    accentText: Color(0xFF9A6D1F),
  );

  static const dark = Palette(
    bg: Color(0xFF17150F),
    panel: Color(0xFF201D16),
    border: Color(0xFF35301F),
    text: Color(0xFFECE7DC),
    muted: Color(0xFFA49C8A),
    chip: Color(0xFF2B2718),
    accent: Color(0xFFD8A24A),
    accentText: Color(0xFFD8A24A),
  );

  static Palette of(BuildContext context) =>
      Theme.of(context).brightness == Brightness.dark ? dark : light;
}

const _seed = Color(0xFFB9852B); // 溫暖金（與 web --accent 一致）

ThemeData buildAppTheme(Brightness brightness) {
  final p = brightness == Brightness.dark ? Palette.dark : Palette.light;
  final scheme = ColorScheme.fromSeed(
    seedColor: _seed,
    brightness: brightness,
  ).copyWith(
    surface: p.panel,
    onSurface: p.text,
    onSurfaceVariant: p.muted,
    outline: p.muted,
  );

  final base = ThemeData(colorScheme: scheme, useMaterial3: true);
  final tt = base.textTheme.apply(bodyColor: p.text, displayColor: p.text);

  return base.copyWith(
    scaffoldBackgroundColor: p.bg,
    dividerColor: p.border,
    // 中文閱讀行距放寬，對齊 web 的 line-height: 1.7。
    textTheme: tt.copyWith(
      bodyLarge: tt.bodyLarge?.copyWith(height: 1.7),
      bodyMedium: tt.bodyMedium?.copyWith(height: 1.6),
    ),
    appBarTheme: AppBarTheme(
      backgroundColor: p.bg,
      surfaceTintColor: Colors.transparent,
      foregroundColor: p.text,
      centerTitle: true,
      elevation: 0,
      scrolledUnderElevation: 0.5,
      titleTextStyle: TextStyle(
        fontSize: 20,
        fontWeight: FontWeight.w600,
        letterSpacing: 3,
        color: p.text,
      ),
    ),
  );
}
