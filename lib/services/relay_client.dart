import 'dart:convert';

import 'package:http/http.dart' as http;

import 'config.dart';

class RelayClient {
  RelayClient({http.Client? client, String? base})
    : _client = client ?? http.Client(),
      base = base ?? Config.relayBase;
  final http.Client _client;
  final String base;
  Future<Map<String, dynamic>> request(
    String path, {
    String? token,
    Map<String, dynamic>? body,
  }) async {
    final uri = Uri.parse('$base$path');
    final headers = {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
    final response =
        await (body == null
                ? _client.get(uri, headers: headers)
                : _client.post(uri, headers: headers, body: jsonEncode(body)))
            .timeout(const Duration(seconds: 20));
    final value = jsonDecode(response.body) as Map<String, dynamic>;
    if (response.statusCode >= 400) {
      throw RelayException(
        value['error'] as String? ?? 'Connection unavailable.',
        response.statusCode,
      );
    }
    return value;
  }

  void close() => _client.close();
}

class RelayException implements Exception {
  const RelayException(this.message, this.status);
  final String message;
  final int status;
  @override
  String toString() => message;
}
