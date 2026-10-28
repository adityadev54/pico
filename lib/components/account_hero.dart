import 'package:flutter/material.dart';
import 'pico_brand.dart';

class AccountHero extends StatelessWidget {
  const AccountHero({super.key, required this.compact, required this.signUp});
  final bool compact, signUp;
  @override
  Widget build(BuildContext context) => Column(
    children: [
      PicoEmblem(size: compact ? 78 : 150),
      SizedBox(height: compact ? 8 : 16),
      Text(
        signUp ? 'Create your account' : 'Welcome back',
        style: TextStyle(
          fontSize: 26,
          fontWeight: FontWeight.w600,
          letterSpacing: -.8,
          color: Theme.of(context).colorScheme.onSurface,
        ),
      ),
    ],
  );
}
