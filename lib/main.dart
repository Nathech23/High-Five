// lib/main.dart
import 'package:flutter/material.dart';
import 'package:medical_assistant/screens/tab_navigator.dart';
import 'package:provider/provider.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

import 'providers/theme_provider.dart';
import 'providers/language_provider.dart';
import 'providers/auth_provider.dart';
import 'providers/chat_provider.dart';
import 'screens/login_screen.dart';
import 'screens/error_screen.dart';
import 'utils/app_localizations.dart';

void main() {
  print("Application médicale Flutter démarrée");
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => ThemeProvider()),
        ChangeNotifierProvider(create: (_) => LanguageProvider()),
        ChangeNotifierProvider(create: (_) => AuthProvider()),
        ChangeNotifierProvider(create: (_) => ChatProvider()),
      ],
      child: Consumer2<ThemeProvider, LanguageProvider>(
        builder: (context, themeProvider, languageProvider, child) {
          return MaterialApp(
            debugShowCheckedModeBanner: false,
            title: 'Assistant Médical',
            theme: themeProvider.currentTheme,
            locale: languageProvider.currentLocale,
            localizationsDelegates: [
              AppLocalizations.delegate,
              GlobalMaterialLocalizations.delegate,
              GlobalWidgetsLocalizations.delegate,
              GlobalCupertinoLocalizations.delegate,
            ],
            supportedLocales: [
              Locale('fr', ''),
              Locale('en', ''),
              Locale('ff', ''),
            ],
            initialRoute: '/',
            routes: {
              '/': (context) => LoginScreen(),
              '/home': (context) => TabNavigator(),
              '/error': (context) => ErrorScreen(),
            },
          );
        },
      ),
    );
  }
}