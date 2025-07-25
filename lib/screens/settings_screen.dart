

//lib/screens/settings_screen.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/theme_provider.dart';
import '../providers/language_provider.dart';
import '../providers/chat_provider.dart';
import '../utils/app_localizations.dart';

class SettingsScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final themeProvider = Provider.of<ThemeProvider>(context);
    final languageProvider = Provider.of<LanguageProvider>(context);
    final chatProvider = Provider.of<ChatProvider>(context);
    final localizations = AppLocalizations.of(context);

    return Scaffold(
      appBar: AppBar(
        title: Text(localizations?.translate('settings') ?? 'Paramètres'),
        backgroundColor: Theme.of(context).primaryColor,
        foregroundColor: Colors.white,
      ),
      body: ListView(
        padding: EdgeInsets.all(16),
        children: [
          _buildSectionTitle('Langue'),
          _buildLanguageSelector(languageProvider),

          SizedBox(height: 24),
          _buildSectionTitle('Thème'),
          _buildThemeSelector(themeProvider),

          SizedBox(height: 24),
          _buildSectionTitle('Accessibilité'),
          SwitchListTile(
            title: Text('Synthèse vocale (TTS)'),
            value: chatProvider.isTextToSpeechEnabled,
            onChanged: (_) => chatProvider.toggleTextToSpeech(),
          ),
          SwitchListTile(
            title: Text('Notifications'),
            value: true,
            onChanged: (_) {
              print("Notifications togglées: ON/OFF");
            },
          ),
        ],
      ),
    );
  }

  Widget _buildSectionTitle(String title) {
    return Padding(
      padding: EdgeInsets.only(bottom: 8),
      child: Text(
        title,
        style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
      ),
    );
  }

  Widget _buildLanguageSelector(LanguageProvider provider) {
    return Column(
      children: [
        RadioListTile(
          title: Text('Français'),
          value: 'fr',
          groupValue: provider.currentLocale.languageCode,
          onChanged: (_) => provider.changeLanguage('fr', 'Français'),
        ),
        RadioListTile(
          title: Text('English'),
          value: 'en',
          groupValue: provider.currentLocale.languageCode,
          onChanged: (_) => provider.changeLanguage('en', 'English'),
        ),
        RadioListTile(
          title: Text('Fulfuldé'),
          value: 'ff',
          groupValue: provider.currentLocale.languageCode,
          onChanged: (_) => provider.changeLanguage('ff', 'Fulfuldé'),
        ),
      ],
    );
  }

  Widget _buildThemeSelector(ThemeProvider provider) {
    final current = provider.currentThemeName;
    final themeOptions = {
      'Médical Clair': ThemeProvider.medicalLightTheme,
      'Médical Foncé': ThemeProvider.medicalDarkTheme,
      'Hôpital Vert': ThemeProvider.hospitalGreenTheme,
      'Senior/Accessibilité': ThemeProvider.seniorAccessibilityTheme,
    };

    return Column(
      children: themeOptions.entries.map((entry) {
        return Card(
          margin: EdgeInsets.symmetric(vertical: 8),
          elevation: current == entry.key ? 4 : 1,
          color: entry.value.cardColor,
          child: RadioListTile(
            title: Text(
              entry.key,
              style: entry.value.textTheme.bodyLarge,
            ),
            value: entry.key,
            groupValue: current,
            onChanged: (_) {
              provider.changeTheme(entry.key);
            },
            secondary: Icon(Icons.color_lens, color: entry.value.primaryColor),
          ),
        );
      }).toList(),
    );
  }
}
