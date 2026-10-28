import 'package:flutter/material.dart';

class AccountSwitch extends StatelessWidget {
  const AccountSwitch({
    super.key,
    required this.signUp,
    required this.onToggle,
  });
  final bool signUp;
  final VoidCallback onToggle;
  @override
  Widget build(BuildContext context) => Wrap(
    alignment: WrapAlignment.center,
    crossAxisAlignment: WrapCrossAlignment.center,
    children: [
      Text(
        signUp ? 'Already have an account?' : 'New to Pico?',
        style: TextStyle(
          fontSize: 12,
          color: Theme.of(context).colorScheme.onSurfaceVariant,
        ),
      ),
      TextButton(
        onPressed: onToggle,
        child: Text(
          signUp ? 'Sign in instead' : 'Create an account',
          style: TextStyle(fontSize: 12),
        ),
      ),
    ],
  );
}
