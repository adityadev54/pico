import 'package:flutter_test/flutter_test.dart';
import 'package:pico/services/command_parser.dart';

void main() {
  test('Approved desktop app names route to app opening', () {
    const apps = ['ChatGPT', 'GalaxyBuds', 'Microsoft Word'];
    for (final input in [
      'Open ChatGpt',
      'open Chat GPT',
      'Launch ChatGPT app',
    ]) {
      final command = parseComputerCommand(input, approvedAppNames: apps);
      expect(command?.kind, 'open_app');
      expect(command?.input['app'], 'ChatGPT');
    }
    expect(
      parseComputerCommand(
        'Open Galaxy Buds',
        approvedAppNames: apps,
      )?.input['app'],
      'GalaxyBuds',
    );
    expect(
      parseComputerCommand(
        'open my homework.pdf',
        approvedAppNames: apps,
      )?.kind,
      'open_document',
    );
    expect(
      parseComputerCommand('open wikipedia', approvedAppNames: apps)?.kind,
      'open_website',
    );
  });
  test('Ambiguous app prefixes do not silently choose one', () {
    expect(
      parseComputerCommand(
        'Open Chat',
        approvedAppNames: ['ChatGPT', 'Chat Work'],
      )?.kind,
      isNot('open_app'),
    );
  });
}
