

//lib/widgets/typing_indicator.dart

import 'package:flutter/material.dart';

class TypingIndicator extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        CircleAvatar(radius: 10, backgroundColor: Theme.of(context).primaryColor),
        SizedBox(width: 8),
        Text("L'IA est en train d’écrire...", style: TextStyle(fontStyle: FontStyle.italic)),
      ],
    );
  }
}
