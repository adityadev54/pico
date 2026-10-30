using System.Diagnostics;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json.Nodes;
internal static class FileTaskExecution {
 static string S(JsonObject p,string k,string fallback="")=>p[k]?.GetValue<string>()??fallback;
 static string Digest(byte[] raw)=>Convert.ToHexString(SHA256.HashData(raw)).ToLowerInvariant();
 static string HashFile(string path){using var stream=File.OpenRead(path);return Convert.ToHexString(SHA256.HashData(stream)).ToLowerInvariant();}
 static string Candidate(string path)=>new Guid(SHA256.HashData(Encoding.UTF8.GetBytes(Path.GetFullPath(path).ToLowerInvariant()))[..16]).ToString();
 static IEnumerable<string> Files(FolderGrant g)=>Directory.EnumerateFiles(g.Path,"*",new EnumerationOptions{RecurseSubdirectories=true,IgnoreInaccessible=true,AttributesToSkip=FileAttributes.Hidden|FileAttributes.ReparsePoint}).Take(10000);
 internal static async Task<JsonObject> Execute(JsonObject p,FileAccess access,Func<JsonObject,bool> approve,Func<string,JsonObject,Task<JsonObject>> api,CancellationToken cancel) {
  var result=new JsonObject{["task_id"]=p["task_id"]?.DeepClone(),["call_id"]=p["call_id"]?.DeepClone()};string tool=S(p,"tool");
  try {
   if(!long.TryParse(S(p,"expires_at"),out var expiry)||expiry<DateTimeOffset.UtcNow.ToUnixTimeMilliseconds())throw new InvalidOperationException("timeout");
   cancel.ThrowIfCancellationRequested();
   var started=await api("/agent/start",new(){["task_id"]=S(p,"task_id")});
   if(started["cancelled"]?.GetValue<bool>()==true)throw new InvalidOperationException("cancelled");
   var grants=access.Grants.Where(g=>FolderAccessStore.Usable(g)&&(S(p,"grant_id")==""||g.Id==S(p,"grant_id"))).ToList();
   bool writes=tool is "fs_write" or "organize_photos" or "fetch_upload" or "process_run";
   if(writes)grants=grants.Where(g=>g.Access=="write").ToList();
   if(tool!="manage_permissions"&&tool!="open_website"&&grants.Count==0)throw new InvalidOperationException("permission_denied");
   var data=new JsonObject();var evidence=new JsonObject();
   if(writes||tool is "open_document" or "open_website") {
    var review=(JsonObject)p.DeepClone();review["workspace"]=grants.FirstOrDefault()?.Path??"";
    var phoneApproved=started["phone_approved"]?.GetValue<bool>()==true&&tool!="process_run";
    if(!phoneApproved&&!approve(review))throw new InvalidOperationException("permission_denied");
    if((await api("/agent/start",new(){["task_id"]=S(p,"task_id")}))["cancelled"]?.GetValue<bool>()==true)throw new InvalidOperationException("cancelled");
    if(!grants.All(g=>access.Grants.Any(current=>current.Id==g.Id&&(!writes||current.Access=="write"))&&FolderAccessStore.Usable(g)))throw new InvalidOperationException("permission_denied");
    cancel.ThrowIfCancellationRequested();if(expiry<DateTimeOffset.UtcNow.ToUnixTimeMilliseconds())throw new InvalidOperationException("timeout");
   }
   var grant=grants.FirstOrDefault();
   switch(tool) {
    case "search_documents": {
     var matches=new JsonArray();string query=S(p,"query");if(string.IsNullOrWhiteSpace(query))throw new InvalidOperationException("invalid_args");
     foreach(var g in grants)foreach(var path in Files(g)){cancel.ThrowIfCancellationRequested();var fi=new FileInfo(path);if(!fi.Name.Contains(query,StringComparison.OrdinalIgnoreCase)||fi.Length>20*1024*1024)continue;var c=new JsonObject{["candidate_id"]=Candidate(path),["name"]=fi.Name,["size_bytes"]=fi.Length};if(fi.Length<=1048576)c["digest"]=Digest(File.ReadAllBytes(path));matches.Add(c);if(matches.Count==20)break;}
     if(matches.Count==0)throw new InvalidOperationException("no_match");data["candidates"]=matches;break;
    }
    case "transfer_selected_file":case "read_back_file": {
     string? path=grants.SelectMany(Files).FirstOrDefault(f=>Candidate(f)==S(p,"candidate_id"));if(path==null)throw new InvalidOperationException("no_match");
     if(new FileInfo(path).Length>1048576)throw new InvalidOperationException("file_too_large");var raw=File.ReadAllBytes(path);string digest=Digest(raw);
     evidence=new(){["candidate_id"]=S(p,"candidate_id"),["name"]=Path.GetFileName(path),["size_bytes"]=raw.Length,["digest"]=digest};
     if(tool=="transfer_selected_file") {
      if(S(p,"expected_digest")!=digest||S(p,"expected_size")!=raw.Length.ToString())throw new InvalidOperationException("candidate_changed");
      var upload=(JsonObject)evidence.DeepClone();upload["task_id"]=S(p,"task_id");upload["approval_id"]=S(p,"approval_id");upload["content_base64"]=Convert.ToBase64String(raw);await api("/agent/transfer",upload);
     }
     string excerpt="";try {if(!raw.Contains((byte)0))excerpt=new UTF8Encoding(false,true).GetString(raw);}catch(DecoderFallbackException){}data["name"]=Path.GetFileName(path);data["excerpt"]=excerpt[..Math.Min(1500,excerpt.Length)];break;
    }
    case "fs_list": {
     var path=access.Resolve(grant!,S(p,"path","."));var entries=new JsonArray();foreach(var f in Directory.EnumerateFileSystemEntries(path).Take(200)){if((File.GetAttributes(f)&(FileAttributes.Hidden|FileAttributes.ReparsePoint))!=0)continue;entries.Add(new JsonObject{["name"]=Path.GetFileName(f),["type"]=Directory.Exists(f)?"dir":"file",["size_bytes"]=File.Exists(f)?new FileInfo(f).Length:0});}data["entries"]=entries;break;
    }
    case "fs_read": {
     var path=access.Resolve(grant!,S(p,"path"));if(!File.Exists(path))throw new InvalidOperationException("no_match");if(new FileInfo(path).Length>1048576)throw new InvalidOperationException("file_too_large");var raw=File.ReadAllBytes(path);data=Manifest(S(p,"path"),raw);string text;try{if(raw.Contains((byte)0))throw new DecoderFallbackException();text=new UTF8Encoding(false,true).GetString(raw);}catch(DecoderFallbackException){data["binary"]=true;break;}data["content"]=text[..Math.Min(1500,text.Length)];data["truncated"]=text.Length>1500;evidence["digest"]=Digest(raw);evidence["size_bytes"]=raw.Length;break;
    }
    case "fs_write":case "fetch_upload": {
     var path=access.Resolve(grant!,S(p,"path"));byte[] raw=Encoding.UTF8.GetBytes(S(p,"content"));
     if(tool=="fetch_upload"){var artifact=await api("/agent/artifact",new(){["id"]=S(p,"artifact_id")});raw=Convert.FromBase64String(S(artifact,"content_base64"));if(Digest(raw)!=S(p,"artifact_id"))throw new InvalidOperationException("candidate_changed");}
     if(raw.Length>1048576)throw new InvalidOperationException("file_too_large");
     bool exists=File.Exists(path);string? revision=p["base_revision"]?.GetValue<string>();
     if(exists){string current=Digest(File.ReadAllBytes(path));if(tool=="fetch_upload"&&current==Digest(raw)){data=Manifest(S(p,"path"),raw);break;}if(revision==null||revision!=current)throw new InvalidOperationException("candidate_changed");}
     else if(revision!=null)throw new InvalidOperationException("no_match");
     string temp=path+"."+Guid.NewGuid().ToString("N")+".tmp";try{File.WriteAllBytes(temp,raw);File.Move(temp,path,exists);}finally{if(File.Exists(temp))File.Delete(temp);}data=Manifest(S(p,"path"),raw);evidence["digest"]=Digest(raw);break;
    }
    case "organize_photos": {
     string folder=S(p,"folder");if(folder.Contains('/')||folder.Contains('\\')||folder.StartsWith('.'))throw new InvalidOperationException("invalid_args");var target=access.Resolve(grant!,folder);Directory.CreateDirectory(target);
     var types=new HashSet<string>(new[]{".jpg",".jpeg",".png",".heic",".webp",".gif",".bmp",".tif"},StringComparer.OrdinalIgnoreCase);var seen=new HashSet<string>();foreach(var f in Directory.EnumerateFiles(target)){if((File.GetAttributes(f)&FileAttributes.ReparsePoint)==0)seen.Add(HashFile(f));}
     int found=0,copied=0,duplicates=0;foreach(var f in Files(grant!)){cancel.ThrowIfCancellationRequested();if(f.StartsWith(target+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase)||!types.Contains(Path.GetExtension(f)))continue;found++;var digest=HashFile(f);if(!seen.Add(digest)){duplicates++;continue;}if(copied>=2000)break;string dest=Path.Combine(target,Path.GetFileName(f));for(int i=2;File.Exists(dest)&&i<1000;i++)dest=Path.Combine(target,Path.GetFileNameWithoutExtension(f)+"_"+i+Path.GetExtension(f));File.Copy(f,dest,false);copied++;}data=new(){["folder"]=folder,["copied_count"]=copied,["duplicates_skipped"]=duplicates,["found"]=found};evidence["count"]=copied;break;
    }
    case "open_document": {
     var matches=grants.SelectMany(Files).Where(f=>Path.GetFileName(f).Contains(S(p,"query"),StringComparison.OrdinalIgnoreCase)).Take(2).ToArray();if(matches.Length!=1)throw new InvalidOperationException(matches.Length==0?"no_match":"ambiguous_match");
     var extensions=new[]{".txt",".md",".pdf",".docx",".xlsx",".pptx",".csv",".png",".jpg"};if(!extensions.Contains(Path.GetExtension(matches[0]).ToLowerInvariant()))throw new InvalidOperationException("permission_denied");Process.Start(new ProcessStartInfo(matches[0]){UseShellExecute=true});data["name"]=Path.GetFileName(matches[0]);data["candidate_id"]=Candidate(matches[0]);evidence["candidate_id"]=Candidate(matches[0]);break;
    }
    case "open_website": {if(!Uri.TryCreate(S(p,"url"),UriKind.Absolute,out var u)||u.Scheme!="https"||u.UserInfo!="")throw new InvalidOperationException("invalid_args");Process.Start(new ProcessStartInfo(u.AbsoluteUri){UseShellExecute=true});data["url"]=u.AbsoluteUri;break;}
    case "process_run": {
     var argv=JsonNode.Parse(S(p,"argv_json"))!.AsArray().Select(x=>x!.GetValue<string>()).ToArray();if(argv.Length==0||new[]{"cmd","cmd.exe","powershell","powershell.exe","pwsh","sh","bash"}.Contains(Path.GetFileName(argv[0]).ToLowerInvariant()))throw new InvalidOperationException("permission_denied");
     var start=new ProcessStartInfo(argv[0]){UseShellExecute=false,RedirectStandardOutput=true,RedirectStandardError=true,CreateNoWindow=true,WorkingDirectory=access.Resolve(grant!,S(p,"cwd","."))};foreach(var a in argv.Skip(1))start.ArgumentList.Add(a);
     var allowed=new HashSet<string>(new[]{"PATH","HOME","USERPROFILE","SYSTEMROOT","WINDIR","TEMP","TMP","LOCALAPPDATA","APPDATA","PATHEXT","DOTNET_ROOT","JAVA_HOME"},StringComparer.OrdinalIgnoreCase);foreach(var k in start.Environment.Keys.ToArray())if(!allowed.Contains(k))start.Environment.Remove(k);
     using var process=Process.Start(start)??throw new InvalidOperationException("process_failed");using var timeout=CancellationTokenSource.CreateLinkedTokenSource(cancel);timeout.CancelAfter(TimeSpan.FromSeconds(Math.Clamp(int.TryParse(S(p,"timeout_s"),out var secs)?secs:15,1,30)));
     var stdout=Drain(process.StandardOutput);var stderr=Drain(process.StandardError);try{await process.WaitForExitAsync(timeout.Token);}catch{try{process.Kill(true);}catch{}throw new InvalidOperationException(cancel.IsCancellationRequested?"cancelled":"timeout");}
     data=new(){["exit_code"]=process.ExitCode,["stdout"]=await stdout,["stderr"]=await stderr};if(process.ExitCode!=0)throw new InvalidOperationException("process_failed");break;
    }
    default:throw new InvalidOperationException("unsupported_tool");
   }
   result["status"]="succeeded";result["data_json"]=Bounded(data);result["evidence_json"]=Bounded(evidence);result["message"]="Request finished.";
  }catch(Exception e){result["status"]="failed";result["error_code"]=e is OperationCanceledException?"cancelled":e is FileNotFoundException?"no_match":e is InvalidOperationException?e.Message:"permission_denied";result["message"]="Couldn’t finish: "+result["error_code"]!.GetValue<string>();}
  return result;
 }
 static JsonObject Manifest(string path,byte[] raw)=>new(){["path"]=path,["size_bytes"]=raw.Length,["digest"]=Digest(raw)};
 static async Task<string> Drain(StreamReader stream){var output=new StringBuilder();var buffer=new char[1024];int count;while((count=await stream.ReadAsync(buffer))>0)if(output.Length<800)output.Append(buffer,0,Math.Min(count,800-output.Length));return output.ToString();}
 static string Bounded(JsonObject data){if(data.ToJsonString().Length<=2000)return data.ToJsonString();foreach(var key in data.Select(k=>k.Key).ToArray()){if(data[key] is JsonArray a){while(a.Count>1&&data.ToJsonString().Length>1900)a.RemoveAt(a.Count-1);}else if(data[key] is JsonValue v&&v.TryGetValue<string>(out var t)&&t.Length>300)data[key]=t[..300];}data["truncated"]=true;return data.ToJsonString().Length<=2000?data.ToJsonString():"{\"truncated\":true}";}
}
