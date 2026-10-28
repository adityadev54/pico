part of 'pico_store.dart';

extension PicoChatStore on PicoStore {
  String get _activitiesKey => 'pico.activities.${userId ?? 'local'}';
  Future<void> recordActivity(
    String title,
    String detail,
    String target,
  ) async {
    activities.insert(
      0,
      ActivityEntry(
        id: _uuid(),
        title: title,
        detail: detail,
        created: DateTime.now(),
        target: target,
      ),
    );
    if (activities.length > 40) activities.removeRange(40, activities.length);
    await _persistActivities();
    _changed();
  }

  Future<void> _persistActivities() => preferences
      .setString(
        _activitiesKey,
        jsonEncode(activities.map((e) => e.toJson()).toList()),
      )
      .then((_) {});

  void loadPlaces() {
    places.clear();
    selectedPlaceId = null;
    activities.clear();
    try {
      activities.addAll(
        (jsonDecode(preferences.getString(_activitiesKey) ?? '[]') as List).map(
          (e) => ActivityEntry.fromJson(Map<String, dynamic>.from(e)),
        ),
      );
    } catch (_) {
      /* Leave malformed history empty. */
    }
    try {
      places.addAll(
        (jsonDecode(preferences.getString(_placesKey) ?? '[]') as List).map(
          (e) => Place.fromJson(Map<String, dynamic>.from(e)),
        ),
      );
    } catch (_) {
      error = 'Saved Places could not be read.';
    }
  }

  Future<void> _persist() async {
    if (!await preferences.setString(
      _placesKey,
      jsonEncode(places.map((p) => p.toJson()).toList()),
    )) {
      throw StateError('Storage unavailable');
    }
  }

  Future<void> savePlace(String sentence) async {
    sentence = sentence.trim();
    if (sentence.isEmpty || busy) return;
    final place = Place(
      id: pendingPlaceId ?? _uuid(),
      sentence: sentence,
      created: DateTime.now(),
    );
    pendingPlaceId = null;
    selectedPlaceId = null;
    places.insert(0, place);
    try {
      await _persist();
      error = null;
    } catch (_) {
      places.remove(place);
      error = 'Couldn’t save your Place. Try again.';
      _changed();
      return;
    }
    _changed();
    await recordActivity('Place saved', sentence, 'place:${place.id}');
    setMood('working');
    try {
      await _deliverPlaces();
    } finally {
      if (mood == 'working') setMood('idle');
    }
    _changed();
  }

  Future<void> updatePlace(Place place, {bool? parked, bool? finished}) async {
    final i = places.indexWhere((p) => p.id == place.id);
    if (i < 0) return;
    final old = places[i];
    places[i] = old.copyWith(parked: parked, finished: finished);
    try {
      await _persist();
      error = null;
      await recordActivity(
        finished == true
            ? 'Place finished'
            : parked == true
            ? 'Place parked'
            : 'Place resumed',
        place.sentence,
        'place:${place.id}',
      );
    } catch (_) {
      places[i] = old;
      error = 'Couldn’t update your Place.';
    }
    _changed();
  }

  Future<void> deleteChat(Place place) async {
    final i = places.indexWhere((p) => p.id == place.id);
    if (i < 0) return;
    final removed = places.removeAt(i);
    try {
      await _persist();
    } catch (_) {
      places.insert(i, removed);
      error = 'Couldn’t delete this chat. Try again.';
      _changed();
      return;
    }
    activities.removeWhere((a) => a.target == 'place:${place.id}');
    await _persistActivities();
    if (selectedPlaceId == place.id) selectedPlaceId = null;
    error = null;
    _changed();
  }

  Future<void> rememberSearch(String value) async {
    final text = value.trim();
    if (text.isEmpty) return;
    activities.removeWhere((a) => a.target == 'search:$text');
    await recordActivity(text, 'Search', 'search:$text');
  }

  Future<void> clearHistory() async {
    // Clear only this app’s local history; retain live delivery messages.
    await preferences.remove(_placesKey);
    await preferences.remove(_activitiesKey);
    activities.clear();
    places.clear();
    sessions.clear();
    tasks.clear();
    current = null;
    selectedPlaceId = null;
    _changed();
  }
}
