
//lib/screens/history_screen.dart
import 'package:flutter/material.dart';

class HistoryScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    print("Accès à l’historique – API GET /chat/history");

    return Scaffold(
      appBar: AppBar(
        title: Text('Historique des conversations'),
        backgroundColor: Theme.of(context).primaryColor,
        foregroundColor: Colors.white,
      ),
      body: ListView.builder(
        itemCount: 3, // mock
        itemBuilder: (context, index) {
          final id = index + 1;
          return ListTile(
            leading: Icon(Icons.chat),
            title: Text('Conversation $id'),
            subtitle: Text('Dernier message il y a X jours'),
            onTap: () {
              print("Reprise conversation ID: $id – API GET /chat/history/$id");
            },
            trailing: IconButton(
              icon: Icon(Icons.delete_outline),
              onPressed: () {
                print("Suppression conversation ID: $id – API DELETE /chat/$id");
              },
            ),
          );
        },
      ),
    );
  }
}
