import 'dart:convert';

import '../models/computer_command.dart';

/// True when the text uses command language (addressing Pico, a request
/// verb) even if [parseComputerCommand] recognizes no supported action.
/// Used to explain the miss instead of failing silently as a note.
bool looksLikeCommand(String speech) {
  return RegExp(
    r'^(hey pico|pico|please|can you|could you|would you|will you|open|launch|start|find|search|look for|locate|send|transfer|bring|share|summari[sz]e|google|visit|go to|browse|manage|show|ask (?:pico|picko|piko)|draft|create|make|write|rename|change|arrange|organize|organise|gather|collect|convert|turn|delete|remove|trash|restore|undelete|play|riddle|puzzle|timer|remind|merge|split|rotate|watermark|unlock|extract|duplicate|zip|unzip|compress|recent|undo|empty|disk|storage)\b',
    caseSensitive: false,
  ).hasMatch(speech.trim());
}

/// Common speech transcriptions retain the explicit Ask Pico opt-in.
String? museRequestText(String speech) => RegExp(
  r'^ask\s+(?:pico|picko|piko)[: ,]+(.+)$',
  caseSensitive: false,
).firstMatch(speech.trim())?.group(1)?.trim();

const _picoGreetingReply =
    'Hey!! So good to see you! I’m ready to run your computer — '
    'ask me to open something, find a file, or say “what can you do?”';

const _picoCapabilitiesIntro =
    'I run your computer from your phone: open apps and files (“open chrome”), '
    'find documents (“find my brief”), gather photos into one folder, convert files '
    '(“convert scan.jpg to pdf”), edit PDF pages (“merge a.pdf and b.pdf”), move files '
    'to trash and bring them back, rename, duplicate, zip and unzip, show recent, '
    'duplicate or largest files, search inside files, undo edits, empty trash, check '
    'disk usage, create notes, and open websites. I can also play a '
    'guessing game, ask riddles, and set timers and reminders right here. Connect a '
    'computer in Devices then just tell me what to do!';

/// Local small-talk Pico answers itself, with no computer needed:
/// greetings and "what can you do". Returns the reply, or null.
String? picoSmallTalk(String speech) {
  final text = speech.trim().toLowerCase().replaceAll(
    RegExp(r'[.!?\s]+$'),
    '',
  );
  if (text.isEmpty) return null;
  final bare = text
      .replaceFirst(
        RegExp(
          r'^(hi|hey|hello|hiya|yo|good morning|good afternoon|good evening)[, ]*',
        ),
        '',
      )
      .replaceFirst(RegExp(r'^pico[, ]*'), '')
      .trim();
  if (bare.isEmpty) return _picoGreetingReply;
  if (RegExp(
    r'^(what can you do|what do you do|who are you|what are you|help( me)?|what are your features|list your features|capabilities|what can i ask( you)?)$',
  ).hasMatch(bare)) {
    return _picoCapabilitiesIntro;
  }
  return null;
}

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
    // A bare "name.ext" is a file, not a site (report.pdf must open the
    // document, not https://report.pdf). Paths under a real host stay URLs.
    const fileExtensions = {
      'pdf',
      'doc',
      'docx',
      'odt',
      'rtf',
      'xls',
      'xlsx',
      'csv',
      'ods',
      'ppt',
      'pptx',
      'key',
      'odp',
      'txt',
      'md',
      'rst',
      'jpg',
      'jpeg',
      'png',
      'gif',
      'webp',
      'bmp',
      'tif',
      'tiff',
      'heic',
      'zip',
      'tar',
      'gz',
      'rar',
      '7z',
      'dmg',
      'exe',
      'mp3',
      'mp4',
      'mov',
    };
    final host = url.split('/').first.toLowerCase();
    if (host.contains('.') && fileExtensions.contains(host.split('.').last)) {
      return null;
    }
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

