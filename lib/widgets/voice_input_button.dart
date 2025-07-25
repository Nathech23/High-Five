
//lib/widgets/voice_input_button.dart
import 'package:flutter/material.dart';

class VoiceInputButton extends StatelessWidget {
  final VoidCallback onPressed;

  const VoiceInputButton({required this.onPressed});

  @override
  Widget build(BuildContext context) {
    return IconButton(
      icon: Icon(Icons.mic, color: Theme.of(context).primaryColor),
      onPressed: onPressed,
    );
  }
}
