import 'package:flutter_test/flutter_test.dart';

import 'package:pico/services/command_parser.dart';

void main() {
  test('file wording routes to a reviewed local write', () {
    for (final text in [
      'Create a file called test.txt saying Hello',
      'Create a text file named test.txt containing Hello',
      'Create a note called test.txt saying Hello',
      'Create file test.txt saying Hello',
    ]) {
      final command = parseComputerCommand(text);
      expect(command?.kind, 'create_note', reason: text);
      expect(command?.input['name'], 'test.txt');
      expect(command?.input['text'], 'Hello');
    }
  });
  test('draft requests are identified for explicit guidance', () {
    expect(looksLikeCommand('Draft a three-item checklist'), isTrue);
    expect(looksLikeCommand('Ask Pico: draft a checklist'), isTrue);
  });
  test('Android speech spelling retains explicit Muse routing', () {
    expect(
      museRequestText(
        'Ask picko: Draft a three item checklist into checklist.txt',
      ),
      'Draft a three item checklist into checklist.txt',
    );
    expect(museRequestText('Ask Pico: Draft a checklist'), 'Draft a checklist');
    expect(museRequestText('Ask piko, Draft a checklist'), 'Draft a checklist');
    expect(looksLikeCommand('Ask picko: Draft a checklist'), isTrue);
    expect(museRequestText('Draft a checklist'), isNull);
    expect(museRequestText('Ask another app to draft'), isNull);
  });
}
