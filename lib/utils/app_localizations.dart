
// lib/utils/app_localizations.dart
import 'package:flutter/material.dart';

class AppLocalizations {
  final Locale locale;

  AppLocalizations(this.locale);

  static AppLocalizations? of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations);
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
  _AppLocalizationsDelegate();

  Map<String, String> get _localizedStrings {
    switch (locale.languageCode) {
      case 'en':
        return _enStrings;
      case 'ff':
        return _ffStrings;
      default:
        return _frStrings;
    }
  }

  String translate(String key) {
    return _localizedStrings[key] ?? key;
  }

  // Français
  static const Map<String, String> _frStrings = {
    'app_title': 'Assistant Médical',
    'login': 'Connexion',
    'email': 'Email',
    'password': 'Mot de passe',
    'welcome': 'Bienvenue',
    'new_conversation': 'Nouvelle conversation',
    'history': 'Historique',
    'favorites': 'Favoris',
    'settings': 'Paramètres',
    'logout': 'Déconnexion',
    'type_message': 'Tapez votre message...',
    'send': 'Envoyer',
    'quick_replies': 'Réponses rapides',
    'language': 'Langue',
    'theme': 'Thème',
    'accessibility': 'Accessibilité',
  };

  // English
  static const Map<String, String> _enStrings = {
    'app_title': 'Medical Assistant',
    'login': 'Login',
    'email': 'Email',
    'password': 'Password',
    'welcome': 'Welcome',
    'new_conversation': 'New conversation',
    'history': 'History',
    'favorites': 'Favorites',
    'settings': 'Settings',
    'logout': 'Logout',
    'type_message': 'Type your message...',
    'send': 'Send',
    'quick_replies': 'Quick replies',
    'language': 'Language',
    'theme': 'Theme',
    'accessibility': 'Accessibility',
  };

  // Fulfuldé (basique)
  static const Map<String, String> _ffStrings = {
    'app_title': 'Ballotooɗo Dawro-Renndo',
    'login': 'Naatde',
    'email': 'Email',
    'password': 'Sariya',
    'welcome': 'Njaaraama',
    'new_conversation': 'Haalde hesere',
    'history': 'Taariika',
    'favorites': 'Ɓuuɗe-mi',
    'settings': 'Teelte',
    'logout': 'Yaltude',
    'type_message': 'Winndaa karfeeje maa...',
    'send': 'Neldu',
    'quick_replies': 'Jaabe suɓɓe',
    'language': 'Ɗemngal',
    'theme': 'Mbaadi',
    'accessibility': 'Yaajnde',
  };
}

class _AppLocalizationsDelegate extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  bool isSupported(Locale locale) {
    return ['fr', 'en', 'ff'].contains(locale.languageCode);
  }

  @override
  Future<AppLocalizations> load(Locale locale) async {
    return AppLocalizations(locale);
  }

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}