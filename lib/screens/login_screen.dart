
// lib/screens/login_screen.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../utils/app_localizations.dart';
import '../widgets/medical_button.dart';
import '../widgets/medical_text_field.dart';

class LoginScreen extends StatefulWidget {
  @override
  _LoginScreenState createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _formKey = GlobalKey<FormState>();
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    print("Écran de connexion initialisé");

    // Redirection automatique si déjà connecté
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final authProvider = Provider.of<AuthProvider>(context, listen: false);
      if (authProvider.isAuthenticated) {
        Navigator.of(context).pushReplacementNamed('/home');
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final localizations = AppLocalizations.of(context);

    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: EdgeInsets.all(24.0),
          child: Form(
            key: _formKey,
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Logo et titre
                Icon(
                  Icons.medical_services,
                  size: 80,
                  color: theme.primaryColor,
                ),
                SizedBox(height: 24),
                Text(
                  localizations?.translate('app_title') ?? 'Assistant Médical',
                  style: theme.textTheme.headlineLarge,
                  textAlign: TextAlign.center,
                ),
                SizedBox(height: 48),

                // Champ email
                MedicalTextField(
                  controller: _emailController,
                  labelText: localizations?.translate('email') ?? 'Email',
                  keyboardType: TextInputType.emailAddress,
                  prefixIcon: Icons.email_outlined,
                  validator: (value) {
                    if (value == null || value.isEmpty) {
                      return 'Veuillez saisir votre email';
                    }
                    if (!value.contains('@')) {
                      return 'Email invalide';
                    }
                    return null;
                  },
                ),
                SizedBox(height: 16),

                // Champ mot de passe
                MedicalTextField(
                  controller: _passwordController,
                  labelText: localizations?.translate('password') ?? 'Mot de passe',
                  obscureText: true,
                  prefixIcon: Icons.lock_outlined,
                  validator: (value) {
                    if (value == null || value.isEmpty) {
                      return 'Veuillez saisir votre mot de passe';
                    }
                    if (value.length < 6) {
                      return 'Le mot de passe doit contenir au moins 6 caractères';
                    }
                    return null;
                  },
                ),
                SizedBox(height: 32),

                // Bouton connexion
                MedicalButton(
                  text: localizations?.translate('login') ?? 'Connexion',
                  isLoading: _isLoading,
                  onPressed: _handleLogin,
                ),
                SizedBox(height: 16),

                // Lien créer un compte
                TextButton(
                  onPressed: () {
                    print("Redirection inscription – à implémenter plus tard");
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: Text('Fonctionnalité en cours de développement'),
                        backgroundColor: theme.primaryColor,
                      ),
                    );
                  },
                  child: Text(
                    'Créer un compte',
                    style: TextStyle(color: theme.primaryColor),
                  ),
                ),

                // Info de test
                SizedBox(height: 24),
                Container(
                  padding: EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: theme.primaryColor.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '🧪 Compte de test:',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                      Text('Email: patient@test.com'),
                      Text('Mot de passe: 123456'),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _handleLogin() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isLoading = true);

    final authProvider = Provider.of<AuthProvider>(context, listen: false);

    try {
      final success = await authProvider.login(
        _emailController.text.trim(),
        _passwordController.text,
      );

      if (success) {
        Navigator.of(context).pushReplacementNamed('/home');
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Email ou mot de passe incorrect'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Erreur de connexion: ${e.toString()}'),
          backgroundColor: Colors.red,
        ),
      );
    }

    setState(() => _isLoading = false);
  }

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }
}
