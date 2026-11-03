using System.Text.Json.Nodes;
internal static class FocusGate {
 internal static bool Active(JsonObject state)=>state["focused"]?.GetValue<bool>()==true;
 internal static bool MayRun(string kind,JsonObject data)=>kind switch {
  "open_app"=>false,
  "tool_call"=>data["tool"]?.GetValue<string>() is "search_documents" or "fs_read" or "fs_list" or "read_back_file" or "transfer_selected_file",
  "skill_request"=>data["query"]?.GetValue<string>()!="teach",
  _=>true
 };
 internal static void Hold(JsonObject state,string text,string? identity=null) {
  string key="result:"+(identity??text);
  var places=state["places"]!.AsObject();
  if(places[key]==null)places[key]=new JsonObject{["sentence"]=text,["status"]="ready",["local_result"]=true};
 }
}
