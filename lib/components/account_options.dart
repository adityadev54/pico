import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

class AccountOptions extends StatelessWidget {
  const AccountOptions({
    super.key,
    required this.remember,
    required this.onRemember,
    required this.onForgot,
    required this.enabled,
  });
  final bool remember, enabled;
  final ValueChanged<bool> onRemember;
  final VoidCallback onForgot;
  @override
  Widget build(BuildContext context) => Row(
    mainAxisAlignment: MainAxisAlignment.spaceBetween,
    children: [
      Flexible(
        child: InkWell(
          borderRadius: BorderRadius.circular(24),
          onTap: enabled ? () => onRemember(!remember) : null,
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Checkbox(
                value: remember,
                onChanged: enabled ? (v) => onRemember(v!) : null,
                activeColor: PicoTheme.accent,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(5),
                ),
              ),
              Flexible(
                child: Text(
                  'Remember me',
                  style: TextStyle(
                    fontSize: 12,
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
      SizedBox(width: 8),
      Flexible(
        child: TextButton(
          style: TextButton.styleFrom(
            padding: EdgeInsets.zero,
            alignment: Alignment.centerRight,
            minimumSize: Size(48, 48),
          ),
          onPressed: enabled ? onForgot : null,
          child: Text(
            'Forgot password?',
            textAlign: TextAlign.right,
            style: TextStyle(fontSize: 12),
          ),
        ),
      ),
    ],
  );
}
