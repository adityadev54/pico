import '../models/computer_command.dart';

ComputerCommand? parseFileManagement(String text, {String? device}) {
  ComputerCommand command(String kind, Map<String, dynamic> input) =>
      ComputerCommand(kind, input, deviceHint: device);
  String clean(String s) => s.trim().replaceAll(RegExp(r'^["“]|["”]$'), '');
  final delete = RegExp(
    r'^(?:delete|trash|remove)\s+(.+)$',
    caseSensitive: false,
  ).firstMatch(text);
  if (delete != null) {
    return command('delete_files', {
      'path': clean(delete.group(1)!),
      'confirm': 'DELETE',
    });
  }
  final restore = RegExp(
    r'^(?:restore|undelete)\s+(.+)$',
    caseSensitive: false,
  ).firstMatch(text);
  if (restore != null) {
    return command('restore_deleted', {'name': clean(restore.group(1)!)});
  }
  if (RegExp(
    r'^empty (?:pico[’\x27]?s? )?trash$',
    caseSensitive: false,
  ).hasMatch(text)) {
    return command('empty_trash', {'confirm': 'EMPTY'});
  }
  final zip = RegExp(
    r'^(?:zip|compress)\s+(.+?)(?:\s+as\s+(.+))?$',
    caseSensitive: false,
  ).firstMatch(text);
  if (zip != null) {
    return command('archive', {
      'action': 'create',
      'paths': zip
          .group(1)!
          .split(RegExp(r'\s+and\s+|,\s*'))
          .map(clean)
          .toList(),
      if (zip.group(2) != null) 'output': clean(zip.group(2)!),
    });
  }
  final unzip = RegExp(
    r'^unzip\s+(.+?)(?:\s+to\s+(.+))?$',
    caseSensitive: false,
  ).firstMatch(text);
  if (unzip != null) {
    return command('archive', {
      'action': 'extract',
      'paths': [clean(unzip.group(1)!)],
      if (unzip.group(2) != null) 'output': clean(unzip.group(2)!),
    });
  }
  return null;
}
