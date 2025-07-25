
// lib/screens/chat_screen.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/chat_provider.dart';
import '../widgets/message_bubble.dart';
import '../widgets/typing_indicator.dart';
import '../widgets/quick_reply_bar.dart';
import '../widgets/voice_input_button.dart';

class ChatScreen extends StatefulWidget {
  @override
  _ChatScreenState createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final TextEditingController _messageController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final FocusNode _focusNode = FocusNode();

  @override
  void initState() {
    super.initState();
    print("Page principale du Chatbot initialisée");
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            CircleAvatar(
              backgroundColor: Colors.white,
              child: Icon(
                Icons.medical_services,
                color: theme.primaryColor,
              ),
            ),
            SizedBox(width: 12),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Assistant Médical',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
                Text(
                  'En ligne',
                  style: TextStyle(fontSize: 12, color: Colors.white70),
                ),
              ],
            ),
          ],
        ),
        backgroundColor: theme.primaryColor,
        foregroundColor: Colors.white,
        elevation: 0,
        actions: [
          IconButton(
            icon: Icon(Icons.more_vert),
            onPressed: () {
              _showChatOptions();
            },
          ),
        ],
      ),
      body: Column(
        children: [
          // Suggestions de questions rapides
          QuickReplyBar(),

          // Zone de messages
          Expanded(
            child: Consumer<ChatProvider>(
              builder: (context, chatProvider, child) {
                return ListView.builder(
                  controller: _scrollController,
                  padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  itemCount: chatProvider.messages.length + (chatProvider.isTyping ? 1 : 0),
                  itemBuilder: (context, index) {
                    if (index == chatProvider.messages.length && chatProvider.isTyping) {
                      return TypingIndicator();
                    }

                    final message = chatProvider.messages[index];
                    return MessageBubble(
                      message: message,
                      onTTSPressed: () {
                        chatProvider.playTextToSpeech(message.text);
                      },
                      onFavoritePressed: () {
                        chatProvider.addToFavorites(message.id);
                      },
                    );
                  },
                );
              },
            ),
          ),

          // Zone de saisie
          _buildInputArea(),
        ],
      ),
    );
  }

  Widget _buildInputArea() {
    final theme = Theme.of(context);

    return Container(
      padding: EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: theme.scaffoldBackgroundColor,
        boxShadow: [
          BoxShadow(
            color: Colors.grey.withOpacity(0.1),
            spreadRadius: 1,
            blurRadius: 4,
            offset: Offset(0, -2),
          ),
        ],
      ),
      child: Row(
        children: [
          // Bouton micro
          VoiceInputButton(
            onPressed: () {
              final chatProvider = Provider.of<ChatProvider>(context, listen: false);
              chatProvider.startSpeechToText();
            },
          ),

          SizedBox(width: 12),

          // Zone de texte
          Expanded(
            child: Container(
              constraints: BoxConstraints(maxHeight: 120),
              decoration: BoxDecoration(
                color: theme.cardColor,
                borderRadius: BorderRadius.circular(24),
                border: Border.all(color: Colors.grey.withOpacity(0.3)),
              ),
              child: TextField(
                controller: _messageController,
                focusNode: _focusNode,
                maxLines: null,
                textInputAction: TextInputAction.newline,
                decoration: InputDecoration(
                  hintText: 'Tapez votre question médicale...',
                  border: InputBorder.none,
                  contentPadding: EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                  hintStyle: TextStyle(color: Colors.grey[500]),
                ),
                onChanged: (text) {
                  setState(() {});
                },
                onSubmitted: (text) {
                  if (text.trim().isNotEmpty) {
                    _sendMessage();
                  }
                },
              ),
            ),
          ),

          SizedBox(width: 12),

          // Bouton envoyer
          GestureDetector(
            onTap: _messageController.text.trim().isEmpty ? null : _sendMessage,
            child: Container(
              padding: EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: _messageController.text.trim().isEmpty
                    ? Colors.grey[300]
                    : theme.primaryColor,
                shape: BoxShape.circle,
              ),
              child: Icon(
                Icons.send,
                color: _messageController.text.trim().isEmpty
                    ? Colors.grey[500]
                    : Colors.white,
                size: 24,
              ),
            ),
          ),
        ],
      ),
    );
  }

  void _sendMessage() {
    final text = _messageController.text.trim();
    if (text.isEmpty) return;

    final chatProvider = Provider.of<ChatProvider>(context, listen: false);
    chatProvider.sendMessage(text);

    _messageController.clear();
    _scrollToBottom();

    // Retirer le focus du champ de texte
    _focusNode.unfocus();
  }

  void _scrollToBottom() {
    Future.delayed(Duration(milliseconds: 100), () {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _showChatOptions() {
    showModalBottomSheet(
      context: context,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) => Container(
        padding: EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: Icon(Icons.clear_all),
              title: Text('Effacer la conversation'),
              onTap: () {
                Navigator.pop(context);
                _clearConversation();
              },
            ),
            ListTile(
              leading: Icon(Icons.download),
              title: Text('Exporter la conversation'),
              onTap: () {
                Navigator.pop(context);
                print("Export conversation – API GET /chat/export");
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text('Fonctionnalité en développement')),
                );
              },
            ),
            ListTile(
              leading: Icon(Icons.share),
              title: Text('Partager avec médecin'),
              onTap: () {
                Navigator.pop(context);
                print("Partage conversation – à implémenter");
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text('Fonctionnalité en développement')),
                );
              },
            ),
          ],
        ),
      ),
    );
  }

  void _clearConversation() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Effacer la conversation'),
        content: Text('Êtes-vous sûr de vouloir effacer toute la conversation ?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('Annuler'),
          ),
          TextButton(
            onPressed: () {
              final chatProvider = Provider.of<ChatProvider>(context, listen: false);
              chatProvider.clearChat();
              Navigator.pop(context);
            },
            child: Text('Effacer', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _messageController.dispose();
    _scrollController.dispose();
    _focusNode.dispose();
    super.dispose();
  }
}
