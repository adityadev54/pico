import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;
import 'package:supabase_flutter/supabase_flutter.dart';

import 'config.dart';
import 'task_view.dart';

class ComputerTasks {
  ComputerTasks(this.client);
  final SupabaseClient client;
  String get _base => Config.relayBase;
  Map<String, String> get _headers => {
    'Authorization': 'Bearer ${client.auth.currentSession!.accessToken}',
    'Content-Type': 'application/json',
  };

  Future<Map<String, dynamic>> create({
    required String device,
    required String session,
    required String kind,
    required Map<String, dynamic> input,
    bool confirmed = false,
  }) async {
    final response = await http
        .post(
          Uri.parse('$_base/tasks'),
          headers: _headers,
          body: jsonEncode({
            'device_id': device,
            'session_id': session,
            'kind': kind,
            'input': input,
            'confirmed': confirmed,
          }),
        )
        .timeout(const Duration(seconds: 25));
    if (response.statusCode != 200) {
      throw Exception(_message(response, 'Couldn’t queue this request'));
    }
    return Map<String, dynamic>.from(jsonDecode(response.body));
  }

  Future<List<Map<String, dynamic>>> list({String? session}) async {
    var query = client.from('tasks').select();
    if (session != null) query = query.eq('session_id', session);
    final rows = await query
        .order('created_at', ascending: false)
        .limit(session == null ? 100 : 200);
    return rows.map((e) => picoTaskView(Map<String, dynamic>.from(e))).toList();
  }

  Future<Uint8List> download(String id) async {
    final response = await http
        .post(
          Uri.parse('$_base/files/download'),
          headers: _headers,
          body: jsonEncode({'id': id}),
        )
        .timeout(const Duration(seconds: 30));
    if (response.statusCode != 200) {
      throw Exception(_message(response, 'Couldn’t download this file'));
    }
    return base64Decode(jsonDecode(response.body)['content_base64'] as String);
  }

  Future<void> removeFile(String id) async =>
      _post('/files/delete', {'id': id});
  Future<void> clearHistory() async => _post('/history/clear', {});
  Future<void> receipt({
    required String task,
    required int size,
    required String digest,
  }) async => _post('/tasks/receipt', {
    'task_id': task,
    'size_bytes': size,
    'digest': digest,
  });

  Future<void> _post(String path, Map<String, dynamic> body) async {
    final response = await http
        .post(
          Uri.parse('$_base$path'),
          headers: _headers,
          body: jsonEncode(body),
        )
        .timeout(const Duration(seconds: 30));
    if (response.statusCode != 200) {
      throw Exception(_message(response, 'Couldn’t complete this request'));
    }
  }

  Future<Map<String, dynamic>> upload({
    required String device,
    required String name,
    required Uint8List bytes,
    String? grant,
  }) async {
    final response = await http
        .post(
          Uri.parse('$_base/uploads'),
          headers: _headers,
          body: jsonEncode({
            'device_id': device,
            'name': name,
            'content_base64': base64Encode(bytes),
            'purpose': 'transfer',
            'grant_id': ?grant,
          }),
        )
        .timeout(const Duration(seconds: 60));
    if (response.statusCode != 200) {
      throw Exception(_message(response, 'Couldn’t upload'));
    }
    return Map<String, dynamic>.from(jsonDecode(response.body));
  }

  Future<void> steer(String id, String name) async {
    final response = await http
        .post(
          Uri.parse('$_base/tasks/steer'),
          headers: _headers,
          body: jsonEncode({'id': id, 'name': name}),
        )
        .timeout(const Duration(seconds: 20));
    if (response.statusCode != 200) {
      throw Exception(_message(response, 'Couldn’t rename'));
    }
  }

  Future<void> cancel(String id) async {
    final response = await http
        .post(
          Uri.parse('$_base/tasks/cancel'),
          headers: _headers,
          body: jsonEncode({'id': id}),
        )
        .timeout(const Duration(seconds: 20));
    if (response.statusCode != 200) {
      throw Exception(_message(response, 'Couldn’t cancel'));
    }
  }

  String _message(http.Response response, String fallback) {
    try {
      final value = jsonDecode(response.body) as Map<String, dynamic>;
      final error = value['error'] as String?;
      if (error != null && error.isNotEmpty) return error;
    } catch (_) {}
    return fallback;
  }
}
