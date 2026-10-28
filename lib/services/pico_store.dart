import 'dart:async';
import 'dart:convert';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart' hide Session;

import '../models/place.dart';
import '../models/activity.dart';
import '../models/session.dart';
import 'relay_client.dart';

part 'pico_chat_store.dart';
part 'pico_connection_store.dart';
part 'pico_agent_store.dart';

class PicoStore extends ChangeNotifier {
  PicoStore(
    this.preferences, {
    SupabaseClient? accountClient,
    RelayClient? relay,
  }) : client = accountClient,
       relay = relay ?? RelayClient();
  final SharedPreferences preferences;
  final SupabaseClient? client;
  final RelayClient relay;
  final List<Place> places = [];
  final List<ActivityEntry> activities = [];
  final List<Session> sessions = [];
  final List<Map<String, dynamic>> tasks = [];
  List<Map<String, dynamic>> devices = [];
  Session? current;
  String? selectedPlaceId, error, pendingPlaceId;
  String character = 'tuck', mood = 'idle', characterSize = 'medium';
  bool darkMode = false, busy = false, recoveringPassword = false;
  bool _refreshing = false;
  String? _loadedUser, _sentCompanion;
  Future<void>? _companionSync;
  Timer? _timer, _moodTimer;
  StreamSubscription<AuthState>? _auth;
  bool get signedIn => userId != null;
  String? get userId => client?.auth.currentUser?.id;
  String? get _token => client?.auth.currentSession?.accessToken;
  bool get linked => devices.isNotEmpty;
  ThemeMode get themeMode => darkMode ? ThemeMode.dark : ThemeMode.light;
  double get characterScale => switch (characterSize) {
    'small' => .75,
    'large' => 1.2,
    _ => 1.0,
  };
  String get connection => devices.isEmpty
      ? 'Not connected'
      : devices.any(isOnline)
      ? 'Connected'
      : 'Offline';
  bool isOnline(Map<String, dynamic> device) {
    final seen = DateTime.tryParse(device['last_seen'] as String? ?? '');
    return seen != null &&
        DateTime.now().toUtc().difference(seen.toUtc()).inSeconds < 30;
  }

  String get _placesKey => 'pico.places.${userId ?? 'local'}';
  Future<void> load() async {
    final savedCharacter = preferences.getString('character');
    character = ['tuck', 'mica'].contains(savedCharacter)
        ? savedCharacter!
        : 'tuck';
    if (savedCharacter != character) {
      await preferences.setString('character', character);
    }
    characterSize = preferences.getString('pico.character_size') ?? 'medium';
    darkMode = preferences.getBool('pico.dark_mode') ?? false;
    loadPlaces();
    _loadedUser = userId;
    _auth = client?.auth.onAuthStateChange.listen((state) async {
      if (state.event == AuthChangeEvent.passwordRecovery) {
        recoveringPassword = true;
      }
      if (_loadedUser != userId) {
        _loadedUser = userId;
        devices = [];
        _sentCompanion = null;
        pendingPlaceId = null;
        loadPlaces();
      }
      notifyListeners();
      await refreshDevices();
    });
    await refreshDevices();
    if (client != null) {
      _timer = Timer.periodic(
        const Duration(seconds: 4),
        (_) => refreshDevices(),
      );
    }
  }

  void newSession() {
    selectedPlaceId = null;
    current = null;
    error = null;
    mood = 'idle';
    notifyListeners();
  }

  void selectPlace(Place place) {
    selectedPlaceId = place.id;
    unawaited(
      recordActivity('Chat opened', place.sentence, 'place:${place.id}'),
    );
    notifyListeners();
  }

  void select(Session session) {
    current = session;
    notifyListeners();
  }

  void setMood(String value) {
    if (![
      'idle',
      'listening',
      'talking',
      'working',
      'thinking',
      'done',
      'stuck',
      'needsYou',
    ].contains(value)) {
      return;
    }
    _moodTimer?.cancel();
    if (mood == value) return;
    mood = value;
    notifyListeners();
    unawaited(
      syncCompanion().catchError((Object _) {
        _sentCompanion = null;
      }),
    );
  }

  void completeRecovery() {
    recoveringPassword = false;
    notifyListeners();
  }

  Future<void> send(String text, {String? sourceText}) => savePlace(text);
  Future<void> summarizeDocument(String text) async {
    error = 'General document tasks are outside Pico’s resume flow.';
    notifyListeners();
  }

  Future<void> requestTask(
    String device,
    String kind,
    Map<String, dynamic> input, {
    String? utterance,
  }) async {
    error = 'Use Hold My Place to prepare your return.';
    notifyListeners();
  }

  Future<void> cancelTask(String id) async {
    throw UnsupportedError('No general-purpose computer tasks in Pico.');
  }

  Future<void> react(Session session, int index, String reaction) async {
    throw UnsupportedError('Use Place actions in Pico.');
  }

  void _changed() => notifyListeners();

  @override
  void dispose() {
    _moodTimer?.cancel();
    _auth?.cancel();
    _timer?.cancel();
    relay.close();
    super.dispose();
  }
}

String _uuid() {
  final bytes = List<int>.generate(16, (_) => Random.secure().nextInt(256));
  bytes[6] = (bytes[6] & 15) | 64;
  bytes[8] = (bytes[8] & 63) | 128;
  final hex = bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
  return '${hex.substring(0, 8)}-${hex.substring(8, 12)}-${hex.substring(12, 16)}-${hex.substring(16, 20)}-${hex.substring(20)}';
}
