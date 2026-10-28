import 'package:flutter/material.dart';
import 'package:heroicons/heroicons.dart';
import '../services/pico_store.dart';
import 'character_ground.dart';
import 'screen_chrome.dart';
import 'pico_sheet.dart';

Future<void> showCharacterPicker(BuildContext context, PicoStore store) =>
    showPicoSheet<void>(
      context: context,
      builder: (context) => CharacterPicker(
        initial: store.character,
        onSelect: store.chooseCharacter,
      ),
    );

class CharacterPicker extends StatefulWidget {
  const CharacterPicker({
    super.key,
    required this.initial,
    required this.onSelect,
  });
  final String initial;
  final ValueChanged<String> onSelect;
  @override
  State<CharacterPicker> createState() => _CharacterPickerState();
}

class _CharacterPickerState extends State<CharacterPicker> {
  static const _ids = ['tuck', 'mica'];
  late final int _initialPage = _ids
      .indexOf(widget.initial)
      .clamp(0, _ids.length - 1);
  late final PageController _pages = PageController(
    initialPage: _initialPage,
    viewportFraction: .34,
  );
  late int _page = _initialPage;
  @override
  void dispose() {
    _pages.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Column(
    mainAxisSize: MainAxisSize.min,
    children: [
      Row(
        children: [
          Expanded(
            child: Text(
              'Choose an agent',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.w600,
                letterSpacing: -.5,
              ),
            ),
          ),
          CircleControl(
            icon: HeroIcons.xMark,
            label: 'Close',
            onTap: () => Navigator.pop(context),
          ),
        ],
      ),
      SizedBox(height: 10),
      SizedBox(
        height: 210,
        child: PageView.builder(
          controller: _pages,
          itemCount: _ids.length,
          onPageChanged: (index) {
            setState(() => _page = index);
            widget.onSelect(_ids[index]);
          },
          itemBuilder: (context, index) => AnimatedBuilder(
            animation: _pages,
            builder: (context, _) {
              final current =
                  _pages.hasClients && _pages.position.hasContentDimensions
                  ? _pages.page!
                  : _page.toDouble();
              final distance = (current - index).abs().clamp(0.0, 1.0);
              final id = _ids[index];
              return Semantics(
                label: '${id[0].toUpperCase()}${id.substring(1)}',
                selected: index == _page,
                child: GestureDetector(
                  behavior: HitTestBehavior.opaque,
                  onTap: () => _pages.animateToPage(
                    index,
                    duration: Duration(
                      milliseconds: MediaQuery.disableAnimationsOf(context)
                          ? 0
                          : 250,
                    ),
                    curve: Curves.easeOutCubic,
                  ),
                  child: Opacity(
                    opacity: 1 - distance * .67,
                    child: Transform.scale(
                      scale: 1.12 - distance * .3,
                      child: Stack(
                        alignment: Alignment.bottomCenter,
                        children: [
                          if (distance < .5)
                            Positioned.fill(child: CharacterGround()),
                          Padding(
                            padding: EdgeInsets.only(bottom: 28),
                            child: Image.asset(
                              'assets/characters/$id/idle.${MediaQuery.disableAnimationsOf(context) ? 'png' : 'gif'}',
                              width: 170,
                              height: 170,
                              alignment: Alignment.bottomCenter,
                              gaplessPlayback: true,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              );
            },
          ),
        ),
      ),
      Text(
        '${_ids[_page][0].toUpperCase()}${_ids[_page].substring(1)}',
        style: TextStyle(
          fontSize: 16,
          color: Theme.of(context).colorScheme.onSurface,
        ),
      ),
      SizedBox(height: 14),
    ],
  );
}