/// Parses iLovePDF-style page edits into pdf_pages tool input, or null.
Map<String, dynamic>? _parsePdfPages(String text) {
  List<String> files(String raw) => splitDeleteNames(raw);
  var match = RegExp(
    r'^merge\s+(.+?)(?:\s+into\s+(\S+))?$',
    caseSensitive: false,
  ).firstMatch(text);
  if (match != null) {
    final paths = files(match.group(1)!);
    if (paths.length < 2) return null;
    return {
      'action': 'merge',
      'paths': paths,
      if (match.group(2) != null) 'output': match.group(2)!,
    };
  }
  match = RegExp(
    r'^split\s+(.+?)\s+pages?\s+([\d,\-\s]+)$',
    caseSensitive: false,
  ).firstMatch(text);
  if (match != null) {
    return {
      'action': 'split',
      'paths': files(match.group(1)!),
      'pages': match.group(2)!.trim(),
    };
  }
  match = RegExp(
    r'^extract\s+pages?\s+([\d,\-\s]+?)\s+from\s+(.+)$',
    caseSensitive: false,
  ).firstMatch(text);
  if (match != null) {
    return {
      'action': 'split',
      'paths': files(match.group(2)!),
      'pages': match.group(1)!.trim(),
    };
  }
  match = RegExp(
    r'^rotate\s+(.+?)\s+(\d+)\s*degrees?$',
    caseSensitive: false,
  ).firstMatch(text);
  if (match != null) {
    return {
      'action': 'rotate',
      'paths': files(match.group(1)!),
      'angle': int.parse(match.group(2)!),
    };
  }
  match = RegExp(
    r'^delete\s+pages?\s+([\d,\-\s]+?)\s+from\s+(.+)$',
    caseSensitive: false,
  ).firstMatch(text);
  if (match != null) {
    return {
      'action': 'delete',
      'paths': files(match.group(2)!),
      'pages': match.group(1)!.trim(),
    };
  }
  match = RegExp(
    r'^(?:watermark|stamp)\s+(.+?)\s+with\s+["\u201c]?(.+?)["\u201d]?$',
    caseSensitive: false,
  ).firstMatch(text);
  if (match != null) {
    return {
      'action': 'watermark',
      'paths': files(match.group(1)!),
      'watermark': match.group(2)!.trim(),
    };
  }
  match = RegExp(
    r'^unlock\s+(.+?)\s+with\s+password\s+(.+)$',
    caseSensitive: false,
  ).firstMatch(text);
  if (match != null) {
    return {
      'action': 'unlock',
      'paths': files(match.group(1)!),
      'password': match.group(2)!.trim(),
    };
  }
  match = RegExp(
    r'^(?:convert|save|export)\s+(.+?)\s+to\s+images?$',
    caseSensitive: false,
  ).firstMatch(text);
  if (match != null) {
    return {
      'action': 'images',
      'paths': files(match.group(1)!),
    };
  }
  return null;
}

List<String> splitDeleteNames(String raw) {
  return raw
      .split(RegExp(r'\s*(?:,|\band\b)\s*', caseSensitive: false))
      .map(
        (part) => part
            .trim()
            .replaceFirst(
              RegExp(r'^(?:the |my |a |an )', caseSensitive: false),
              '',
            )
            .replaceFirst(
              RegExp(
                r'^(?:note|file|document)(?: named| called)? ',
                caseSensitive: false,
              ),
              '',
            )
            .replaceAll(RegExp(r'''^["']|["']$'''), '')
            .trim(),
      )
      .where((part) => part.isNotEmpty)
      .toList();
}

