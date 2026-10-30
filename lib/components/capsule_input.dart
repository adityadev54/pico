import 'package:flutter/material.dart';
import 'package:heroicons/heroicons.dart';

import 'floating_surface.dart';

/// The toolbar's capsule surface, shared by account, search and conversation.
class CapsuleInput extends StatelessWidget {
  const CapsuleInput({
    super.key,
    this.fieldKey,
    this.focusNode,
    this.controller,
    required this.hint,
    required this.icon,
    this.trailing,
    this.leading,
    this.autofocus = false,
    this.enabled = true,
    this.obscure = false,
    this.maxLines = 1,
    this.keyboardType,
    this.inputAction,
    this.autofillHints,
    this.validator,
    this.onChanged,
    this.onSubmitted,
  });
  final Key? fieldKey;
  final FocusNode? focusNode;
  final TextEditingController? controller;
  final String hint;
  final HeroIcons icon;
  final Widget? trailing, leading;
  final bool autofocus, enabled, obscure;
  final int maxLines;
  final TextInputType? keyboardType;
  final TextInputAction? inputAction;
  final Iterable<String>? autofillHints;
  final String? Function(String?)? validator;
  final ValueChanged<String>? onChanged, onSubmitted;
  @override
  Widget build(BuildContext context) => FloatingSurface(
    radius: 32,
    child: Padding(
      padding: EdgeInsets.fromLTRB(leading == null ? 16 : 4, 3, 6, 3),
      child: Row(
        children: [
          leading ??
              HeroIcon(
                icon,
                size: 20,
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
          SizedBox(width: leading == null ? 12 : 4),
          Expanded(
            child: TextFormField(
              key: fieldKey,
              controller: controller,
              focusNode: focusNode,
              autofocus: autofocus,
              enabled: enabled,
              obscureText: obscure,
              minLines: 1,
              maxLines: maxLines,
              keyboardType: keyboardType,
              textInputAction: inputAction,
              autofillHints: autofillHints,
              autocorrect: false,
              enableSuggestions:
                  !obscure && keyboardType != TextInputType.emailAddress,
              validator: validator,
              onChanged: onChanged,
              onFieldSubmitted: onSubmitted,
              style: TextStyle(
                fontSize: 15,
                height: 1.4,
                color: Theme.of(context).colorScheme.onSurface,
              ),
              decoration: InputDecoration(
                hintText: hint,
                hintStyle: TextStyle(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                  fontSize: 15,
                ),
                filled: false,
                isDense: true,
                contentPadding: EdgeInsets.symmetric(vertical: 14),
                border: InputBorder.none,
                enabledBorder: InputBorder.none,
                focusedBorder: InputBorder.none,
                errorBorder: InputBorder.none,
                focusedErrorBorder: InputBorder.none,
                errorStyle: TextStyle(fontSize: 11),
              ),
            ),
          ),
          if (trailing != null) trailing! else SizedBox(width: 10),
        ],
      ),
    ),
  );
}
