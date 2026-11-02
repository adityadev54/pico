"""Pico workflow metadata over the existing shared task-kind constraint."""
KINDS={'find_document','send_file','open_website','open_app','manage_permissions','summarize_document','read_document','create_note','receive_upload','organize_photos','open_document','list_files','read_file','edit_file','run_command','rename_file','duplicate_file','archive','recent_files','search_contents','find_duplicates','largest_files','undo_edit','empty_trash','disk_usage'}
def view(row):
 result=dict(row);source=result.get('input') or {};kind=source.get('_pico_kind')
 if result.get('kind')=='open_app' and kind in KINDS:result['kind']=kind
 if result.get('kind')=='send_file' and result.get('status')=='working' and (result.get('result') or {}).get('artifact_id'):result['status']='verifying'
 return result
