import 'package:flutter/material.dart';
import 'package:heroicons/heroicons.dart';

import 'capsule_input.dart';

class AccountFields extends StatefulWidget {
  const AccountFields({
    super.key,
    required this.email,
    required this.password,
    required this.signUp,
    required this.enabled,
    required this.onSubmit,
  });
  final TextEditingController email, password;
  final bool signUp, enabled;
  final VoidCallback onSubmit;
  @override
  State<AccountFields> createState() => _AccountFieldsState();
}

class _AccountFieldsState extends State<AccountFields> {
  bool _hidden = true;
  @override
  Widget build(BuildContext context) => AutofillGroup(
    child: Column(
      children: [
        CapsuleInput(
          fieldKey: ValueKey('account-email'),
          controller: widget.email,
          hint: 'Email',
          icon: HeroIcons.envelope,
          enabled: widget.enabled,
          keyboardType: TextInputType.emailAddress,
          inputAction: TextInputAction.next,
          autofillHints: [AutofillHints.email],
          validator: (v) =>
              v != null && RegExp(r'^\S+@\S+\.\S+$').hasMatch(v.trim())
              ? null
              : 'Enter a valid email',
        ),
        SizedBox(height: 10),
        CapsuleInput(
          fieldKey: ValueKey('account-password'),
          controller: widget.password,
          hint: 'Password',
          icon: HeroIcons.lockClosed,
          enabled: widget.enabled,
          obscure: _hidden,
          inputAction: TextInputAction.done,
          autofillHints: [
            widget.signUp ? AutofillHints.newPassword : AutofillHints.password,
          ],
          validator: (v) => widget.signUp
              ? ((v?.length ?? 0) >= 8 ? null : 'Use at least 8 characters')
              : ((v?.isNotEmpty ?? false) ? null : 'Enter your password'),
          onSubmitted: (_) {
            if (widget.enabled) widget.onSubmit();
          },
          trailing: IconButton(
            tooltip: _hidden ? 'Show password' : 'Hide password',
            onPressed: widget.enabled
                ? () => setState(() => _hidden = !_hidden)
                : null,
            icon: HeroIcon(
              _hidden ? HeroIcons.eye : HeroIcons.eyeSlash,
              size: 19,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ),
        ),
      ],
    ),
  );
}
