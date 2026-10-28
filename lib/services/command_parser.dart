import '../models/computer_command.dart';

/// Recognizes supported actions only; other speech stays ordinary conversation.
ComputerCommand? parseComputerCommand(String speech) {
  var text = speech.trim().replaceAll(RegExp(r'[.!?]+$'), '');
  text = text.replaceFirst(
    RegExp(r'^(hey\s+pico[, ]*|pico[, ]*|please\s+)', caseSensitive: false),
    '',
  );
  final trailingWeb = RegExp(
    r'^(?:search for|look for|find) (.+) on (?:the )?(?:web|internet)$',
    caseSensitive: false,
  ).firstMatch(text);
  if (trailingWeb != null) text = 'search the web for ${trailingWeb.group(1)}';
  String? device;
  final target = RegExp(
    r'\s+on (?:my |the )?((?=.*\b(?:mac|macbook|windows|pc|laptop|computer)\b).+)$',
    caseSensitive: false,
  ).firstMatch(text);
  if (target != null) {
    device = target.group(1);
    text = text.substring(0, target.start);
  }
  ComputerCommand command(String kind, Map<String, dynamic> input) =>
      ComputerCommand(kind, input, deviceHint: device);
  final appMatch = RegExp(
    r'^(?:open|launch|start)\s+(?:the\s+)?(calculator|calendar|vs\s*code|visual studio code|browser|default browser|notes|sticky notes)(?: app)?$',
    caseSensitive: false,
  ).firstMatch(text);
  if (appMatch != null) {
    final app = appMatch.group(1)!.toLowerCase().replaceAll(' ', '');
    return command('open_app', {
      'app': switch (app) {
        'vscode' || 'visualstudiocode' => 'vscode',
        'defaultbrowser' => 'browser',
        'stickynotes' => 'notes',
        _ => app,
      },
    });
  }
  if (RegExp(
    r'^(?:open |manage |show )?(?:permissions|folder access)$',
    caseSensitive: false,
  ).hasMatch(text)) {
    return command('manage_permissions', {});
  }
  if (RegExp(
    r'^(?:send|transfer|bring|share)\b.*\b(?:to (?:my |the )?phone|to (?:my |the )?iphone|here)$',
    caseSensitive: false,
  ).hasMatch(text)) {
    return command('send_file', {});
  }
  if (RegExp(
    r'^(?:summari[sz]e|give me (?:a )?(?:summary|takeaways))\b',
    caseSensitive: false,
  ).hasMatch(text)) {
    final name = text
        .replaceFirst(
          RegExp(
            r'^(?:summari[sz]e|give me (?:a )?(?:summary|takeaways)(?: of)?)\s*',
            caseSensitive: false,
          ),
          '',
        )
        .trim();
    if (name.isEmpty ||
        RegExp(
          r'^(?:this|that|the)(?: file| document)?$',
          caseSensitive: false,
        ).hasMatch(name)) {
      return command('summarize_document', {});
    }
    return command('find_document', {
      'query': name.replaceFirst(
        RegExp(r'^(?:the |my )', caseSensitive: false),
        '',
      ),
      'summarize': true,
    });
  }
  final webSearch = RegExp(
    r'^(?:search (?:the )?(?:web|internet)(?: for)?|google|look up|find (?:a |the )?website(?: for| about)?)\s+(.+)$',
    caseSensitive: false,
  ).firstMatch(text);
  if (webSearch != null) {
    return command('open_website', {
      'url': Uri.https('www.google.com', '/search', {
        'q': webSearch.group(1)!,
      }).toString(),
    });
  }
  final website = RegExp(
    r'^(?:open|visit|go to|browse)\s+(.+)$',
    caseSensitive: false,
  ).firstMatch(text);
  if (website != null) {
    var url = website
        .group(1)!
        .trim()
        .replaceFirst(
          RegExp(r'^(?:the )?website\s+', caseSensitive: false),
          '',
        );
    url = url
        .replaceAll(RegExp(r'\s+dot\s+', caseSensitive: false), '.')
        .replaceAll(RegExp(r'\s+slash\s+', caseSensitive: false), '/');
    const sites = {
      'youtube': 'youtube.com',
      'google': 'google.com',
      'wikipedia': 'wikipedia.org',
      'github': 'github.com',
      'figma': 'figma.com',
      'amazon': 'amazon.com',
      'bing': 'bing.com',
    };
    url = sites[url.toLowerCase()] ?? url;
    if (!url.contains('://')) {
      if (!RegExp(r'^[\w-]+(?:\.[\w-]+)+(?:/\S*)?$').hasMatch(url)) return null;
      url = 'https://$url';
    }
    final parsed = Uri.tryParse(url);
    if (parsed == null ||
        !['https', 'http'].contains(parsed.scheme) ||
        parsed.host.isEmpty ||
        parsed.userInfo.isNotEmpty) {
      return null;
    }
    return command('open_website', {'url': url});
  }
  final find = RegExp(
    r'^(?:find|search for|look for|locate)\s+(.+)$',
    caseSensitive: false,
  ).firstMatch(text);
  if (find != null) {
    var query = find
        .group(1)!
        .replaceFirst(
          RegExp(
            r'^(?:(?:my|the|a) )?(?:(?:file|document)(?: named| called)? )?',
            caseSensitive: false,
          ),
          '',
        )
        .trim();
    query = query.replaceAll(RegExp(r'\s+dot\s+', caseSensitive: false), '.');
    if (query.isNotEmpty) return command('find_document', {'query': query});
  }
  return null;
}