String _cleanFileName(String raw) {
  return raw
      .trim()
      .replaceFirst(
        RegExp(r'^(?:the |my |a |an )', caseSensitive: false),
        '',
      )
      .replaceFirst(
        RegExp(
          r'^(?:file |document )(?:named |called )?',
          caseSensitive: false,
        ),
        '',
      )
      .replaceAll(RegExp(r'\s+dot\s+', caseSensitive: false), '.')
      .replaceAll(RegExp(r'''^["']|["']$'''), '')
      .trim();
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
    RegExp(
      r'^(hey\s+pico[, ]*|hello[, ]*|pico[, ]*|please\s+)',
      caseSensitive: false,
    ),
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
    r'^(?:open|launch|start)\s+(?:the\s+)?(calculator|calendar|chrome|google chrome|safari|firefox|mozilla firefox|edge|microsoft edge|finder|my files|files|file explorer|file manager|explorer|terminal|mail|photos|music|notes|sticky notes|messages|facetime|maps|settings|system settings|system preferences|app store|vs\s*code|visual studio code|word|excel|powerpoint|browser|default browser)(?: app)?$',
    caseSensitive: false,
  ).firstMatch(text);
  if (appMatch != null) {
    final app = appMatch.group(1)!.toLowerCase().replaceAll(' ', '');
    return command('open_app', {
      'app': switch (app) {
        'googlechrome' => 'chrome',
        'mozillafirefox' => 'firefox',
        'microsoftedge' => 'edge',
        'finder' ||
        'myfiles' ||
        'files' ||
        'fileexplorer' ||
        'filemanager' ||
        'explorer' => 'files',
        'systemsettings' || 'systempreferences' => 'settings',
        'appstore' => 'appstore',
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
  final convert = RegExp(
    r'^(?:convert|turn|change)\s+(.+?)\s+to\s+(pdf|word(?: document)?|docx|text|txt|png|jpe?g|webp)$',
    caseSensitive: false,
  ).firstMatch(text);
  if (convert != null) {
    var name = convert
        .group(1)!
        .replaceFirst(
          RegExp(r'^(?:the |my |a |an )', caseSensitive: false),
          '',
        )
        .trim();
    var format = convert.group(2)!.toLowerCase();
    if (format == 'word' || format == 'word document') format = 'docx';
    if (format == 'text') format = 'txt';
    if (format == 'jpeg') format = 'jpg';
    if (name.isNotEmpty) {
      return command('convert_file', {'path': name, 'to': format});
    }
  }
  // PDF page edits come before file delete: "delete pages 1-2" is not trash.
  final pdf = _parsePdfPages(text);
  if (pdf != null) return command('pdf_pages', pdf);
  final remove = RegExp(
    r'^(?:delete|remove|trash)\s+(.+)$',
    caseSensitive: false,
  ).firstMatch(text);
  if (remove != null) {
    final names = splitDeleteNames(remove.group(1)!);
    if (names.isNotEmpty) return command('delete_files', {'names': names});
  }
  final rename = RegExp(
    r'^rename\s+(.+?)\s+to\s+(.+)$',
    caseSensitive: false,
  ).firstMatch(text);
  if (rename != null) {
    final from = _docQuery(rename.group(1)!);
    final to = _cleanFileName(rename.group(2)!);
    if (from != null && to.isNotEmpty) {
      return command('rename_file', {'path': from, 'new_name': to});
    }
  }
  final duplicate = RegExp(
    r'^(?:duplicate|make a copy of)\s+(.+)$',
    caseSensitive: false,
  ).firstMatch(text);
  if (duplicate != null) {
    final query = _docQuery(duplicate.group(1)!);
    if (query != null) return command('duplicate_file', {'path': query});
  }
  final zip = RegExp(
    r'^(?:zip|compress)\s+(.+?)(?:\s+as\s+(\S+))?$',
    caseSensitive: false,
  ).firstMatch(text);
  if (zip != null) {
    final paths = splitDeleteNames(zip.group(1)!);
    if (paths.isNotEmpty) {
      return command('archive', {
        'action': 'create',
        'paths': paths,
        if (zip.group(2) != null) 'output': _cleanNoteName(zip.group(2)!),
      });
    }
  }
  final unzip = RegExp(
    r'^unzip\s+(.+?)(?:\s+to\s+(.+))?$',
    caseSensitive: false,
  ).firstMatch(text);
  if (unzip != null) {
    final paths = splitDeleteNames(unzip.group(1)!);
    if (paths.isNotEmpty) {
      return command('archive', {
        'action': 'extract',
        'paths': paths,
        if (unzip.group(2) != null)
          'output': _cleanNoteName(unzip.group(2)!),
      });
    }
  }
  if (RegExp(
    r'^(?:show(?: me)? )?(?:my )?recent files?$',
    caseSensitive: false,
  ).hasMatch(text)) {
    return command('recent_files', {});
  }
  final recentDays = RegExp(
    r'^recent files from (?:the )?last (\d+) days?$',
    caseSensitive: false,
  ).firstMatch(text);
  if (recentDays != null) {
    return command('recent_files', {
      'days': int.parse(recentDays.group(1)!),
    });
  }
  final inside = RegExp(
    r'^(?:find files containing|search (?:inside|in) files for|which file contains)\s+(.+)$',
    caseSensitive: false,
  ).firstMatch(text);
  if (inside != null) {
    final query = inside
        .group(1)!
        .replaceAll(RegExp(r'\s+dot\s+', caseSensitive: false), '.')
        .trim();
    if (query.isNotEmpty) return command('search_contents', {'query': query});
  }
  if (RegExp(
    r'^(?:duplicates?|(?:find|show|list)(?: my)? duplicates?(?: files?)?)$',
    caseSensitive: false,
  ).hasMatch(text)) {
    return command('find_duplicates', {});
  }
  if (RegExp(
    r'^(?:(?:show|list)(?: my)? )?(largest|biggest) files?$',
    caseSensitive: false,
  ).hasMatch(text)) {
    return command('largest_files', {});
  }
  final undo = RegExp(
    r'^undo (?:changes|edit|the last change|the last edit)(?: to| on)? (.+)$',
    caseSensitive: false,
  ).firstMatch(text);
  if (undo != null) {
    final query = _docQuery(undo.group(1)!);
    if (query != null) return command('undo_edit', {'path': query});
  }
  if (RegExp(
    r'^empty (?:pico )?trash$',
    caseSensitive: false,
  ).hasMatch(text)) {
    return command('empty_trash', {'confirm': 'EMPTY'});
  }
  if (RegExp(
    r'^(?:(?:disk|storage) usage|how much (?:disk )?space(?: do i have| is used| am i using)?)$',
    caseSensitive: false,
  ).hasMatch(text)) {
    return command('disk_usage', {});
  }
  final restore = RegExp(
    r'^(?:restore|undelete|bring back)\s+(.+)$',
    caseSensitive: false,
  ).firstMatch(text);
  if (restore != null) {
    final name = splitDeleteNames(restore.group(1)!);
    if (name.isNotEmpty) {
      return command('restore_deleted', {'name': name.first});
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
