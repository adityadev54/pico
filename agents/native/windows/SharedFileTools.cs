using System.Text.Json.Nodes;
internal static class SharedFileTools {
 internal static readonly string[] Names=["delete_files","restore_deleted","archive","empty_trash","convert_file","pdf_pages"];
 internal static async Task<JsonObject> Execute(JsonObject p,FileAccess access,WorkflowRuntime runtime,Func<JsonObject,bool> approve,Func<string,JsonObject,Task<JsonObject>> api,CancellationToken cancel) {
  var outcome=new JsonObject{["task_id"]=p["task_id"]!.DeepClone(),["call_id"]=p["call_id"]!.DeepClone()};
  try {
   string tool=p["tool"]!.GetValue<string>();bool deletion=tool is "delete_files" or "empty_trash";
   void Validate(){cancel.ThrowIfCancellationRequested();if(!long.TryParse(p["expires_at"]?.GetValue<string>(),out long expires)||expires<DateTimeOffset.UtcNow.ToUnixTimeMilliseconds())throw new InvalidOperationException("Request expired.");}
   Validate();var started=await api("/agent/start",new(){["task_id"]=p["task_id"]!.DeepClone()});
   if(started["cancelled"]?.GetValue<bool>()==true)throw new OperationCanceledException();
   var grant=access.Grants.SingleOrDefault(g=>g.Id==p["grant_id"]?.GetValue<string>()&&FolderAccessStore.Usable(g));
   if(grant==null||!(deletion?grant.Access=="delete":grant.Access is "write" or "delete"))throw new InvalidOperationException("Choose a folder with the required permission.");
   var review=(JsonObject)p.DeepClone();review["workspace"]=grant.Path;
   // Permanent empty always requires a local explicit review, even after phone approval.
   if((tool=="empty_trash"||started["phone_approved"]?.GetValue<bool>()!=true)&&!approve(review))throw new InvalidOperationException("Not approved on this computer.");
   Validate();
   var result=await runtime.Call(new(){["operation"]="tool",["payload"]=p.DeepClone()},async(kind,body)=> {
    Validate();if(kind=="cancelled")return JsonValue.Create(cancel.IsCancellationRequested);
    if(kind!="grants")throw new InvalidOperationException("Unsupported callback.");
    if((await api("/agent/start",new(){["task_id"]=p["task_id"]!.DeepClone()}))["cancelled"]?.GetValue<bool>()==true)throw new OperationCanceledException();
    return new JsonArray(access.Grants.Where(FolderAccessStore.Usable).Select(g=>(JsonNode)new JsonObject{["id"]=g.Id,["path"]=g.Path,["access"]=g.Access}).ToArray());
   },cancel);
   outcome["status"]="succeeded";outcome["message"]="Request finished.";
   outcome["data_json"]=Bounded(result["data"]);outcome["evidence_json"]=Bounded(result["evidence"]);
  }catch(Exception e){outcome["status"]="failed";outcome["error_code"]=e is OperationCanceledException?"cancelled":"request_failed";outcome["message"]=e.Message[..Math.Min(200,e.Message.Length)];}
  return outcome;
 }
 static string Bounded(JsonNode? value){string text=value?.ToJsonString()??"{}";return text.Length<=2000?text:"{\"truncated\":true}";}
}
