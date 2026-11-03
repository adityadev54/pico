import 'package:flutter/material.dart';
import 'package:heroicons/heroicons.dart';
import 'package:kin_ui/kin_ui.dart';

import '../services/pico_store.dart';
import 'companion_image.dart';
import 'kin_action.dart';

/// One inline flow for any taught file routine; no per-workflow routes or sheets.
class RoutineCards extends StatefulWidget {
  const RoutineCards({super.key, required this.store});
  final PicoStore store;
  @override
  State<RoutineCards> createState() => _RoutineCardsState();
}

class _RoutineCardsState extends State<RoutineCards> {
  String? selected;
  @override
  Widget build(BuildContext context) {
    final store = widget.store;
    final expanded = store.routineReviewId ?? selected;
    final waiting = store.routineRequest != null;
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: KinCard(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                CompanionImage(
                  character: store.character,
                  mood: store.mood,
                  size: 40,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Watch & repeat',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
                IconButton(
                  tooltip: 'Refresh routines',
                  onPressed: waiting ? null : () => store.requestRoutines(),
                  icon: const HeroIcon(HeroIcons.arrowPath, size: 19),
                ),
                IconButton(
                  tooltip: 'Close routines',
                  onPressed: store.hideRoutines,
                  icon: const HeroIcon(HeroIcons.xMark, size: 19),
                ),
              ],
            ),
            if (waiting)
              const Padding(
                padding: EdgeInsets.only(bottom: 12),
                child: LinearProgressIndicator(),
              ),
            if (store.routineMessage != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Text(store.routineMessage!),
              ),
            if (store.routines.isEmpty && !waiting)
              const Text(
                'Show Pico a result once on your computer. Repeat it here with the files you choose.',
              ),
            for (final routine in store.routines) ...[
              KinListTile(
                padding: const EdgeInsets.symmetric(vertical: 12),
                title: routine['name'] as String,
                subtitle: (routine['sources'] as List? ?? []).join(', '),
                trailing: HeroIcon(
                  expanded == routine['id']
                      ? HeroIcons.chevronUp
                      : HeroIcons.chevronDown,
                  size: 19,
                ),
                onTap: waiting
                    ? null
                    : () => setState(() {
                        selected = expanded == routine['id']
                            ? null
                            : routine['id'] as String;
                        store.routineReviewId = null;
                      }),
              ),
              if (expanded == routine['id']) ...[
                const Text(
                  'Pico will send the current contents of these files to Muse, then save a new result on your computer. Uses your account limits.',
                ),
                const SizedBox(height: 12),
                KinAction(
                  onTap: waiting
                      ? null
                      : () => store.requestRoutines(
                          routine: routine['id'] as String,
                        ),
                  label: 'Run with these files',
                ),
                const SizedBox(height: 12),
              ],
            ],
            KinAction(
              variant: KinButtonVariant.ghost,
              onTap: waiting ? null : () => store.requestRoutines(teach: true),
              leading: const HeroIcon(HeroIcons.plus, size: 18),
              label: 'Teach on my computer',
            ),
          ],
        ),
      ),
    );
  }
}
