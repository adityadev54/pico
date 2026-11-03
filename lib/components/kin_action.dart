import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:kin_ui/kin_ui.dart';

/// Kin button with wrapping labels, keyboard activation and explicit semantics.
class KinAction extends StatefulWidget {
  const KinAction({
    super.key,
    required this.label,
    this.onTap,
    this.leading,
    this.variant = KinButtonVariant.primary,
  });
  final String label;
  final VoidCallback? onTap;
  final Widget? leading;
  final KinButtonVariant variant;
  @override
  State<KinAction> createState() => _KinActionState();
}

class _KinActionState extends State<KinAction> {
  bool focus = false;
  @override
  Widget build(BuildContext context) => Semantics(
    button: true,
    enabled: widget.onTap != null,
    label: widget.label,
    onTap: widget.onTap,
    excludeSemantics: true,
    child: FocusableActionDetector(
      enabled: widget.onTap != null,
      shortcuts: const {
        SingleActivator(LogicalKeyboardKey.enter): ActivateIntent(),
        SingleActivator(LogicalKeyboardKey.space): ActivateIntent(),
      },
      actions: {
        ActivateIntent: CallbackAction<ActivateIntent>(
          onInvoke: (_) {
            widget.onTap?.call();
            return null;
          },
        ),
      },
      onShowFocusHighlight: (value) => setState(() => focus = value),
      child: Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(40),
          border: Border.all(
            color: focus
                ? Theme.of(context).colorScheme.primary
                : Colors.transparent,
          ),
        ),
        constraints: const BoxConstraints(minHeight: 48),
        child: KinButton(
          onTap: widget.onTap,
          enabled: widget.onTap != null,
          variant: widget.variant,
          leading: widget.leading,
          child: Flexible(
            child: Text(
              widget.label,
              textAlign: TextAlign.center,
              style: TextStyle(
                color: widget.variant == KinButtonVariant.primary
                    ? Colors.white
                    : Theme.of(context).colorScheme.primary,
              ),
            ),
          ),
        ),
      ),
    ),
  );
}
