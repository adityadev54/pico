import 'dart:ui';
import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

/// Shared centered dialog route with typed results and keyboard-aware bounds.
Future<T?> showPicoDialog<T>({
  required BuildContext context,
  required WidgetBuilder builder,
  bool isScrollControlled = false,
  bool isDismissible = true,
  bool structured = false,
}) {
  return showGeneralDialog<T>(
    context: context,
    barrierDismissible: isDismissible,
    barrierLabel: MaterialLocalizations.of(context).modalBarrierDismissLabel,
    barrierColor: Color(0x55000000),
    transitionDuration: Duration(milliseconds: 220),
    transitionBuilder: (context, animation, secondaryAnimation, child) {
      if (MediaQuery.disableAnimationsOf(context)) return child;
      final curved = CurvedAnimation(
        parent: animation,
        curve: Curves.easeOutCubic,
        reverseCurve: Curves.easeInCubic,
      );
      return FadeTransition(
        opacity: curved,
        child: ScaleTransition(
          scale: Tween<double>(begin: 0.96, end: 1).animate(curved),
          child: child,
        ),
      );
    },
    pageBuilder: (dialogContext, animation, secondaryAnimation) {
      return SafeArea(
        child: Padding(
          padding: EdgeInsets.only(
            left: 12,
            right: 12,
            top: 12,
            bottom: 12 + MediaQuery.viewInsetsOf(dialogContext).bottom,
          ),
          child: LayoutBuilder(
            builder: (context, constraints) {
              return Center(
                child: MediaQuery.removeViewInsets(
                  context: context,
                  removeBottom: true,
                  child: Builder(
                    builder: (contentContext) {
                      final content = builder(contentContext);
                      if (structured || content is PicoDialog) {
                        return content;
                      }
                      return PicoDialog(
                        contentPadding: EdgeInsets.zero,
                        content: isScrollControlled
                            ? SizedBox(
                                height: constraints.maxHeight * 0.85,
                                child: content,
                              )
                            : SingleChildScrollView(child: content),
                      );
                    },
                  ),
                ),
              );
            },
          ),
        ),
      );
    },
  );
}

/// One dialog surface for confirmations, input forms, time and scrollable detail.
/// The route owns viewport/keyboard bounds; content owns its internal layout.
class PicoDialog extends StatelessWidget {
  const PicoDialog({
    super.key,
    this.title,
    this.content,
    this.actions = const [],
    this.icon,
    this.contentPadding = const EdgeInsets.all(12),
    this.maxWidth = 340,
  });

  final double maxWidth;
  final Widget? title;
  final Widget? content;
  final List<Widget> actions;
  final IconData? icon;
  final EdgeInsetsGeometry contentPadding;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final dark = theme.brightness == Brightness.dark;
    final solid = MediaQuery.highContrastOf(context);
    return ConstrainedBox(
      constraints: BoxConstraints(maxWidth: maxWidth),
      child: DecoratedBox(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(34),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.18),
              blurRadius: 40,
              offset: Offset(0, 14),
            ),
          ],
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(34),
          child: BackdropFilter(
            filter: ImageFilter.blur(
              sigmaX: solid ? 0 : 30,
              sigmaY: solid ? 0 : 30,
            ),
            child: Material(
              color: theme.colorScheme.surface.withValues(
                alpha: solid ? 1 : 0.9,
              ),
              child: Container(
                width: double.infinity,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(34),
                  border: Border.all(
                    color: Colors.white.withValues(alpha: dark ? 0.16 : 0.65),
                  ),
                ),
                child: title == null && actions.isEmpty
                    ? Padding(padding: contentPadding, child: content)
                    : Column(
                        mainAxisSize: MainAxisSize.min,
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Flexible(
                            fit: FlexFit.loose,
                            child: SingleChildScrollView(
                              primary: false,
                              child: Padding(
                                padding: contentPadding,
                                child: Column(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    if (icon != null) ...[
                                      Icon(
                                        icon,
                                        size: 24,
                                        color: PicoTheme.accent,
                                      ),
                                      SizedBox(height: 12),
                                    ],
                                    if (title != null) ...[
                                      DefaultTextStyle(
                                        textAlign: TextAlign.center,
                                        style: theme.textTheme.titleMedium!
                                            .copyWith(
                                              fontWeight: FontWeight.w700,
                                            ),
                                        child: title!,
                                      ),
                                      SizedBox(height: 12),
                                    ],
                                    if (content != null)
                                      DefaultTextStyle(
                                        textAlign: TextAlign.center,
                                        style: theme.textTheme.bodyMedium!
                                            .copyWith(
                                              height: 1.35,
                                              color: Theme.of(context)
                                                  .colorScheme
                                                  .onSurfaceVariant,
                                            ),
                                        child: content!,
                                      ),
                                  ],
                                ),
                              ),
                            ),
                          ),
                          if (actions.isNotEmpty)
                            Padding(
                              padding: EdgeInsets.fromLTRB(12, 0, 12, 12),
                              child: IntrinsicHeight(
                                child: Row(
                                  crossAxisAlignment:
                                      CrossAxisAlignment.stretch,
                                  children: [
                                    for (
                                      var i = 0;
                                      i < actions.length;
                                      i++
                                    ) ...[
                                      if (i > 0) SizedBox(width: 12),
                                      Expanded(child: actions[i]),
                                    ],
                                  ],
                                ),
                              ),
                            ),
                        ],
                      ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Compact alert action shared by confirmations and other dialog flows.
class PicoDialogAction extends StatelessWidget {
  const PicoDialogAction({
    super.key,
    required this.label,
    required this.onPressed,
    this.primary = false,
    this.destructive = false,
  });
  final String label;
  final VoidCallback? onPressed;
  final bool primary;
  final bool destructive;
  @override
  Widget build(BuildContext context) => SizedBox(
    width: double.infinity,
    child: TextButton(
      style: TextButton.styleFrom(
        minimumSize: const Size(0, 48),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
        shape: const StadiumBorder(),
        backgroundColor: primary
            ? PicoTheme.accent
            : Theme.of(context).colorScheme.onSurface.withValues(alpha: .06),
        foregroundColor: primary
            ? Colors.white
            : destructive
            ? Theme.of(context).colorScheme.error
            : Theme.of(context).colorScheme.onSurface,
        textStyle: const TextStyle(
          fontFamily: 'DM Sans',
          fontSize: 15,
          fontWeight: FontWeight.w600,
        ),
      ),
      onPressed: onPressed,
      child: Text(label, textAlign: TextAlign.center),
    ),
  );
}
