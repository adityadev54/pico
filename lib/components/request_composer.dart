import 'package:flutter/material.dart';
import 'package:heroicons/heroicons.dart';

import 'capsule_input.dart';

import 'package:kin_ui/kin_ui.dart';

class RequestComposer extends StatelessWidget {
  const RequestComposer({
    super.key,
    required this.controller,
    required this.listening,
    required this.busy,
    required this.onVoice,
    required this.onSend,
    this.onCamera,
    this.onRoutines,
    this.autofocus = true,
    this.focusNode,
  });
  final TextEditingController controller;
  final FocusNode? focusNode;
  final bool listening, busy, autofocus;
  final VoidCallback onVoice, onSend;
  final VoidCallback? onCamera, onRoutines;
  @override
  Widget build(BuildContext context) => Padding(
    padding: EdgeInsets.fromLTRB(12, 12, 12, 12),
    child: CapsuleInput(
      controller: controller,
      focusNode: focusNode,
      hint: listening ? 'Listening…' : 'Ask or save a thought…',
      icon: HeroIcons.microphone,
      leading: Builder(
        builder: (anchor) => IconButton(
          tooltip: 'Add',
          icon: const HeroIcon(HeroIcons.plus, size: 21),
          onPressed: () {
            final box = anchor.findRenderObject()! as RenderBox;
            final overlay =
                Overlay.of(anchor).context.findRenderObject()! as RenderBox;
            final items = <KinPopupMenuItem>[
              KinPopupMenuItem(
                label: 'Microphone',
                leading: const HeroIcon(HeroIcons.microphone, size: 20),
                onTap: onVoice,
              ),
              if (onCamera != null)
                KinPopupMenuItem(
                  label: 'Camera',
                  leading: const HeroIcon(HeroIcons.camera, size: 20),
                  onTap: onCamera,
                ),
              if (onRoutines != null)
                KinPopupMenuItem(
                  label: 'Watch & repeat',
                  leading: const HeroIcon(HeroIcons.arrowPath, size: 20),
                  onTap: onRoutines,
                ),
            ];
            // Kin positions from the menu's top; measure its rows so its
            // bottom tracks the actual + button, including larger text.
            var width = 160.0;
            var height = 2 * KinSpacing.sm;
            for (final item in items) {
              final text = TextPainter(
                text: TextSpan(
                  text: item.label,
                  style: KinTypography.bodyMedium,
                ),
                textDirection: Directionality.of(context),
                textScaler: MediaQuery.textScalerOf(context),
              )..layout();
              final rowHeight = text.height > 20 ? text.height : 20.0;
              height += rowHeight + 2 * (KinSpacing.sm + 2);
              final rowWidth =
                  text.width +
                  20 +
                  (KinSpacing.sm + 2) +
                  2 * (KinSpacing.sm + 2) +
                  4 * KinSpacing.xs;
              if (rowWidth > width) width = rowWidth;
              text.dispose();
            }
            final origin = box.localToGlobal(Offset.zero, ancestor: overlay);
            KinPopupMenu.show(
              context: context,
              position: RelativeRect.fromLTRB(
                origin.dx,
                0,
                overlay.size.width - origin.dx - width,
                overlay.size.height - origin.dy + height + 6,
              ),
              items: items,
            );
          },
        ),
      ),
      autofocus: autofocus,
      maxLines: 4,
      inputAction: TextInputAction.send,
      onSubmitted: (_) => onSend(),
      trailing: IconButton(
        tooltip: 'Send',
        onPressed: busy ? null : onSend,
        icon: HeroIcon(
          HeroIcons.arrowUpCircle,
          size: 27,
          color: busy
              ? Theme.of(context).colorScheme.onSurfaceVariant
              : Theme.of(context).colorScheme.primary,
        ),
      ),
    ),
  );
}
