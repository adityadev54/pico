import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:supabase_flutter/supabase_flutter.dart';

import 'config.dart';

class ComputerTasks {
  ComputerTasks(this.client);
  final SupabaseClient client;
  Future<Map<String, dynamic>> create({
    required String device,
    required String session,
    required String kind,
    required Map<String, dynamic> input,
  }) async {
    final response = await http
        .post(
          Uri.parse('${Config.relayUrl}/tasks'),
          headers: {
            'Authorization':
                'Bearer ${client.auth.currentSession!.accessToken}',
            'Content-Type': 'application/json',
          },
          body: jsonEncode({
            'device_id': device,
            'session_id': session,
            'kind': kind,
            'input': input,
          }),
        )
        .timeout(const Duration(seconds: 25));
    if (response.statusCode != 200) {
      throw Exception('Couldn’t queue this request');
    }
    return Map<String, dynamic>.from(jsonDecode(response.body));
  }

  Future<List<Map<String, dynamic>>> list() async =>
      await client.from('tasks').select().order('created_at');
  Future<void> removeFile(String id) async =>
      _post('/files/delete', {'id': id});
  Future<void> clearHistory() async => _post('/history/clear', {});
  Future<void> _post(String path, Map<String, dynamic> body) async {
    final response = await http
        .post(
          Uri.parse('${Config.relayUrl}$path'),
          headers: {
            'Authorization':
                'Bearer ${client.auth.currentSession!.accessToken}',
            'Content-Type': 'application/json',
          },
          body: jsonEncode(body),
        )
        .timeout(const Duration(seconds: 30));
    if (response.statusCode != 200) {
      throw Exception('Couldn’t complete this request');
    }
  }

  Future<void> cancel(String id) async {
    final response = await http
        .post(
          Uri.parse('${Config.relayUrl}/tasks/cancel'),
          headers: {
            'Authorization':
                'Bearer ${client.auth.currentSession!.accessToken}',
            'Content-Type': 'application/json',
          },
          body: jsonEncode({'id': id}),
        )
        .timeout(const Duration(seconds: 20));
    if (response.statusCode != 200) throw Exception('Couldn’t cancel');
  }
}
