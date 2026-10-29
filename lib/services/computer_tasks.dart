import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;
import 'package:supabase_flutter/supabase_flutter.dart';

import 'config.dart';

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
          }),
        )
        .timeout(const Duration(seconds: 25));
    if (response.statusCode != 200) {
      throw Exception(_message(response, 'Couldn’t queue this request'));
    }
    return Map<String, dynamic>.from(jsonDecode(response.body));
  }

  Future<List<Map<String, dynamic>>> list() async {
    final rows = await client
        .from('tasks')
        .select()
        .order('created_at', ascending: false)
        .limit(30);
    return rows.map((e) => Map<String, dynamic>.from(e)).toList();
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
