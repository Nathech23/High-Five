import 'package:flutter/material.dart';

class MedicalButton extends StatelessWidget {
  final String text;
  final bool isLoading;
  final IconData? icon;
  final VoidCallback onPressed;

  const MedicalButton({
    required this.text,
    required this.onPressed,
    this.isLoading = false,
    this.icon,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return ElevatedButton.icon(
      onPressed: isLoading ? null : onPressed,
      icon: icon != null
          ? Icon(icon, size: 20)
          : SizedBox.shrink(),
      label: isLoading
          ? SizedBox(
        height: 20,
        width: 20,
        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
      )
          : Text(text),
      style: ElevatedButton.styleFrom(
        backgroundColor: theme.primaryColor,
        foregroundColor: Colors.white,
        padding: EdgeInsets.symmetric(vertical: 16),
        textStyle: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
    );
  }
}
