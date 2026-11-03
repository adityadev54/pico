import '../models/computer_command.dart';

/// Local deterministic routing; these file tools do not call Muse.
ComputerCommand? parseDocumentCommand(String text, {String? device}) {
  ComputerCommand command(String kind, Map<String, dynamic> input) =>
      ComputerCommand(kind, input, deviceHint: device);
  String unquote(String name) =>
      name.trim().replaceAll(RegExp(r'^["“]|["”]$'), '');
  final conversion = RegExp(
    r'^(?:convert|turn|change)\s+(.+?)\s+(?:in)?to\s+(pdf|docx|word|txt|text|png|jpe?g|webp)$',
    caseSensitive: false,
  ).firstMatch(text);
  if (conversion != null) {
    var format = conversion.group(2)!.toLowerCase();
    format = {'word': 'docx', 'text': 'txt', 'jpeg': 'jpg'}[format] ?? format;
    return command('convert_file', {
      'path': unquote(conversion.group(1)!),
      'to': format,
    });
  }
  final merge = RegExp(
    r'^merge\s+(.+?)(?:\s+into\s+(.+))?$',
    caseSensitive: false,
  ).firstMatch(text);
  if (merge != null) {
    final names = merge
        .group(1)!
        .split(RegExp(r'\s+and\s+|,\s*'))
        .map(unquote)
        .toList();
    if (names.length >= 2) {
      return command('pdf_pages', {
        'action': 'merge',
        'paths': names,
        if (merge.group(2) != null) 'output': unquote(merge.group(2)!),
      });
    }
  }
  final split = RegExp(
    r'^split\s+(.+?)\s+pages?\s+([\d,\-\s]+)$',
    caseSensitive: false,
  ).firstMatch(text);
  if (split != null) {
    return command('pdf_pages', {
      'action': 'split',
      'paths': [unquote(split.group(1)!)],
      'pages': split.group(2)!.trim(),
    });
  }
  final extract = RegExp(
    r'^extract\s+pages?\s+([\d,\-\s]+?)\s+from\s+(.+)$',
    caseSensitive: false,
  ).firstMatch(text);
  if (extract != null) {
    return command('pdf_pages', {
      'action': 'split',
      'paths': [unquote(extract.group(2)!)],
      'pages': extract.group(1)!.trim(),
    });
  }
  final rotate = RegExp(
    r'^rotate\s+(.+?)\s+(90|180|270)\s*degrees?$',
    caseSensitive: false,
  ).firstMatch(text);
  if (rotate != null) {
    return command('pdf_pages', {
      'action': 'rotate',
      'paths': [unquote(rotate.group(1)!)],
      'angle': int.parse(rotate.group(2)!),
    });
  }
  final watermark = RegExp(
    r'^(?:watermark|stamp)\s+(.+?)\s+with\s+(.+)$',
    caseSensitive: false,
  ).firstMatch(text);
  if (watermark != null) {
    return command('pdf_pages', {
      'action': 'watermark',
      'paths': [unquote(watermark.group(1)!)],
      'watermark': unquote(watermark.group(2)!),
    });
  }
  return null;
}
