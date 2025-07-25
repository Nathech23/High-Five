
//lib/widgets/quick_reply_bar.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/chat_provider.dart';

class QuickReplyBar extends StatelessWidget {
  final List<String> suggestions = [
    "J’ai mal à la tête",
    "J’ai de la fièvre",
    "Je tousse beaucoup",
  ];

  @override
  Widget build(BuildContext context) {
    final chatProvider = Provider.of<ChatProvider>(context, listen: false);

    return Container(
      height: 48,
      margin: EdgeInsets.symmetric(vertical: 8),
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: EdgeInsets.symmetric(horizontal: 16),
        itemCount: suggestions.length,
        separatorBuilder: (_, __) => SizedBox(width: 8),
        itemBuilder: (_, index) {
          return ActionChip(
            label: Text(suggestions[index]),
            onPressed: () => chatProvider.sendQuickReply(suggestions[index]),
            backgroundColor: Theme.of(context).primaryColor.withOpacity(0.1),
            labelStyle: TextStyle(color: Theme.of(context).primaryColor),
          );
        },
      ),
    );
  }
}
