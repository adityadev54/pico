import 'package:flutter_test/flutter_test.dart';
import 'package:pico/services/task_view.dart';

void main() {
  test('Shared-schema task metadata preserves the actual workflow', () {
    final raw = {
      'kind': 'open_app',
      'status': 'queued',
      'input': {'_pico_kind': 'create_note'},
    };
    expect(picoTaskView(raw)['kind'], 'create_note');
    expect(raw['kind'], 'open_app');
  });
  test('Transfer only finishes after a verified receipt', () {
    final raw = {
      'kind': 'open_app',
      'status': 'working',
      'input': {'_pico_kind': 'send_file'},
      'result': {'artifact_id': 'digest'},
    };
    expect(picoTaskView(raw)['status'], 'verifying');
    expect(
      picoTaskView({
        ...raw,
        'status': 'completed',
        'result': {'artifact_id': 'digest', 'receipt': 'verified'},
      })['status'],
      'completed',
    );
  });
}
