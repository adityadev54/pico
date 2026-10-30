import '../components/session_drawer.dart';
import '../components/conversation_view.dart';
import '../components/voice_status.dart';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:speech_to_text/speech_to_text.dart';

import '../components/character_stage.dart';
import '../components/computer_actions.dart';
import '../components/home_controls.dart';
import '../components/request_composer.dart';
import '../services/command_parser.dart';
import '../services/pico_store.dart';
import '../theme/app_theme.dart';
import 'settings_screen.dart';
import 'search_screen.dart';
import 'devices_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key, required this.store});
  final PicoStore store;
  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> with WidgetsBindingObserver {
  bool _drawer = false;
  bool _typing = false;
  bool _voiceSending = false;
  bool _startingVoice = false;
  bool _voiceSubmitted = false;
  String _heard = '';
  double _soundLevel = 0;
  int _voiceGeneration = 0;
  final _text = TextEditingController();
  final _composerFocus = FocusNode();
  final _speech = SpeechToText();
  final _scroll = ScrollController();
  PicoStore get store => widget.store;
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _text.addListener(_dismissStaleError);
    store.addListener(_followConversation);
  }

  String? _shownChat;
  void _followConversation() {
    final switched = _shownChat != store.current?.id;
    _shownChat = store.current?.id;
    final follow =
        switched || !_scroll.hasClients || _scroll.position.extentAfter < 100;
    if (!follow) return;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted && _scroll.hasClients) {
        _scroll.jumpTo(_scroll.position.maxScrollExtent);
      }
    });
  }

  // Old send errors linger above the input until the next attempt;
  // typing something new dismisses them so they can't be mistaken
  // for a fresh failure.
  void _dismissStaleError() {
    if (store.error != null) store.clearError();
  }

  @override
  void didChangeMetrics() {
    if (_typing) _followConversation();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    store.removeListener(_followConversation);
    _text.removeListener(_dismissStaleError);
    _text.dispose();
    _composerFocus.dispose();
    _scroll.dispose();
    _speech.cancel();
    super.dispose();
  }

  void _open(Widget screen) {
    setState(() => _drawer = false);
    Navigator.push(context, MaterialPageRoute<void>(builder: (_) => screen));
  }

  void _compose() {
    if (!_typing) {
      ++_voiceGeneration;
      _speech.cancel();
      _heard = '';
    }
    setState(() => _typing = !_typing);
    if (_typing) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _composerFocus.requestFocus();
      });
    } else {
      _composerFocus.unfocus();
    }
  }

  Future<void> _voice() async {
    if (store.busy || _voiceSending || _startingVoice) return;
    if (_speech.isListening) {
      await _speech.stop();
      return;
    }
    _startingVoice = true;
    final generation = ++_voiceGeneration;
    try {
      final available = await _speech.initialize(
        onStatus: (status) {
          if (mounted &&
              (status == 'done' || status == 'notListening') &&
              !_voiceSending &&
              store.mood == 'listening') {
            store.setMood('idle');
          }
        },
        onError: (_) {
          if (mounted) {
            store.setMood('stuck');
            setState(() => _heard = '');
            _notice('Couldn’t hear that. Double tap to try again.');
          }
        },
      );
      if (!mounted) return;
      if (!available) {
        _notice('Allow microphone and speech access in your device settings.');
        return;
      }
      _composerFocus.unfocus();
      setState(() {
        _typing = false;
        _heard = '';
        _voiceSubmitted = false;
      });
      store.setMood('listening');
      await _speech.listen(
        onSoundLevelChange: (level) {
          if (mounted) {
            setState(() => _soundLevel = ((level + 2) / 12).clamp(0, 1));
          }
        },
        listenOptions: SpeechListenOptions(
          listenFor: Duration(seconds: 45),
          pauseFor: Duration(seconds: 3),
          partialResults: true,
          cancelOnError: true,
          listenMode: ListenMode.confirmation,
        ),
        onResult: (result) async {
          if (!mounted || generation != _voiceGeneration || _voiceSubmitted) {
            return;
          }
          setState(() => _heard = result.recognizedWords);
          if (result.finalResult && result.recognizedWords.trim().isNotEmpty) {
            _voiceSubmitted = true;
            setState(() => _voiceSending = true);
            try {
              await _dispatch(result.recognizedWords);
            } finally {
              if (mounted) {
                setState(() {
                  _voiceSending = false;
                  _heard = '';
                });
              }
            }
          }
        },
      );
    } catch (_) {
      if (mounted) {
        store.setMood('stuck');
        _notice('Voice is unavailable. Tap the type icon to write instead.');
      }
    } finally {
      _startingVoice = false;
    }
  }

  Future<bool> _dispatch(String value) async {
    // Supported computer actions run as tasks; other speech stays a Place.
    if (store.linked && await dispatchComputerAction(context, store, value)) {
      if (!mounted) return false;
    } else {
      if (looksLikeCommand(value)) {
        _notice(
          store.linked
              ? 'Action not started. For a file, try “Create a file called test.txt saying Hello”. For a draft, use “Ask Pico: Draft a three-item checklist into checklist.txt”.'
              : 'Action not started. Connect a computer in Devices first.',
        );
        return false;
      }
      await store.savePlace(value);
      if (!mounted) return false;
    }
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted && _scroll.hasClients) {
        _scroll.animateTo(
          _scroll.position.maxScrollExtent,
          duration: Duration(milliseconds: 250),
          curve: Curves.easeOut,
        );
      }
    });
    return store.error == null;
  }

  void _notice(String text) =>
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));
  Future<void> _send() async {
    final value = _text.text;
    if (value.trim().isEmpty || store.busy) return;
    await _speech.stop();
    final sent = await _dispatch(value);
    if (!mounted) return;
    if (sent) _text.clear();
    if (_scroll.hasClients) {
      _scroll.animateTo(
        _scroll.position.maxScrollExtent,
        duration: Duration(milliseconds: 250),
        curve: Curves.easeOut,
      );
    }
  }

  @override
  Widget build(BuildContext context) => ListenableBuilder(
    listenable: store,
    builder: (context, _) {
      final width = MediaQuery.sizeOf(context).width;
      final slide = (width * .75).clamp(0.0, 320.0);
      return AnnotatedRegion<SystemUiOverlayStyle>(
        value: _drawer || Theme.of(context).brightness == Brightness.dark
            ? SystemUiOverlayStyle.light
            : SystemUiOverlayStyle.dark,
        child: PopScope(
          canPop: !_drawer,
          onPopInvokedWithResult: (didPop, _) {
            if (!didPop) setState(() => _drawer = false);
          },
          child: Scaffold(
            resizeToAvoidBottomInset: false,
            backgroundColor: _drawer
                ? PicoTheme.drawer
                : Theme.of(context).scaffoldBackgroundColor,
            body: Stack(
              children: [
                SessionDrawer(
                  store: store,
                  width: slide,
                  onClose: () => setState(() => _drawer = false),
                  onNewChat: () {
                    ++_voiceGeneration;
                    _speech.cancel();
                    _text.clear();
                    setState(() {
                      _drawer = false;
                      _typing = true;
                      _heard = '';
                    });
                    WidgetsBinding.instance.addPostFrameCallback((_) {
                      if (mounted) _composerFocus.requestFocus();
                    });
                  },
                  onSettings: () => _open(SettingsScreen(store: store)),
                ),
                AnimatedContainer(
                  duration: Duration(
                    milliseconds: MediaQuery.disableAnimationsOf(context)
                        ? 0
                        : 280,
                  ),
                  curve: Curves.easeOutCubic,
                  transform: Matrix4.identity()
                    ..translateByDouble(_drawer ? slide : 0, 0, 0, 1)
                    ..scaleByDouble(_drawer ? .88 : 1, _drawer ? .88 : 1, 1, 1),
                  transformAlignment: Alignment.centerLeft,
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(_drawer ? 28 : 0),
                    child: Stack(
                      children: [
                        Scaffold(
                          resizeToAvoidBottomInset: true,
                          body: Stack(
                            children: [
                              ConversationView(
                                store: store,
                                controller: _scroll,
                                typing: _typing,
                                onCompose: _compose,
                                onVoice: _voice,
                                onDevices: () =>
                                    _open(DevicesScreen(store: store)),
                              ),
                              HomeControls(
                                store: store,
                                onMenu: () {
                                  FocusManager.instance.primaryFocus?.unfocus();
                                  setState(() => _drawer = true);
                                },
                                onType: _compose,
                                onSearch: () =>
                                    _open(SearchScreen(store: store)),
                              ),
                              Align(
                                alignment: Alignment.bottomCenter,
                                child: SafeArea(
                                  top: false,
                                  child: ConstrainedBox(
                                    constraints: BoxConstraints(maxWidth: 680),
                                    child: Column(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        if (!_typing &&
                                            store.visiblePlaces.isNotEmpty)
                                          SizedBox(
                                            height: store.linked
                                                ? 105 * store.characterScale
                                                : 188 * store.characterScale,
                                            child: FittedBox(
                                              child: CharacterStage(
                                                character: store.character,
                                                mood: store.mood,
                                                onVoice: _voice,
                                                onReports: () => _open(
                                                  SearchScreen(store: store),
                                                ),
                                                onHandoff: () => _open(
                                                  DevicesScreen(
                                                    store: store,
                                                    handoff: true,
                                                  ),
                                                ),
                                              ),
                                            ),
                                          ),
                                        if (!_typing &&
                                            (store.mood == 'listening' ||
                                                _voiceSending ||
                                                _heard.isNotEmpty))
                                          VoiceStatus(
                                            level: _soundLevel,
                                            text: _heard,
                                            listening:
                                                store.mood == 'listening',
                                            onStop: () async {
                                              if (_speech.isListening) {
                                                await _speech.stop();
                                              } else {
                                                setState(() => _heard = '');
                                              }
                                            },
                                          ),
                                        if (_typing)
                                          RequestComposer(
                                            autofocus: _typing,
                                            focusNode: _composerFocus,
                                            controller: _text,
                                            listening:
                                                store.mood == 'listening',
                                            busy: store.busy,
                                            onVoice: _voice,
                                            onSend: _send,
                                          ),
                                      ],
                                    ),
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                        if (_drawer)
                          Positioned.fill(
                            child: GestureDetector(
                              onTap: () => setState(() => _drawer = false),
                              child: Container(
                                color: Colors.black.withValues(alpha: .12),
                              ),
                            ),
                          ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      );
    },
  );
}
