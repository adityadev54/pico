part of 'pico_store.dart';

extension PicoWorkflowStore on PicoStore {
  Future<void> refreshMuseStatus() async {
    if (!signedIn ||
        (_museChecked != null &&
            DateTime.now().difference(_museChecked!).inSeconds < 60)) {
      return;
    }
    _museChecked = DateTime.now();
    final owner = userId;
    try {
      final value = await relay.request('/ai/status', token: _token);
      if (owner != userId) return;
      museState = value['state'] as String? ?? 'unavailable';
      museLabel = value['label'] as String? ?? 'Muse unavailable';
    } catch (_) {
      if (owner != userId) return;
      museState = 'unavailable';
      museLabel = 'Muse status unavailable';
    }
    _changed();
  }

  Future<void> approveTask(String id, {String? grant}) async {
    try {
      await relay.request(
        '/tasks/approve',
        token: _token,
        body: {'id': id, 'confirmed': true, 'grant_id': ?grant},
      );
      error = null;
      await refreshTasks();
    } catch (e) {
      error = e.toString();
      _changed();
    }
  }

  Future<void> readCandidate(
    Map<String, dynamic> search,
    Map<String, dynamic> candidate,
  ) => requestTask(search['device_id'] as String, 'read_document', {
    'search_task_id': search['id'],
    'candidate_id': candidate['candidate_id'],
  });

  Future<void> summarizeTask(String id) async {
    if (busy) return;
    busy = true;
    _changed();
    try {
      await relay.request(
        '/ai/summarize',
        token: _token,
        body: {'id': id, 'request_id': _uuid(), 'confirmed': true},
      );
      error = null;
      await refreshTasks();
    } catch (e) {
      error = e.toString();
    } finally {
      busy = false;
      _changed();
    }
  }
}
