import 'package:flutter/material.dart';
import 'package:heroicons/heroicons.dart';
import '../theme/app_theme.dart';

class AccountSubmit extends StatelessWidget {
  const AccountSubmit({
    super.key,
    required this.label,
    required this.busy,
    required this.onSubmit,
  });
  final String label;
  final bool busy;
  final VoidCallback onSubmit;
  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: BoxDecoration(
      borderRadius: BorderRadius.circular(30),
      gradient: PicoTheme.actionGradient,
      boxShadow: [
        BoxShadow(
          color: PicoTheme.accent.withValues(alpha: .16),
          blurRadius: 16,
          offset: const Offset(0, 5),
        ),
      ],
    ),
    child: SizedBox(
      width: double.infinity,
      child: FilledButton(
        onPressed: busy ? null : onSubmit,
        style: FilledButton.styleFrom(
          backgroundColor: Colors.transparent,
          disabledBackgroundColor: Colors.transparent,
          foregroundColor: Colors.white,
          disabledForegroundColor: Colors.white70,
          minimumSize: const Size.fromHeight(52),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          shape: const StadiumBorder(),
          textStyle: const TextStyle(
            fontSize: 15,
            fontWeight: FontWeight.w600,
            fontFamily: 'DM Sans',
          ),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Flexible(child: Text(busy ? 'One moment…' : label)),
            if (busy)
              const SizedBox(
                width: 18,
                height: 18,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: Colors.white,
                ),
              )
            else
              const HeroIcon(
                HeroIcons.arrowRight,
                size: 20,
                color: Colors.white,
              ),
          ],
        ),
      ),
    ),
  );
}
