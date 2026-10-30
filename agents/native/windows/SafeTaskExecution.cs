using System.Text.Json.Nodes;
internal static class SafeTaskExecution {
 internal static JsonObject Execute(JsonObject payload, AppAccessSettings apps) {
  var result=new JsonObject { ["task_id"]=payload["task_id"]?.DeepClone(), ["call_id"]=payload["call_id"]?.DeepClone() };
  if(payload["tool"]?.GetValue<string>()!="open_app") {
   result["status"]="failed";result["error_code"]="unsupported_tool";
   result["message"]="This tool is not enabled in the Windows companion yet.";return result;
  }
  string name=payload["app_id"]?.GetValue<string>() ?? payload["app"]?.GetValue<string>() ?? "";
  var app=apps.Allowed.FirstOrDefault(a=>a.Id==name || string.Equals(a.Name,name,StringComparison.OrdinalIgnoreCase));
  var opened=app==null ? new AppOpenResult(false,"Approve this app in the computer’s Open apps menu first.") : apps.Open(app.Id,payload["expires_at"]?.GetValue<string>() ?? "0");
  result["status"]=opened.Opened?"succeeded":"failed";result["message"]=opened.Message;
  if(opened.Opened){result["data_json"]=new JsonObject{["app"]=app!.Name}.ToJsonString();result["evidence_json"]="{}";}
  else result["error_code"]="permission_denied";
  return result;
 }
}
