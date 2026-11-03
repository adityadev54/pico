using System.Text.Json.Nodes;
internal static class SafeTaskExecution {
 internal static JsonObject? ResolveApprovedAppDocument(JsonObject payload,AppAccessSettings apps) {
  if(payload["tool"]?.GetValue<string>()!="open_document")return null;
  var matches=apps.MatchName(payload["query"]?.GetValue<string>()??"");
  if(matches.Count!=1)return null;
  var selected=matches[0];var request=(JsonObject)payload.DeepClone();request["tool"]="open_app";request["app_id"]=selected.Id;
  var result=Execute(request,apps);
  if(result["status"]?.GetValue<string>()=="succeeded")result["data_json"]=new JsonObject{["name"]=selected.Name,["opened_as"]="approved_app",["opened_app_id"]=selected.Id}.ToJsonString();
  return result;
 }
 internal static JsonObject Execute(JsonObject payload, AppAccessSettings apps) {
  var result=new JsonObject { ["task_id"]=payload["task_id"]?.DeepClone(), ["call_id"]=payload["call_id"]?.DeepClone() };
  if(payload["tool"]?.GetValue<string>()!="open_app") {
   result["status"]="failed";result["error_code"]="unsupported_tool";
   result["message"]="This tool is not enabled in the Windows companion yet.";return result;
  }
  string name=payload["app_id"]?.GetValue<string>() ?? payload["app"]?.GetValue<string>() ?? "";
  var byId=apps.Allowed.FirstOrDefault(a=>a.Id==name);
  var matches=byId!=null?new[]{byId}:apps.MatchName(name,true).ToArray();
  if(matches.Length>1){result["status"]="failed";result["error_code"]="ambiguous_app";result["message"]="More than one approved app matches. Choose it from your app list.";return result;}
  var app=matches.SingleOrDefault();
  var opened=app==null ? new AppOpenResult(false,"Approve this app in the computer’s Open apps menu first.") : apps.Open(app.Id,payload["expires_at"]?.GetValue<string>() ?? "0");
  result["status"]=opened.Opened?"succeeded":"failed";result["message"]=opened.Message;
  if(opened.Opened){result["data_json"]=new JsonObject{["app"]=app!.Name}.ToJsonString();result["evidence_json"]="{}";}
  else result["error_code"]="permission_denied";
  return result;
 }
}
