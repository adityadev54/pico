import 'package:flutter/material.dart';
import 'package:heroicons/heroicons.dart';

import '../components/character_picker.dart';
import '../components/floating_surface.dart';
import '../components/screen_chrome.dart';
import '../components/section_group.dart';
import '../models/place.dart';
import '../services/pico_store.dart';

class SearchScreen extends StatefulWidget {
  const SearchScreen({super.key, required this.store});
  final PicoStore store;
  @override
  State<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends State<SearchScreen> {
  final controller = TextEditingController();
  String get query => controller.text.trim();

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  Future<void> _openChat(Place place) async {
    await widget.store.rememberSearch(query);
    if (!mounted) return;
    widget.store.selectPlace(place);
    Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) => ListenableBuilder(
    listenable: widget.store,
    builder: (context, _) {
      final store = widget.store;
      final term = query.toLowerCase();
      final chats = store.places
          .where((p) => p.sentence.toLowerCase().contains(term))
          .toList();
      final agents = ['Tuck', 'Mica']
          .where((name) => '$name agent companion'.toLowerCase().contains(term))
          .toList();
      final seen = <String>{};
      final recent = store.activities
          .where((a) {
            if (a.target.startsWith('place:')) {
              if (!store.places.any((p) => 'place:${p.id}' == a.target)) {
                return false;
              }
            } else if (a.target != 'character' &&
                !a.target.startsWith('search:')) {
              return false;
            }
            return seen.add(a.target);
          })
          .take(5)
          .toList();
      return Scaffold(
        body: Stack(
          children: [
            Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 680),
                child: ListView(
                  padding: EdgeInsets.fromLTRB(
                    12,
                    MediaQuery.paddingOf(context).top + 90,
                    12,
                    30,
                  ),
                  children: [
                    FloatingSurface(
                      child: TextField(
                        controller: controller,
                        autofocus: true,
                        textInputAction: TextInputAction.search,
                        onChanged: (_) => setState(() {}),
                        onSubmitted: store.rememberSearch,
                        decoration: const InputDecoration(
                          hintText: 'Search chats and agents',
                        ),
                      ),
                    ),
                    const SizedBox(height: 12),
                    if (query.isNotEmpty) ...[
                      if (chats.isNotEmpty)
                        SectionGroup(
                          title: 'Chats',
                          children: [
                            for (final chat in chats)
                              SettingsRow(
                                icon: HeroIcons.chatBubbleLeft,
                                title: chat.sentence,
                                onTap: () => _openChat(chat),
                              ),
                          ],
                        ),
                      if (agents.isNotEmpty)
                        SectionGroup(
                          title: 'Agents',
                          children: [
                            for (final agent in agents)
                              SettingsRow(
                                icon: HeroIcons.faceSmile,
                                title: agent,
                                onTap: () async {
                                  await store.rememberSearch(query);
                                  if (!context.mounted) return;
                                  showCharacterPicker(context, store);
                                },
                              ),
                          ],
                        ),
                      if (chats.isEmpty && agents.isEmpty)
                        const Padding(
                          padding: EdgeInsets.all(12),
                          child: Text('No chats or agents found.'),
                        ),
                    ],
                    SectionGroup(
                      title: 'Recent activity',
                      children: [
                        if (recent.isEmpty)
                          const Padding(
                            padding: EdgeInsets.all(12),
                            child: Text('Nothing recent yet.'),
                          ),
                        for (final activity in recent)
                          SettingsRow(
                            icon: activity.target.startsWith('search:')
                                ? HeroIcons.magnifyingGlass
                                : activity.target == 'character'
                                ? HeroIcons.faceSmile
                                : HeroIcons.chatBubbleLeft,
                            title: activity.target.startsWith('place:')
                                ? activity.detail
                                : activity.title,
                            subtitle: activity.target.startsWith('place:')
                                ? 'Chat'
                                : activity.detail,
                            onTap: () {
                              if (activity.target.startsWith('place:')) {
                                final chat = store.places.firstWhere(
                                  (p) => 'place:${p.id}' == activity.target,
                                );
                                store.selectPlace(chat);
                                Navigator.pop(context);
                              } else if (activity.target == 'character') {
                                showCharacterPicker(context, store);
                              } else {
                                setState(() {
                                  controller.text = activity.target.substring(
                                    7,
                                  );
                                  controller.selection =
                                      TextSelection.collapsed(
                                        offset: controller.text.length,
                                      );
                                });
                              }
                            },
                          ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            ScreenToolbar(onBack: () => Navigator.pop(context)),
          ],
        ),
      );
    },
  );
}
