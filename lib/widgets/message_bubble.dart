
//lib/widgets/message_bubble.dart
import 'package:flutter/material.dart';
import '../models/message.dart';

class MessageBubble extends StatelessWidget {
  final Message message;
  final VoidCallback onTTSPressed;
  final VoidCallback onFavoritePressed;

  const MessageBubble({
    required this.message,
    required this.onTTSPressed,
    required this.onFavoritePressed,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isUser = message.isUser;

    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Card(
        color: isUser ? theme.primaryColor : theme.cardColor,
        margin: EdgeInsets.symmetric(vertical: 6),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
        ),
        child: Container(
          padding: EdgeInsets.all(12),
          constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.7),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                message.text,
                style: TextStyle(
                  color: isUser ? Colors.white : theme.textTheme.bodyLarge?.color,
                  fontSize: 16,
                ),
              ),
              SizedBox(height: 8),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  if (!isUser)
                    IconButton(
                      icon: Icon(Icons.volume_up, size: 20, color: theme.primaryColor),
                      onPressed: onTTSPressed,
                    ),
                  IconButton(
                    icon: Icon(
                      message.isFavorite ? Icons.favorite : Icons.favorite_border,
                      size: 20,
                      color: Colors.redAccent,
                    ),
                    onPressed: onFavoritePressed,
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
