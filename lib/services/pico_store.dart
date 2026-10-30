import 'dart:async';
import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart' hide Session;

import '../models/place.dart';
import '../models/chat_entry.dart';
import '../models/approved_app.dart';
import '../models/activity.dart';
import '../models/session.dart';
import 'computer_tasks.dart';
import 'relay_client.dart';

part 'pico_chat_store.dart';
part 'pico_session_store.dart';
part 'pico_connection_store.dart';
part 'pico_agent_store.dart';
part 'pico_app_access.dart';
part 'pico_workflow_store.dart';

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
  final List<Map<String, dynamic>> _placeUpdates = [];
  final List<ApprovedApp> approvedApps = [];
  String? approvedAppsDeviceId,
      activeAppRequestId,
      openingAppId,
      appActionMessage;
  bool appsLoading = false;
  String museState = 'checking', museLabel = 'Checking Muse';
  DateTime? _museChecked;
  Timer? _appsTimer, _appOpenTimer;
  final List<ActivityEntry> activities = [];
  final List<Session> sessions = [];
  final List<Map<String, dynamic>> tasks = [];
  List<Map<String, dynamic>> devices = [];
  Session? current;
  bool composingNewChat = false;
  final Set<String> _hiddenTaskIds = {};
  final Set<String> _deletedChats = {};
  final Set<String> _newChatPlaceIds = {};
  Iterable<Place> get visiblePlaces => places.reversed.where(
    (p) => current != null && (p.chatId ?? p.id) == current!.id,
  );
  Iterable<Map<String, dynamic>> get visibleTasks => tasks.where(
    (t) =>
        !_hiddenTaskIds.contains(t['id']) &&
        (t['session_id'] == null || t['session_id'] == current?.id),
  );
  List<ChatEntry> get conversation => [
    ...visiblePlaces.map(ChatEntry.message),
    ...visibleTasks.map(ChatEntry.reply),
  ]..sort((a, b) => a.created.compareTo(b.created));
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
        _museChecked = null;
        museState = signedIn ? 'checking' : 'off';
        museLabel = signedIn ? 'Checking Muse' : 'Sign in for Muse';
        devices = [];
        tasks.clear();
        sessions.clear();
        current = null;
        busy = false;
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
    composingNewChat = true;
    _newChatPlaceIds.clear();
    _hiddenTaskIds.addAll(tasks.map((t) => t['id'] as String));
    selectedPlaceId = null;
    current = null;
    error = null;
    mood = 'idle';
    unawaited(persistChats());
    notifyListeners();
  }

  void selectPlace(Place place) {
    composingNewChat = false;
    _hiddenTaskIds.clear();
    selectedPlaceId = place.id;
    current = sessions
        .where((s) => s.id == (place.chatId ?? place.id))
        .firstOrNull;
    unawaited(persistChats());
    unawaited(
      recordActivity('Chat opened', place.sentence, 'place:${place.id}'),
    );
    notifyListeners();
  }

  void select(Session session) {
    composingNewChat = false;
    _hiddenTaskIds.clear();
    selectedPlaceId = null;
    current = session;
    unawaited(persistChats());
    error = null;
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

  Future<void> askPico(String device, String text, {String? grantId}) async {
    if (!signedIn || busy) return;
    final owner = userId;
    busy = true;
    notifyListeners();
    try {
      final chat = await rememberRequest(text);
      if (owner != userId) return;
      final response = await relay.request(
        '/ai/request',
        token: _token,
        body: {
          'device_id': device,
          'request_id': _uuid(),
          'session_id': chat.id,
          'text': text,
          'grant_id': ?grantId,
        },
      );
      if (owner != userId) return;
      if (response['task'] is Map) {
        tasks.insert(0, Map<String, dynamic>.from(response['task']));
        error = null;
      } else {
        final question = response['question'] as String?;
        if (question != null) await rememberReply(question, chat.id);
        error = null;
      }
    } catch (e) {
      if (owner != userId) return;
      error = e.toString().replaceFirst('Exception: ', '');
    } finally {
      if (owner == userId) {
        busy = false;
        notifyListeners();
      }
    }
  }

  Future<void> requestTask(
    String device,
    String kind,
    Map<String, dynamic> input, {
    String? utterance,
    bool confirmed = false,
  }) async {
    if (busy) return;
    if (client == null) {
      error = 'Sign in on your phone first.';
      notifyListeners();
      return;
    }
    final owner = userId;
    busy = true;
    setMood('working');
    try {
      final chat = await rememberRequest(
        utterance ?? requestTitle(kind, input),
      );
      final task = await ComputerTasks(client!).create(
        device: device,
        session: chat.id,
        kind: kind,
        input: input,
        confirmed: confirmed,
      );
      if (owner != userId) return;
      tasks.insert(0, Map<String, dynamic>.from(task));
      error = null;
      await recordActivity(
        'Request sent',
        utterance ?? kind,
        'task:${task['id']}',
      );
    } catch (e) {
      if (owner != userId) return;
      error = e.toString().replaceFirst('Exception: ', '');
      forgetDeadDevice(device, error);
    } finally {
      if (owner == userId) busy = false;
      if (mood == 'working') setMood('idle');
      notifyListeners();
    }
  }

  /// Drops a computer the relay no longer recognizes (unpaired,
  /// revoked, or a different backend) and re-checks, so the next send
  /// doesn't fail the same way. Returns true when it dropped.
  bool forgetDeadDevice(String device, String? message) {
    if (message == null || !message.contains('Computer not found')) {
      return false;
    }
    devices.removeWhere((d) => d['id'] == device);
    unawaited(refreshDevices());
    return true;
  }

  void clearError() {
    if (error == null) return;
    error = null;
    notifyListeners();
  }

  Future<void> approveTransfer({
    required String device,
    required Map<String, dynamic> searchTask,
    required Map<String, dynamic> candidate,
  }) async {
    // Exact-file approval: binds this candidate to a new transfer task.
    await requestTask(device, 'send_file', {
      'candidate_id': candidate['candidate_id'],
      'approval_id': _uuid(),
      'search_task_id': searchTask['id'],
    }, utterance: 'Send ${candidate['name']} to phone');
  }

  Future<void> refreshTasks() async {
    if (client == null) return;
    final owner = userId;
    try {
      final service = ComputerTasks(client!);
      final rows = await service.list();
      final chat = current?.id;
      if (chat != null) {
        final history = await service.list(session: chat);
        final ids = rows.map((r) => r['id']).toSet();
        rows.addAll(history.where((r) => !ids.contains(r['id'])));
      }
      if (owner != userId) return;
      final incoming = rows.map((r) => r['id']).toSet();
      tasks.removeWhere((t) => incoming.contains(t['id']));
      tasks.addAll(rows);
      await importTaskChats(rows);
      notifyListeners();
    } catch (_) {
      // Keep last tasks through a network outage.
    }
  }

  Future<void> submitReceipt({
    required String task,
    required int size,
    required String digest,
  }) async {
    if (client == null) return;
    await ComputerTasks(client!)
        .receipt(task: task, size: size, digest: digest);
    await refreshTasks();
  }

  Future<Map<String, dynamic>?> uploadFile(
    String device,
    String name,
    Uint8List bytes, {
    String? grant,
  }) async {
    if (client == null) return null;
    try {
      final receipt = await ComputerTasks(client!)
          .upload(device: device, name: name, bytes: bytes, grant: grant);
      await refreshTasks();
      error = null;
      notifyListeners();
      return receipt;
    } catch (e) {
      error = e.toString().replaceFirst('Exception: ', '');
      notifyListeners();
      return null;
    }
  }

  Future<void> steerTask(String id, String name) async {
    if (client == null) return;
    try {
      await ComputerTasks(client!).steer(id, name);
      await refreshTasks();
      error = null;
    } catch (e) {
      error = e.toString().replaceFirst('Exception: ', '');
    }
    notifyListeners();
  }

  Future<void> cancelTask(String id) async {
    if (client == null) return;
    try {
      await ComputerTasks(client!).cancel(id);
      final i = tasks.indexWhere((t) => t['id'] == id);
      if (i >= 0) tasks[i] = {...tasks[i], 'status': 'cancelled'};
      error = null;
    } catch (e) {
      error = e.toString().replaceFirst('Exception: ', '');
    }
    notifyListeners();
  }

  Future<void> react(Session session, int index, String reaction) async {
    throw UnsupportedError('Use Place actions in Pico.');
  }

  void _changed() => notifyListeners();

  @override
  void dispose() {
    _moodTimer?.cancel();
    _appsTimer?.cancel();
    _appOpenTimer?.cancel();
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
