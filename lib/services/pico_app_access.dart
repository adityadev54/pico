part of 'pico_store.dart';

extension PicoAppAccess on PicoStore {
  void _clearAppAccess() {
    approvedApps.clear();
    approvedAppsDeviceId = null;
    openingAppId = null;
    activeAppRequestId = null;
    appActionMessage = null;
    appsLoading = false;
    _appsTimer?.cancel();
    _appOpenTimer?.cancel();
  }

  Future<void> loadApprovedApps() async {
    if (!signedIn || !linked || appsLoading) return;
    final owner = userId, device = devices.first['id'] as String;
    appsLoading = true;
    appActionMessage = null;
    _appsTimer?.cancel();
    _changed();
    try {
      await relay.request(
        '/mail',
        token: _token,
        body: {
          'device_id': device,
          'id': _uuid(),
          'kind': 'apps_request',
          'payload': <String, String>{},
        },
      );
      if (userId != owner || !devices.any((d) => d['id'] == device)) return;
      if (!appsLoading) return;
      _appsTimer = Timer(const Duration(seconds: 20), () {
        appsLoading = false;
        appActionMessage = 'No app list received yet. Check that your computer is online and Pico is updated.';
        _changed();
      });
      await refreshDevices();
    } catch (_) {
      if (userId != owner) return;
      appsLoading = false;
      appActionMessage = 'Couldn’t load apps. Please try again.';
      _changed();
    }
  }

  Future<void> openApprovedApp(ApprovedApp app) async {
    if (!signedIn || !linked || openingAppId != null) return;
    if (!devices.any(isOnline)) {
      appActionMessage =
          'Your computer is offline. Open Pico there and try again.';
      _changed();
      return;
    }
    if (approvedAppsDeviceId != devices.first['id'] ||
        !approvedApps.any((a) => a.id == app.id)) {
      return;
    }
    final owner = userId,
        device = devices.first['id'] as String,
        request = _uuid();
    activeAppRequestId = request;
    openingAppId = app.id;
    appActionMessage = 'Waiting for your computer…';
    _changed();
    try {
      await relay.request(
        '/mail',
        token: _token,
        body: {
          'device_id': device,
          'id': request,
          'kind': 'open_app',
          'payload': {'app_id': app.id, 'request_id': request},
        },
      );
      if (userId != owner || activeAppRequestId != request) return;
      _appOpenTimer?.cancel();
      _appOpenTimer = Timer(const Duration(seconds: 65), () {
        openingAppId = null;
        appActionMessage =
            'No confirmation yet. Check your computer before trying again.';
        _changed();
      });
      await refreshDevices();
    } catch (_) {
      if (userId != owner || activeAppRequestId != request) return;
      openingAppId = null;
      appActionMessage = 'Couldn’t send the request. Please try again.';
      _changed();
    }
  }

  void _receiveAppMessage(Map<String, dynamic> message) {
    if (!linked || message['device_id'] != devices.first['id']) return;
    final data = Map<String, dynamic>.from(message['payload']);
    if (message['kind'] == 'app_catalog') {
      final apps = (jsonDecode(data['catalog'] as String) as List)
          .map((a) => ApprovedApp.fromJson(Map<String, dynamic>.from(a)))
          .take(20)
          .toList();
      approvedApps
        ..clear()
        ..addAll(apps);
      approvedAppsDeviceId = message['device_id'] as String;
      _appsTimer?.cancel();
      appsLoading = false;
      if (openingAppId == null) appActionMessage = null;
    } else if (message['kind'] == 'app_result' &&
        data['request_id'] == activeAppRequestId) {
      _appOpenTimer?.cancel();
      openingAppId = null;
      appActionMessage = data['message'] as String;
      activeAppRequestId = null;
    }
  }
}
