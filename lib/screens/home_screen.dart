
// lib/screens/home_screen.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../utils/app_localizations.dart';
import '../widgets/medical_button.dart';

class HomeScreen extends StatefulWidget {
  @override
  _HomeScreenState createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  @override
  void initState() {
    super.initState();
    print("Page d'accueil/Dashboard utilisateur initialisée");
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final localizations = AppLocalizations.of(context);
    final authProvider = Provider.of<AuthProvider>(context);

    return Scaffold(
      appBar: AppBar(
        title: Text(localizations?.translate('app_title') ?? 'Assistant Médical'),
        backgroundColor: theme.primaryColor,
        foregroundColor: Colors.white,
        elevation: 0,
        actions: [
          IconButton(
            icon: Icon(Icons.logout),
            onPressed: () => _handleLogout(),
          ),
        ],
      ),
      body: SafeArea(
        child: Padding(
          padding: EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Message de bienvenue
              Container(
                padding: EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: theme.cardColor,
                  borderRadius: BorderRadius.circular(12),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.grey.withOpacity(0.1),
                      spreadRadius: 1,
                      blurRadius: 4,
                      offset: Offset(0, 2),
                    ),
                  ],
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(
                          Icons.waving_hand,
                          color: theme.primaryColor,
                          size: 28,
                        ),
                        SizedBox(width: 12),
                        Text(
                          '${localizations?.translate('welcome') ?? 'Bienvenue'} ${authProvider.userName}!',
                          style: theme.textTheme.headlineLarge,
                        ),
                      ],
                    ),
                    SizedBox(height: 12),
                    Text(
                      'Comment puis-je vous aider aujourd\'hui avec vos questions de santé ?',
                      style: theme.textTheme.bodyLarge,
                    ),
                  ],
                ),
              ),

              SizedBox(height: 24),

              // Bouton principale: nouvelle conversation
              MedicalButton(
                text: localizations?.translate('new_conversation') ?? 'Démarrer une nouvelle conversation',
                icon: Icons.chat_bubble_outline,
                onPressed: () {
                  Navigator.of(context).pushNamed('/chat');
                },
              ),

              SizedBox(height: 16),

              // Grille des fonctionnalités
              Expanded(
                child: GridView.count(
                  crossAxisCount: 2,
                  crossAxisSpacing: 12,
                  mainAxisSpacing: 12,
                  childAspectRatio: 1.2,
                  children: [
                    _buildFeatureCard(
                      context,
                      title: localizations?.translate('history') ?? 'Historique',
                      icon: Icons.history,
                      onTap: () {
                        print("API GET /chat/history");
                        Navigator.of(context).pushNamed('/history');
                      },
                    ),
                    _buildFeatureCard(
                      context,
                      title: localizations?.translate('favorites') ?? 'Favoris',
                      icon: Icons.favorite_outline,
                      onTap: () {
                        print("API GET /chat/favorites");
                        Navigator.of(context).pushNamed('/favorites');
                      },
                    ),
                    _buildFeatureCard(
                      context,
                      title: 'Urgences',
                      icon: Icons.emergency,
                      color: Colors.red,
                      onTap: () {
                        print("Mode urgence activé - redirection vers urgences");
                        _showEmergencyDialog();
                      },
                    ),
                    _buildFeatureCard(
                      context,
                      title: 'Notifications',
                      icon: Icons.notifications_outlined,
                      onTap: () {
                        print("Notification simulée: rappel prise médicamenteuse");
                        _showNotificationDemo();
                      },
                    ),
                  ],
                ),
              ),

              // Liste conversations récentes (mockées)
              Container(
                height: 120,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Conversations récentes',
                      style: theme.textTheme.bodyLarge?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    SizedBox(height: 8),
                    Expanded(
                      child: ListView(
                        scrollDirection: Axis.horizontal,
                        children: [
                          _buildRecentConversationCard(
                            'Consultation migraine',
                            'Il y a 2 heures',
                            Icons.psychology_outlined,
                          ),
                          _buildRecentConversationCard(
                            'Questions diabète',
                            'Hier',
                            Icons.favorite_outline,
                          ),
                          _buildRecentConversationCard(
                            'Suivi tension',
                            'Il y a 3 jours',
                            Icons.trending_up,
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildFeatureCard(
      BuildContext context, {
        required String title,
        required IconData icon,
        required VoidCallback onTap,
        Color? color,
      }) {
    final theme = Theme.of(context);
    final cardColor = color ?? theme.primaryColor;

    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: EdgeInsets.all(16.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                icon,
                size: 32,
                color: cardColor,
              ),
              SizedBox(height: 8),
              Text(
                title,
                style: theme.textTheme.bodyMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                  color: cardColor,
                ),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildRecentConversationCard(String title, String time, IconData icon) {
    final theme = Theme.of(context);

    return Container(
      width: 140,
      margin: EdgeInsets.only(right: 12),
      child: Card(
        elevation: 1,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        child: Padding(
          padding: EdgeInsets.all(12.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(icon, size: 20, color: theme.primaryColor),
              SizedBox(height: 4),
              Text(
                title,
                style: theme.textTheme.bodyMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                  fontSize: 12,
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
              Spacer(),
              Text(
                time,
                style: theme.textTheme.bodyMedium?.copyWith(
                  fontSize: 10,
                  color: Colors.grey[600],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _showEmergencyDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Row(
          children: [
            Icon(Icons.warning, color: Colors.red),
            SizedBox(width: 8),
            Text('Urgence Médicale'),
          ],
        ),
        content: Text(
          'En cas d\'urgence médicale réelle, contactez immédiatement:\n\n🚨 SAMU: 15\n🚑 Pompiers: 18\n📞 Urgences: 112',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: Text('Compris'),
          ),
        ],
      ),
    );
  }

  void _showNotificationDemo() {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            Icon(Icons.medication, color: Colors.white),
            SizedBox(width: 8),
            Text('Rappel: Prise de médicament à 14h00'),
          ],
        ),
        backgroundColor: Theme.of(context).primaryColor,
        duration: Duration(seconds: 3),
      ),
    );
  }

  void _handleLogout() async {
    final authProvider = Provider.of<AuthProvider>(context, listen: false);
    await authProvider.logout();
    Navigator.of(context).pushReplacementNamed('/');
  }
}