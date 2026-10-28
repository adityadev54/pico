import 'package:flutter/material.dart';
import 'pico_dialog.dart';

Future<T?> showPicoSheet<T>({
  required BuildContext context,
  required WidgetBuilder builder,
}) => showGeneralDialog<T>(
  context: context,
  barrierDismissible: true,
  barrierLabel: MaterialLocalizations.of(context).modalBarrierDismissLabel,
  barrierColor: const Color(0x55000000),
  transitionDuration: const Duration(milliseconds: 260),
  transitionBuilder: (context, animation, secondary, child) {
    if (MediaQuery.disableAnimationsOf(context)) return child;
    final curve = CurvedAnimation(
      parent: animation,
      curve: Curves.easeOutCubic,
    );
    return FadeTransition(
      opacity: curve,
      child: SlideTransition(
        position: Tween(
          begin: const Offset(0, .15),
          end: Offset.zero,
        ).animate(curve),
        child: child,
      ),
    );
  },
  pageBuilder: (context, animation, secondary) => SafeArea(
    child: Padding(
      padding: EdgeInsets.fromLTRB(
        12,
        12,
        12,
        12 + MediaQuery.viewInsetsOf(context).bottom,
      ),
      child: Align(
        alignment: Alignment.bottomCenter,
        child: PicoDialog(
          maxWidth: 500,
          contentPadding: const EdgeInsets.all(16),
          content: SingleChildScrollView(child: builder(context)),
        ),
      ),
    ),
  ),
);
