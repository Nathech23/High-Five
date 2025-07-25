
// lib/providers/language_provider.dart
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

class LanguageProvider extends ChangeNotifier {
  static const String _languageKey = 'selected_language';

  Locale _currentLocale = Locale('fr', '');
  String _currentLanguageName = 'Français';

  Locale get currentLocale => _currentLocale;
  String get currentLanguageName => _currentLanguageName;

  LanguageProvider() {
    _loadLanguage();
  }

  void changeLanguage(String languageCode, String languageName) {
    print("Langue changée vers $languageName – rechargement contextuel nécessaire");

    _currentLocale = Locale(languageCode, '');
    _currentLanguageName = languageName;
    _saveLanguage();
    notifyListeners();
  }

  Future<void> _loadLanguage() async {
    final prefs = await SharedPreferences.getInstance();
    final languageCode = prefs.getString(_languageKey) ?? 'fr';
    final languageName = _getLanguageName(languageCode);
    changeLanguage(languageCode, languageName);
  }

  Future<void> _saveLanguage() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_languageKey, _currentLocale.languageCode);
  }

  String _getLanguageName(String code) {
    switch (code) {
      case 'fr': return 'Français';
      case 'en': return 'English';
      case 'ff': return 'Fulfuldé';
      default: return 'Français';
    }
  }
}
