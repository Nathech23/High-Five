
//lib/screens/favorites_screen.dart
import 'package:flutter/material.dart';

class FavoritesScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    print("Chargement favoris – API GET /chat/favorites");

    return Scaffold(
      appBar: AppBar(
        title: Text('Favoris'),
        backgroundColor: Theme.of(context).primaryColor,
        foregroundColor: Colors.white,
      ),
      body: ListView.builder(
        itemCount: 3, // mock
        itemBuilder: (context, index) {
          return ListTile(
            leading: Icon(Icons.favorite, color: Colors.red),
            title: Text('Réponse médicale ${index + 1}'),
            subtitle: Text('Extrait de la conversation sauvegardée...'),
            trailing: IconButton(
              icon: Icon(Icons.share),
              onPressed: () {
                print("Partage conversation – à implémenter");
              },
            ),
          );
        },
      ),
    );
  }
}
