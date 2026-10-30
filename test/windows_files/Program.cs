using System.Text.Json.Nodes;
using System.Security.Cryptography;
internal sealed class FileAccess(string path):FolderAccessStore(path){}
static class Checks {
 static int count;
 static void Check(bool condition,string message){if(!condition)throw new Exception(message);count++;}
 static string S(JsonObject p,string key)=>p[key]?.GetValue<string>()??"";
 static string Hash(byte[] b)=>Convert.ToHexString(SHA256.HashData(b)).ToLowerInvariant();
 static async Task Main(){
  var root=Path.Combine((OperatingSystem.IsMacOS()?"/private/tmp":Path.GetTempPath()),"pico-win-workflow-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(root);
  try{
   var folder=Path.Combine(root,"files");Directory.CreateDirectory(folder);var access=new FileAccess(Path.Combine(root,"grants.json"));access.Add(folder,"read");var transfers=new Dictionary<string,JsonObject>();bool phoneApproved=false;
   async Task<JsonObject> Api(string path,JsonObject p){await Task.CompletedTask;if(path=="/agent/start")return new(){["cancelled"]=false,["phone_approved"]=phoneApproved};if(path=="/agent/transfer"){transfers[S(p,"task_id")]=(JsonObject)p.DeepClone();return new();}if(path=="/agent/artifact"){var bytes=System.Text.Encoding.UTF8.GetBytes("phone upload");return new(){["content_base64"]=Convert.ToBase64String(bytes),["digest"]=Hash(bytes)};}throw new Exception(path);}
   async Task<JsonObject> Run(string tool,JsonObject args,bool approved=true,CancellationToken stop=default){var p=(JsonObject)args.DeepClone();p["tool"]=tool;p["task_id"]=Guid.NewGuid().ToString();p["call_id"]=Guid.NewGuid().ToString();p["expires_at"]=DateTimeOffset.UtcNow.AddMinutes(1).ToUnixTimeMilliseconds().ToString();return await FileTaskExecution.Execute(p,access,_=>approved,Api,stop);}
   File.WriteAllText(Path.Combine(folder,"brief.txt"),"Synthetic brief");
   var search=await Run("search_documents",new(){["query"]="brief"});Check(S(search,"status")=="succeeded","search");var found=JsonNode.Parse(S(search,"data_json"))!["candidates"]![0]!.AsObject();
   var read=await Run("read_back_file",new(){["candidate_id"]=found["candidate_id"]!.DeepClone()});Check(S(read,"status")=="succeeded","read");Check(JsonNode.Parse(S(read,"data_json"))!["excerpt"]!.GetValue<string>()=="Synthetic brief","actual excerpt");
   var selected=new JsonObject{["candidate_id"]=found["candidate_id"]!.DeepClone(),["expected_digest"]=found["digest"]!.DeepClone(),["expected_size"]=found["size_bytes"]!.GetValue<long>().ToString(),["approval_id"]="approval"};
   var sent=await Run("transfer_selected_file",selected);Check(S(sent,"status")=="succeeded"&&transfers.Count==1,"transfer bytes");File.WriteAllText(Path.Combine(folder,"brief.txt"),"changed");Check(S(await Run("transfer_selected_file",selected),"error_code")=="candidate_changed","changed file denied");
   Check(S(await Run("fs_write",new(){["path"]="note.txt",["content"]="hello"}),"status")=="failed","read-only denies writes");
   access.Add(folder,"write");Check(S(await Run("fs_write",new(){["path"]="note.txt",["content"]="hello"},false),"status")=="failed","local approval required");
   var saved=await Run("fs_write",new(){["path"]="note.txt",["content"]="hello"});Check(S(saved,"status")=="succeeded","write");Check(S(await Run("fs_write",new(){["path"]="note.txt",["content"]="overwrite"}),"error_code")=="candidate_changed","no unreviewed overwrite");
   var revision=JsonNode.Parse(S(saved,"data_json"))!["digest"]!.GetValue<string>();Check(S(await Run("fs_write",new(){["path"]="note.txt",["content"]="revised",["base_revision"]=revision}),"status")=="succeeded","revision edit");
   Check(S(await Run("fs_read",new(){["path"]="../outside"}),"status")=="failed","path escape");
   var bytes=System.Text.Encoding.UTF8.GetBytes("phone upload");Check(S(await Run("fetch_upload",new(){["artifact_id"]=Hash(bytes),["path"]="phone.txt"}),"status")=="succeeded","phone upload");
   File.WriteAllBytes(Path.Combine(folder,"a.jpg"),[1,2,3]);File.WriteAllBytes(Path.Combine(folder,"b.png"),[1,2,3]);var photos=await Run("organize_photos",new(){["folder"]="ReviewPhotos"});var data=JsonNode.Parse(S(photos,"data_json"))!;Check(data["copied_count"]!.GetValue<int>()==1&&data["duplicates_skipped"]!.GetValue<int>()==1,"photo dedupe");Check(File.Exists(Path.Combine(folder,"a.jpg")),"original preserved");
   Check(S(await Run("process_run",new(){["argv_json"]="[\"sh\",\"-c\",\"echo bad\"]"}),"status")=="failed","shell denied");
   phoneApproved=true;
   Check(S(await Run("fs_write",new(){["path"]="phone-approved.txt",["content"]="one approval"},false),"status")=="succeeded","server verified phone approval needs no desktop prompt");
   access.Add(folder,"read");
   Check(S(await Run("fs_write",new(){["path"]="blocked.txt",["content"]="no"},false),"status")=="failed","phone approval cannot bypass revoked write access");
   var blocked=await Run("search_documents",new(){["query"]="brief"},stop:new CancellationToken(true));Check(S(blocked,"error_code")=="cancelled","cancel before work");
   Console.WriteLine($"Passed {count} Windows workflow checks using actual production file-handler code on synthetic files. Native UI and physical Windows still need device testing.");
  }finally{Directory.Delete(root,true);}
 }
}
