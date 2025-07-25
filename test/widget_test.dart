import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:medical_assistant/main.dart';
import 'package:medical_assistant/providers/theme_provider.dart';
import 'package:medical_assistant/providers/language_provider.dart';
import 'package:medical_assistant/providers/auth_provider.dart';
import 'package:medical_assistant/providers/chat_provider.dart';
import 'package:medical_assistant/screens/login_screen.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('Main App Test', () {
    testWidgets('Lancement de l\'application - LoginScreen affiché', (WidgetTester tester) async {
      await tester.pumpWidget(
        MultiProvider(
          providers: [
            ChangeNotifierProvider(create: (_) => ThemeProvider()),
            ChangeNotifierProvider(create: (_) => LanguageProvider()),
            ChangeNotifierProvider(create: (_) => AuthProvider()),
            ChangeNotifierProvider(create: (_) => ChatProvider()),
          ],
          child: MaterialApp(
            home: LoginScreen(),
          ),
        ),
      );

      expect(find.byType(LoginScreen), findsOneWidget);
      expect(find.text('Connexion'), findsOneWidget);
      expect(find.byIcon(Icons.medical_services), findsOneWidget);
    });
  });
}
