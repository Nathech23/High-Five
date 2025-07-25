// lib/providers/theme_provider.dart
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

class ThemeProvider extends ChangeNotifier {
  static const String _themeKey = 'selected_theme';

  ThemeData _currentTheme = medicalLightTheme;
  String _currentThemeName = 'Médical Clair';

  ThemeData get currentTheme => _currentTheme;
  String get currentThemeName => _currentThemeName;

  ThemeProvider() {
    _loadTheme();
  }

  static final ThemeData medicalLightTheme = ThemeData(
    primarySwatch: Colors.blue,
    primaryColor: Color(0xFF2196F3),
    scaffoldBackgroundColor: Color(0xFFF8F9FA),
    cardColor: Colors.white,
    textTheme: TextTheme(
      headlineLarge: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: Color(0xFF1976D2)),
      bodyLarge: TextStyle(fontSize: 16, color: Color(0xFF424242)),
      bodyMedium: TextStyle(fontSize: 14, color: Color(0xFF757575)),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: Color(0xFF2196F3),
        foregroundColor: Colors.white,
        padding: EdgeInsets.symmetric(horizontal: 32, vertical: 16),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
    ),
  );

  static final ThemeData medicalDarkTheme = ThemeData(
    brightness: Brightness.dark,
    primarySwatch: Colors.blue,
    primaryColor: Color(0xFF1976D2),
    scaffoldBackgroundColor: Color(0xFF121212),
    cardColor: Color(0xFF1E1E1E),
    textTheme: TextTheme(
      headlineLarge: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: Color(0xFF64B5F6)),
      bodyLarge: TextStyle(fontSize: 16, color: Color(0xFFE0E0E0)),
      bodyMedium: TextStyle(fontSize: 14, color: Color(0xFFBDBDBD)),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: Color(0xFF1976D2),
        foregroundColor: Colors.white,
        padding: EdgeInsets.symmetric(horizontal: 32, vertical: 16),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
    ),
  );

  static final ThemeData hospitalGreenTheme = ThemeData(
    primarySwatch: Colors.teal,
    primaryColor: Color(0xFF00796B),
    scaffoldBackgroundColor: Color(0xFFE0F2F1),
    cardColor: Colors.white,
    textTheme: TextTheme(
      headlineLarge: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: Color(0xFF00695C)),
      bodyLarge: TextStyle(fontSize: 16, color: Color(0xFF424242)),
      bodyMedium: TextStyle(fontSize: 14, color: Color(0xFF757575)),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: Color(0xFF00796B),
        foregroundColor: Colors.white,
        padding: EdgeInsets.symmetric(horizontal: 32, vertical: 16),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
    ),
  );

  static final ThemeData seniorAccessibilityTheme = ThemeData(
    primarySwatch: Colors.indigo,
    primaryColor: Color(0xFF3F51B5),
    scaffoldBackgroundColor: Color(0xFFFFFDE7),
    cardColor: Colors.white,
    textTheme: TextTheme(
      headlineLarge: TextStyle(fontSize: 28, fontWeight: FontWeight.bold, color: Color(0xFF1A237E)),
      bodyLarge: TextStyle(fontSize: 20, color: Color(0xFF000000), fontWeight: FontWeight.w500),
      bodyMedium: TextStyle(fontSize: 18, color: Color(0xFF424242), fontWeight: FontWeight.w500),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: Color(0xFF3F51B5),
        foregroundColor: Colors.white,
        padding: EdgeInsets.symmetric(horizontal: 48, vertical: 24),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        textStyle: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
      ),
    ),
  );

  void changeTheme(String themeName) {
    print("Changement de thème vers $themeName");

    switch (themeName) {
      case 'Médical Clair':
        _currentTheme = medicalLightTheme;
        break;
      case 'Médical Foncé':
        _currentTheme = medicalDarkTheme;
        break;
      case 'Hôpital Vert':
        _currentTheme = hospitalGreenTheme;
        break;
      case 'Senior/Accessibilité':
        _currentTheme = seniorAccessibilityTheme;
        break;
      default:
        _currentTheme = medicalLightTheme;
        themeName = 'Médical Clair';
    }

    _currentThemeName = themeName;
    _saveTheme();
    notifyListeners();
  }

  Future<void> _loadTheme() async {
    final prefs = await SharedPreferences.getInstance();
    final themeName = prefs.getString(_themeKey) ?? 'Médical Clair';
    changeTheme(themeName);
  }

  Future<void> _saveTheme() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_themeKey, _currentThemeName);
  }
}