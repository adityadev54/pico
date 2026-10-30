import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter/semantics.dart';
import 'package:heroicons/heroicons.dart';

import '../models/session.dart';
import 'floating_surface.dart';
import 'chat_bubble_shape.dart';

const reactionIcons = {
  'heart': HeroIcons.heart,
  'like': HeroIcons.handThumbUp,
  'dislike': HeroIcons.handThumbDown,
  'friendly': HeroIcons.faceSmile,
};

class ChatBubble extends StatelessWidget {
  const ChatBubble({super.key, required this.turn, this.onReaction});
  final Turn turn;
  final ValueChanged<String>? onReaction;

  void _openReactions(BuildContext context) {
    final box = context.findRenderObject() as RenderBox;
    _reactions(context, box.localToGlobal(Offset(box.size.width / 2, 0)));
  }

  Future<void> _reactions(BuildContext context, Offset point) async {
    HapticFeedback.selectionClick();
    final size = MediaQuery.sizeOf(context);
    final reaction = await showGeneralDialog<String>(
      context: context,
      barrierDismissible: true,
      barrierLabel: 'close reactions',
      barrierColor: Colors.black.withValues(alpha: .08),
      transitionDuration: Duration(milliseconds: 120),
      pageBuilder: (context, _, _) => Material(
        color: Colors.transparent,
        child: Stack(
          children: [
            Positioned(
              left: (point.dx - 112).clamp(12.0, size.width - 236),
              top: (point.dy - 72).clamp(
                MediaQuery.paddingOf(context).top + 12,
                size.height - 100,
              ),
              child: Material(
                color: Colors.transparent,
                child: FloatingSurface(
                  child: Padding(
                    padding: EdgeInsets.all(4),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        for (final entry in reactionIcons.entries)
                          IconButton(
                            tooltip: entry.key,
                            onPressed: () => Navigator.pop(context, entry.key),
                            icon: HeroIcon(
                              entry.value,
                              size: 23,
                              style: turn.reaction == entry.key
                                  ? HeroIconStyle.solid
                                  : HeroIconStyle.outline,
                              color: Theme.of(context).colorScheme.primary,
                            ),
                          ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
    if (reaction != null) onReaction?.call(reaction);
  }

  @override
  Widget build(BuildContext context) {
    final mine = turn.role == 'user';
    return Align(
      alignment: mine ? Alignment.centerRight : Alignment.centerLeft,
      child: Padding(
        padding: EdgeInsets.only(bottom: 16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: mine
              ? CrossAxisAlignment.end
              : CrossAxisAlignment.start,
          children: [
            GestureDetector(
              behavior: HitTestBehavior.opaque,
              onLongPress: onReaction == null
                  ? null
                  : () => _openReactions(context),
              onSecondaryTapUp: onReaction == null
                  ? null
                  : (event) => _reactions(context, event.globalPosition),
              child: Semantics(
                hint: onReaction == null ? null : 'long press to react',
                customSemanticsActions: onReaction == null
                    ? null
                    : {
                        CustomSemanticsAction(label: 'React'): () =>
                            _openReactions(context),
                      },
                child: Container(
                  constraints: BoxConstraints(
                    maxWidth:
                        MediaQuery.sizeOf(context).width.clamp(0, 600) * .84,
                  ),
                  padding: EdgeInsets.symmetric(horizontal: 21, vertical: 15),
                  decoration: ShapeDecoration(
                    color: mine
                        ? Theme.of(context).colorScheme.primaryContainer
                        : Theme.of(context).colorScheme.surface,
                    shape: ChatBubbleShape(mine: mine),
                  ),
                  child: Text(
                    turn.text,
                    style: TextStyle(fontSize: 15, height: 1.5),
                  ),
                ),
              ),
            ),
            if (turn.reaction != null &&
                reactionIcons.containsKey(turn.reaction))
              Padding(
                padding: EdgeInsets.only(top: 5, left: 8, right: 8),
                child: Semantics(
                  label: '${turn.reaction} reaction',
                  child: HeroIcon(
                    reactionIcons[turn.reaction]!,
                    size: 17,
                    color: Theme.of(context).colorScheme.primary,
                    style: HeroIconStyle.solid,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
