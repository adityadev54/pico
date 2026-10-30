import 'dart:convert';

import '../models/computer_command.dart';

/// True when the text uses command language (addressing Pico, a request
/// verb) even if [parseComputerCommand] recognizes no supported action.
/// Used to explain the miss instead of failing silently as a note.
bool looksLikeCommand(String speech) {
  return RegExp(
    r'^(hey pico|pico|please|can you|could you|would you|will you|open|launch|start|find|search|look for|locate|send|transfer|bring|share|summari[sz]e|google|visit|go to|browse|manage|show|ask (?:pico|picko|piko)|draft|create|make|write|rename|change|arrange|organize|organise|gather|collect)\b',
    caseSensitive: false,
  ).hasMatch(speech.trim());
}

/// Common speech transcriptions retain the explicit Ask Pico opt-in.
String? museRequestText(String speech) => RegExp(
  r'^ask\s+(?:pico|picko|piko)[: ,]+(.+)$',
  caseSensitive: false,
).firstMatch(speech.trim())?.group(1)?.trim();

String? _websiteUrl(String inner) {
  var url = inner.trim().replaceFirst(
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
  return url;
}

String? _docQuery(String inner) {
  final trimmed = inner.trim();
  // File-manager phrasing ("open my files") is not a document request.
  if (RegExp(
    r'^(my |the )?files?( and .*)?$',
    caseSensitive: false,
  ).hasMatch(trimmed)) {
    return null;
  }
  final name = trimmed
      .replaceFirst(RegExp(r'^(?:the |my |a |an )', caseSensitive: false), '')
      .replaceFirst(
        RegExp(
          r'^(?:file |document )(?:named |called )?',
          caseSensitive: false,
        ),
        '',
      )
      .replaceAll(RegExp(r'\s+dot\s+', caseSensitive: false), '.')
      .trim();
  return name.isEmpty ? null : name;
}

String _cleanNoteName(String raw) {
  var name = raw.trim().replaceAll(
    RegExp(r'\s+dot\s+', caseSensitive: false),
    '.',
  );
  if (name.length >= 2 &&
      (name.startsWith('"') && name.endsWith('"') ||
          name.startsWith("'") && name.endsWith("'"))) {
    name = name.substring(1, name.length - 1).trim();
  }
  return name;
}

/// Recognizes supported actions only; other speech stays ordinary conversation.
ComputerCommand? parseComputerCommand(String speech) {
  var text = speech
      .trim()
      .replaceAll(RegExp(r'[.!?]+$'), '')
      .replaceFirst(RegExp(r'\s+please\s*$', caseSensitive: false), '');
  text = text.replaceFirst(
    RegExp(r'^(hey\s+pico[, ]*|pico[, ]*|please\s+)', caseSensitive: false),
    '',
  );
  text = text.replaceFirst(
    RegExp(r'^(can you|could you|would you|will you)\s+', caseSensitive: false),
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
  if (RegExp(
    r'^(?:list|show) (?:my )?files$',
    caseSensitive: false,
  ).hasMatch(text)) {
    return command('list_files', {'path': '.'});
  }
  final read = RegExp(r'^read (.+)$', caseSensitive: false).firstMatch(text);
  if (read != null) {
    return command('read_file', {'path': read.group(1)!.trim()});
  }
  final run = RegExp(
    r'^run command (\[.+\])$',
    caseSensitive: false,
  ).firstMatch(text);
  if (run != null) {
    try {
      final argv = jsonDecode(run.group(1)!);
      if (argv is List && argv.isNotEmpty && argv.every((a) => a is String)) {
        return command('run_command', {'argv': argv});
      }
    } catch (_) {}
    return null;
  }
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
  final organize = RegExp(
    r'^(?:open my files and )?(?:arrange|organize|organise|gather|collect|put)'
    r'\s+(?:all\s+)?(?:the\s+|my\s+)?photos?\s+(?:in(?:to)?|to)\s+'
    r'(?:one single |a single |one |a )?(?:folder\s+)?(?:named|called)\s+(.+?)'
    r"(?:\s+and\s+i\s+don'?t\s+want\s+any\s+duplicates"
    r'|\s+without\s+(?:any\s+)?duplicates'
    r'|\s+with\s+no\s+duplicates)?\s*$',
    caseSensitive: false,
  ).firstMatch(text);
  if (organize != null) {
    final folder = _cleanNoteName(organize.group(1)!);
    if (folder.isNotEmpty) {
      return command('organize_photos', {'folder': folder});
    }
  }
  final open = RegExp(r'^open\s+(.+)$', caseSensitive: false).firstMatch(text);
  if (open != null) {
    final url = _websiteUrl(open.group(1)!);
    if (url != null) return command('open_website', {'url': url});
    final query = _docQuery(open.group(1)!);
    if (query != null) return command('open_document', {'query': query});
    return null;
  }
  final visit = RegExp(
    r'^(?:visit|go to|browse)\s+(.+)$',
    caseSensitive: false,
  ).firstMatch(text);
  if (visit != null) {
    final url = _websiteUrl(visit.group(1)!);
    if (url == null) return null;
    return command('open_website', {'url': url});
  }
  final folderSuffix = RegExp(
    r'\s+in (?:my |the )?(?:project folder|project|notes folder)$',
    caseSensitive: false,
  );
  final noteText = text.replaceFirst(folderSuffix, '');
  final steer = RegExp(
    r'^(?:rename (?:it|that|the note) to|change (?:the |that |my )?filename to|actually call it)\s+(.+)$',
    caseSensitive: false,
  ).firstMatch(noteText);
  if (steer != null) {
    final name = _cleanNoteName(steer.group(1)!);
    if (name.isNotEmpty) return command('steer_output', {'path': name});
  }
  final note = RegExp(
    r'^(?:create|make|write)\s+(?:a\s+)?(?:note|(?:text\s+)?file)\s+(?:(?:named|called)\s+)?(.+?)(?:\s+(?:saying|containing|with contents?)\s+(.+))?$',
    caseSensitive: false,
  ).firstMatch(noteText);
  if (note != null) {
    final name = _cleanNoteName(note.group(1)!);
    if (name.isNotEmpty) {
      return command('create_note', {
        'name': name,
        'text': (note.group(2) ?? '').trim(),
      });
    }
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
