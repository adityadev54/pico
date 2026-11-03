import 'package:flutter_test/flutter_test.dart';
import 'package:pico/services/command_parser.dart';

void main() {
  test('natural document commands preserve filenames and device target', () {
    final photo = parseComputerCommand(
      'Could you convert Homework photo.jpg to pdf on my Mac',
    );
    expect(photo?.kind, 'convert_file');
    expect(photo?.input, {'path': 'Homework photo.jpg', 'to': 'pdf'});
    expect(photo?.deviceHint, 'Mac');
    final merge = parseComputerCommand('merge lecture.pdf and notes.pdf');
    expect(merge?.input, {
      'action': 'merge',
      'paths': ['lecture.pdf', 'notes.pdf'],
    });
    expect(parseComputerCommand('extract page 2 from lecture.pdf')?.input, {
      'action': 'split',
      'paths': ['lecture.pdf'],
      'pages': '2',
    });
  });
  test('unrelated chat is not rerouted into a file operation', () {
    expect(parseComputerCommand('I might convert my notes tomorrow'), isNull);
    expect(
      parseComputerCommand('unlock secret.pdf with password test'),
      isNull,
    );
  });
}
