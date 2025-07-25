
// lib/models/conversation.dart
import 'message.dart';

class Conversation {
  final String id;
  final String title;
  final DateTime lastMessageTime;
  final List<Message> messages;
  final bool isFavorite;

  Conversation({
    required this.id,
    required this.title,
    required this.lastMessageTime,
    required this.messages,
    this.isFavorite = false,
  });

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'lastMessageTime': lastMessageTime.toIso8601String(),
      'messages': messages.map((m) => m.toJson()).toList(),
      'isFavorite': isFavorite,
    };
  }

  factory Conversation.fromJson(Map<String, dynamic> json) {
    return Conversation(
      id: json['id'],
      title: json['title'],
      lastMessageTime: DateTime.parse(json['lastMessageTime']),
      messages: (json['messages'] as List)
          .map((m) => Message.fromJson(m))
          .toList(),
      isFavorite: json['isFavorite'] ?? false,
    );
  }
}
