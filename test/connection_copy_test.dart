import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:pico/services/relay_client.dart';

void main() {
  test('transport failures explain recovery without raw localhost details', () {
    final copy = relayErrorMessage(
      http.ClientException(
        'Connection reset by peer',
        Uri.parse('http://localhost:8766/tasks'),
      ),
    );
    expect(copy, contains('Connection interrupted'));
    expect(copy, isNot(contains('localhost')));
    expect(relayErrorMessage(TimeoutException('timeout')), copy);
    expect(
      relayErrorMessage(const RelayException('Permission denied.', 403)),
      'Permission denied.',
    );
  });
}
