// lib/providers/chat_provider.dart
import 'package:flutter/material.dart';
import '../models/message.dart';

class ChatProvider extends ChangeNotifier {
  List<Message> _messages = [];
  bool _isTyping = false;
  bool _isSpeechToTextEnabled = true;
  bool _isTextToSpeechEnabled = true;

  List<Message> get messages => _messages;
  bool get isTyping => _isTyping;
  bool get isSpeechToTextEnabled => _isSpeechToTextEnabled;
  bool get isTextToSpeechEnabled => _isTextToSpeechEnabled;

  void sendMessage(String text) {
    print("Envoi message – API POST /chat/message");

    final userMessage = Message(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      text: text,
      isUser: true,
      timestamp: DateTime.now(),
    );

    _messages.add(userMessage);
    notifyListeners();

    _simulateAIResponse(text);
  }

  void _simulateAIResponse(String userText) {
    _isTyping = true;
    notifyListeners();

    print("IA est en train d'écrire...");

    Future.delayed(Duration(seconds: 2), () {
      final aiResponse = _generateAIResponse(userText);
      final aiMessage = Message(
        id: DateTime.now().millisecondsSinceEpoch.toString(),
        text: aiResponse,
        isUser: false,
        timestamp: DateTime.now(),
      );

      _messages.add(aiMessage);
      _isTyping = false;
      notifyListeners();
    });
  }

  String _generateAIResponse(String userText) {
    // Simulation de réponse médicale basique
    if (userText.toLowerCase().contains('mal de tête') ||
        userText.toLowerCase().contains('migraine')) {
      return "Je comprends votre préoccupation concernant vos maux de tête. Voici quelques conseils généraux :\n\n• Assurez-vous de rester bien hydraté\n• Essayez de vous reposer dans un endroit calme\n• Évitez les écrans lumineux\n\nSi vos maux de tête persistent ou s'aggravent, je vous recommande vivement de consulter un professionnel de santé.\n\n⚠️ Ceci est un conseil général et ne remplace pas une consultation médicale.";
    } else if (userText.toLowerCase().contains('fièvre')) {
      return "La fièvre peut être le signe de diverses conditions. Voici ce que vous pouvez faire :\n\n• Surveillez votre température régulièrement\n• Restez hydraté avec beaucoup d'eau\n• Reposez-vous autant que possible\n\n🚨 Si votre fièvre dépasse 39°C ou persiste plus de 3 jours, consultez immédiatement un médecin.\n\n⚠️ En cas de difficultés respiratoires ou autres symptômes graves, rendez-vous aux urgences.";
    } else {
      return "Merci pour votre question. Je suis là pour vous aider avec vos préoccupations de santé. Pouvez-vous me donner plus de détails sur vos symptômes ?\n\nJe peux vous fournir des informations générales, mais n'oubliez pas que cela ne remplace jamais l'avis d'un professionnel de santé qualifié.\n\n💡 Pour une réponse plus précise, décrivez-moi :\n• Vos symptômes actuels\n• Depuis quand les ressentez-vous\n• Leur intensité";
    }
  }

  void sendQuickReply(String quickReply) {
    print("Quick reply sélectionnée – appel API Chatbot anticipé");
    sendMessage(quickReply);
  }

  void toggleSpeechToText() {
    _isSpeechToTextEnabled = !_isSpeechToTextEnabled;
    print("STT togglé: ${_isSpeechToTextEnabled ? 'ON' : 'OFF'}");
    notifyListeners();
  }

  void toggleTextToSpeech() {
    _isTextToSpeechEnabled = !_isTextToSpeechEnabled;
    print("TTS togglé: ${_isTextToSpeechEnabled ? 'ON' : 'OFF'}");
    notifyListeners();
  }

  void startSpeechToText() {
    print("STT: Déclenche reconnaissance vocale (Speech-to-Text)");
    // Simulation de reconnaissance vocale
  }

  void playTextToSpeech(String text) {
    print("TTS: Lecture réponse (Text-to-Speech)");
    // Simulation de synthèse vocale
  }

  void addToFavorites(String messageId) {
    print("Ajout aux favoris – API POST /chat/favorite");
    notifyListeners();
  }

  void clearChat() {
    _messages.clear();
    notifyListeners();
  }
}