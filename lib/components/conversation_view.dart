import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter/semantics.dart';
import 'package:heroicons/heroicons.dart';
import '../models/place.dart';
import 'package:kin_ui/kin_ui.dart';
import '../services/pico_store.dart';
import 'screen_chrome.dart';
import 'chat_bubble_shape.dart';
import 'message_frame.dart';
import 'agent_message.dart';
import 'place_empty_state.dart';
import 'task_bubble.dart';

class ConversationView extends StatelessWidget {
  const ConversationView({
    super.key,
    required this.store,
    required this.controller,
    required this.onDevices,
    required this.onCompose,
    this.typing = false,
    this.onVoice,
  });
  final PicoStore store;
  final ScrollController controller;
  final VoidCallback onDevices, onCompose;
  final VoidCallback? onVoice;
  final bool typing;
  @override
  Widget build(BuildContext context) =>
      store.places.isEmpty && store.tasks.isEmpty
      ? SafeArea(
          bottom: false,
          child: Padding(
            padding: EdgeInsets.fromLTRB(12, 76, 12, typing ? 100 : 24),
            child: Center(
              child: ConstrainedBox(
                constraints: BoxConstraints(maxWidth: 680),
                child: Column(
                  children: [
                    if (!store.linked)
                      ComputerConnectionRow(
                        status: store.connection,
                        onTap: onDevices,
                      ),
                    SizedBox(height: 12),
                    if (store.pendingPlaceId != null)
                      Padding(
                        padding: EdgeInsets.only(bottom: 12),
                        child: TextButton.icon(
                          onPressed: onCompose,
                          icon: Icon(Icons.edit_note),
                          label: Text('What were you about to do?'),
                        ),
                      ),
                    Expanded(
                      child: PlaceEmptyState(
                        character: store.character,
                        mood: store.mood,
                        scale: store.characterScale,
                        typing: typing,
                        onCompose: onCompose,
                        onVoice: onVoice,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        )
      : EdgeFades(
          child: Center(
            child: ConstrainedBox(
              constraints: BoxConstraints(maxWidth: 680),
              child: ListView(
                controller: controller,
                padding: EdgeInsets.fromLTRB(
                  12,
                  MediaQuery.paddingOf(context).top + 100,
                  12,
                  300,
                ),
                children: [
                  if (!store.linked)
                    ComputerConnectionRow(
                      status: store.connection,
                      onTap: onDevices,
                    ),
                  const SizedBox(height: 12),
                  for (final task in store.tasks.take(5))
                    TaskBubble(
                      key: ValueKey(task['id']),
                      task: task,
                      store: store,
                    ),
                  for (final place in store.places.reversed.where(
                    (p) => store.selectedPlaceId == null
                        ? !p.finished
                        : p.id == store.selectedPlaceId,
                  ))
                    PlaceMessage(
                      key: ValueKey(place.id),
                      place: place,
                      store: store,
                    ),
                  if (store.places.isNotEmpty &&
                      store.places.every((p) => p.finished) &&
                      store.tasks.isEmpty)
                    const AgentMessage(text: 'All caught up.'),
                ],
              ),
            ),
          ),
        );
}

class PlaceMessage extends StatefulWidget {
  const PlaceMessage({super.key, required this.place, required this.store});
  final Place place;
  final PicoStore store;
  @override
  State<PlaceMessage> createState() => _PlaceMessageState();
}

class _PlaceMessageState extends State<PlaceMessage> {
  bool expanded = false;
  void menu(BuildContext anchor) {
    final box = anchor.findRenderObject()! as RenderBox;
    final overlay = Overlay.of(anchor).context.findRenderObject()! as RenderBox;
    final place = widget.place;
    Widget icon(HeroIcons value) => HeroIcon(
      value,
      size: 19,
      color: Theme.of(context).colorScheme.onSurface,
    );
    KinPopupMenu.show(
      context: context,
      position: RelativeRect.fromRect(
        box.localToGlobal(Offset.zero, ancestor: overlay) & box.size,
        Offset.zero & overlay.size,
      ),
      items: [
        KinPopupMenuItem(
          label: 'Copy',
          leading: icon(HeroIcons.documentDuplicate),
          onTap: () async {
            await Clipboard.setData(ClipboardData(text: place.sentence));
            if (mounted) {
              ScaffoldMessenger.of(
                context,
              ).showSnackBar(const SnackBar(content: Text('Sentence copied.')));
            }
          },
        ),
        if (!place.finished)
          KinPopupMenuItem(
            label: place.parked ? 'Unpark' : 'Park',
            leading: icon(
              place.parked ? HeroIcons.arrowUturnLeft : HeroIcons.archiveBox,
            ),
            onTap: () => widget.store.updatePlace(place, parked: !place.parked),
          ),
        if (!place.finished)
          KinPopupMenuItem(
            label: 'Done',
            leading: icon(HeroIcons.check),
            onTap: () => widget.store.updatePlace(place, finished: true),
          ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final place = widget.place;
    final colors = Theme.of(context).colorScheme;
    final status =
        '${place.parked
            ? 'Parked · '
            : place.finished
            ? 'Done · '
            : ''}${place.delivery == 'delivered'
            ? 'Delivered'
            : place.delivery == 'queued'
            ? 'Waiting for computer'
            : 'Saved here'}';
    final textStyle = TextStyle(
      fontSize: 16,
      height: 1.45,
      color: colors.onSurface,
    );
    final statusStyle = TextStyle(fontSize: 11, color: colors.onSurfaceVariant);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: MessageFrame(
            mine: true,
            text: place.sentence,
            style: textStyle,
            detail: status,
            detailStyle: statusStyle,
            child: Builder(
              builder: (anchor) => Semantics(
                label: 'Saved thought. Long press for options.',
                customSemanticsActions: {
                  const CustomSemanticsAction(label: 'Show options'): () =>
                      menu(anchor),
                },
                child: GestureDetector(
                  onLongPress: () => menu(anchor),
                  onSecondaryTap: () => menu(anchor),
                  child: Material(
                    color: colors.surface,
                    shape: const ChatBubbleShape(mine: true),
                    child: SizedBox(
                      width: double.infinity,
                      child: Padding(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 14,
                          vertical: 12,
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            LayoutBuilder(
                              builder: (context, constraints) {
                                final style = TextStyle(
                                  fontSize: 16,
                                  height: 1.45,
                                  color: colors.onSurface,
                                );
                                final measure = TextPainter(
                                  text: TextSpan(
                                    text: place.sentence,
                                    style: DefaultTextStyle.of(context).style
                                        .merge(style),
                                  ),
                                  maxLines: 6,
                                  textDirection: Directionality.of(context),
                                  textScaler: MediaQuery.textScalerOf(context),
                                )..layout(maxWidth: constraints.maxWidth);
                                return Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      place.sentence,
                                      maxLines: expanded ? null : 6,
                                      overflow: expanded
                                          ? TextOverflow.visible
                                          : TextOverflow.ellipsis,
                                      style: style,
                                    ),
                                    if (measure.didExceedMaxLines)
                                      TextButton(
                                        style: TextButton.styleFrom(
                                          padding: EdgeInsets.zero,
                                          minimumSize: const Size(48, 48),
                                          alignment: Alignment.centerLeft,
                                        ),
                                        onPressed: () => setState(
                                          () => expanded = !expanded,
                                        ),
                                        child: Text(
                                          expanded ? 'Show less' : 'Show more',
                                        ),
                                      ),
                                  ],
                                );
                              },
                            ),
                            const SizedBox(height: 8),
                            Text(status, style: statusStyle),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
        if (place.headStart != null) AgentMessage(text: place.headStart!),
      ],
    );
  }
}
