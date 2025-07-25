
// lib/models/message.dart
class Message {
  final String id;
  final String text;
  final bool isUser;
  final DateTime timestamp;
  final bool isFavorite;

  Message({
    required this.id,
    required this.text,
    required this.isUser,
    required this.timestamp,
    this.isFavorite = false,
  });

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'text': text,
      'isUser': isUser,
      'timestamp': timestamp.toIso8601String(),
      'isFavorite': isFavorite,
    };
  }

  factory Message.fromJson(Map<String, dynamic> json) {
    return Message(
      id: json['id'],
      text: json['text'],
      isUser: json['isUser'],
      timestamp: DateTime.parse(json['timestamp']),
      isFavorite: json['isFavorite'] ?? false,
    );
  }
}