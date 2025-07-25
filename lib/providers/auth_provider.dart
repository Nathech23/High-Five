
// lib/providers/auth_provider.dart
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

class AuthProvider extends ChangeNotifier {
  bool _isAuthenticated = false;
  String _userEmail = '';
  String _userName = '';

  bool get isAuthenticated => _isAuthenticated;
  String get userEmail => _userEmail;
  String get userName => _userName;

  AuthProvider() {
    _checkAuthStatus();
  }

  Future<bool> login(String email, String password) async {
    print("Connexion utilisateur – API POST /auth/login");

    // Simulation d'appel API
    await Future.delayed(Duration(seconds: 2));

    if (email == "patient@test.com" && password == "123456") {
      _isAuthenticated = true;
      _userEmail = email;
      _userName = "Patient Test";
      _saveAuthStatus();
      notifyListeners();
      return true;
    }

    return false;
  }

  Future<void> logout() async {
    print("Déconnexion utilisateur – API POST /auth/logout");

    _isAuthenticated = false;
    _userEmail = '';
    _userName = '';

    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();

    notifyListeners();
  }

  Future<void> _checkAuthStatus() async {
    final prefs = await SharedPreferences.getInstance();
    _isAuthenticated = prefs.getBool('is_authenticated') ?? false;
    _userEmail = prefs.getString('user_email') ?? '';
    _userName = prefs.getString('user_name') ?? '';
    notifyListeners();
  }

  Future<void> _saveAuthStatus() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('is_authenticated', _isAuthenticated);
    await prefs.setString('user_email', _userEmail);
    await prefs.setString('user_name', _userName);
  }
}