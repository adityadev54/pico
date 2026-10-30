Map<String, dynamic> picoTaskView(Map<String, dynamic> row) {
  final task = Map<String, dynamic>.from(row);
  final input = task['input'];
  if (task['kind'] == 'open_app' &&
      input is Map &&
      input['_pico_kind'] is String) {
    const kinds = {
      'find_document',
      'send_file',
      'open_website',
      'manage_permissions',
      'summarize_document',
      'read_document',
      'create_note',
      'receive_upload',
      'organize_photos',
      'open_document',
      'list_files',
      'read_file',
      'edit_file',
      'run_command',
    };
    if (kinds.contains(input['_pico_kind'])) task['kind'] = input['_pico_kind'];
  }
  final result = task['result'];
  if (task['kind'] == 'send_file' &&
      task['status'] == 'working' &&
      result is Map &&
      result['artifact_id'] != null) {
    task['status'] = 'verifying';
  }
  return task;
}
