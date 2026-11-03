using System.Security.Cryptography;
using System.Text;
using System.Text.Json.Nodes;
sealed partial class Companion {
 TeachWindow? teachWindow;bool skillBusy;
 async Task<JsonNode> SkillCall(JsonObject request) {
  string? account=token;if(account==null)throw new InvalidOperationException("Connect your phone first.");
  request["directory"]=Path.Combine(Program.Folder,"routines",Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(account)))[..24]);
  string op=request["operation"]!.GetValue<string>();
  if(op is "finish" or "run"){SetCharacter(current??"tuck",op=="finish"?"curious":"working");moodUntil=DateTimeOffset.UtcNow.AddSeconds(90).ToUnixTimeMilliseconds();}
  try {
   var result=await workflow.Call(request,async(kind,body)=> {
    if(token!=account)throw new InvalidOperationException("Paired account changed; result discarded.");
    if(kind=="grants") {
     var (accessCode,_)=await Api("/agent/ack",new(){["ids"]=new JsonArray()});
     if(accessCode!=System.Net.HttpStatusCode.OK)throw new InvalidOperationException("This computer is no longer connected. Nothing was saved.");
     return new JsonArray(fileAccess.Grants.Where(FolderAccessStore.Usable).Select(g=>(JsonNode)new JsonObject{["id"]=g.Id,["path"]=g.Path,["access"]=g.Access}).ToArray());
    }
    if(kind!="model")throw new InvalidOperationException("Unsupported callback.");
    var (code,value)=await Api("/agent/skills/model",body);if(code!=System.Net.HttpStatusCode.OK)throw new InvalidOperationException(value["error"]?.ToString()??"Muse couldn’t finish. No automatic retry was made.");
    if(token!=account)throw new InvalidOperationException("Paired account changed; result discarded.");return value;
   });
   if(op is "finish" or "run"){SetCharacter(current??"tuck","happy");moodUntil=DateTimeOffset.UtcNow.AddSeconds(4).ToUnixTimeMilliseconds();}return result;
  }catch{SetCharacter(current??"tuck","angry");moodUntil=DateTimeOffset.UtcNow.AddSeconds(4).ToUnixTimeMilliseconds();throw;}
 }
 void PublishSkills(JsonArray rows,string request,string status,string message) {
  var safe=new JsonArray();foreach(var row in rows.Take(12)){var copy=(JsonObject)row!.DeepClone();copy.Remove("root");safe.Add(copy);}
  while(safe.ToJsonString().Length>5900&&safe.Count>0)safe.RemoveAt(safe.Count-1);
  state["outgoing"]!.AsArray().Add(new JsonObject{["id"]=Guid.NewGuid().ToString(),["kind"]="skill_result",["payload"]=new JsonObject{["request_id"]=request,["status"]=status,["message"]=message[..Math.Min(1200,message.Length)],["catalog"]=safe.ToJsonString()}});Save();
 }
 void ShowTeach(){if(teachWindow is {IsDisposed:false}){teachWindow.Activate();return;}teachWindow=new TeachWindow(fileAccess,SkillCall,PublishSkills);teachWindow.Show(this);}
 async Task ReceiveSkill(string mail,JsonObject p) {
  string request=p["request_id"]!.GetValue<string>();
  // Persist before any paid request. Mail replay cannot repeat a model call.
  state["handled"]!.AsArray().Add(mail);Save();
  try {
   if(!long.TryParse(p["expires_at"]?.GetValue<string>(),out long expires)||expires<DateTimeOffset.UtcNow.ToUnixTimeMilliseconds())throw new InvalidOperationException("Request expired; nothing ran.");
   string query=p["query"]!.GetValue<string>();if(query=="teach"){ShowTeach();PublishSkills(new(),request,"ready","Choose files and show Pico an example on your computer.");return;}
   if(query=="catalog"){PublishSkills((await SkillCall(new(){["operation"]="catalog"})).AsArray(),request,"catalog","");return;}
   if(skillBusy||teachWindow is {IsDisposed:false,IsTeaching:true})throw new InvalidOperationException("Finish the current teaching window before running from your phone.");
   if(!query.StartsWith("run:"))throw new InvalidOperationException("Unknown routine request.");
   skillBusy=true;await SkillCall(new(){["operation"]="run",["id"]=query[4..],["request_id"]=request});
   PublishSkills((await SkillCall(new(){["operation"]="catalog"})).AsArray(),request,"completed","Result saved and verified on your computer.");
  }catch(Exception e){PublishSkills(new(),request,"failed",e.Message);}finally{skillBusy=false;}
 }
}
