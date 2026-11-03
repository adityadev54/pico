using System.Diagnostics;
using System.IO.Compression;
using System.Reflection;
using System.Security.Cryptography;
using System.Text.Json.Nodes;

// Private stdio IPC. The worker never receives the pairing token or a network port.
internal sealed class WorkflowRuntime : IDisposable {
 readonly SemaphoreSlim gate=new(1,1); Process? worker;
 static string Install() {
  using var resource=Assembly.GetExecutingAssembly().GetManifestResourceStream("windows-runtime.zip")??throw new IOException("Workflow runtime is missing. Reinstall Pico.");
  using var memory=new MemoryStream();resource.CopyTo(memory);var raw=memory.ToArray();
  string folder=Path.Combine(Program.Folder,"runtime",Convert.ToHexString(SHA256.HashData(raw))[..16]);
  if(File.Exists(Path.Combine(folder,"ready")))return folder;
  string staging=folder+"-"+Guid.NewGuid().ToString("N");Directory.CreateDirectory(staging);
  try {using var zip=new ZipArchive(new MemoryStream(raw));zip.ExtractToDirectory(staging);File.WriteAllText(Path.Combine(staging,"ready"),"ok");Directory.Move(staging,folder);}
  finally {if(Directory.Exists(staging))Directory.Delete(staging,true);}
  return folder;
 }
 void Start() {
  if(worker is {HasExited:false})return;
  string root=Install();var info=new ProcessStartInfo(Path.Combine(root,"python.exe")){UseShellExecute=false,CreateNoWindow=true,RedirectStandardInput=true,RedirectStandardOutput=true,RedirectStandardError=true,WorkingDirectory=root};
  info.ArgumentList.Add("-I");info.ArgumentList.Add("-u");info.ArgumentList.Add(Path.Combine(root,"engine","windows_worker.py"));
  foreach(var key in info.Environment.Keys.ToArray())if(!new[]{"SYSTEMROOT","WINDIR","TEMP","TMP","LOCALAPPDATA","USERPROFILE"}.Contains(key,StringComparer.OrdinalIgnoreCase))info.Environment.Remove(key);
  worker=Process.Start(info)??throw new IOException("Couldn’t start the workflow engine.");
  worker.ErrorDataReceived+=(_,_)=>{};worker.BeginErrorReadLine();
 }
 internal async Task<JsonNode> Call(JsonObject request,Func<string,JsonObject,Task<JsonNode?>> callback,CancellationToken cancel=default) {
  await gate.WaitAsync(cancel);
  try {
   Start();using var timeout=CancellationTokenSource.CreateLinkedTokenSource(cancel);timeout.CancelAfter(TimeSpan.FromSeconds(90));
   await worker!.StandardInput.WriteLineAsync(request.ToJsonString());
   while(true) {
    string? line=await worker.StandardOutput.ReadLineAsync(timeout.Token);if(line==null)throw new IOException("The workflow engine stopped. No automatic retry was made.");
    var reply=JsonNode.Parse(line)!.AsObject();
    if(reply["callback"] is not null) {
     JsonObject response;
     try {response=new(){["result"]=await callback(reply["callback"]!.GetValue<string>(),reply["body"]!.AsObject())};}
     catch(Exception e){response=new(){["error"]=e.Message};}
     await worker.StandardInput.WriteLineAsync(response.ToJsonString());continue;
    }
    if(reply["error"]!=null)throw new InvalidOperationException(reply["error"]!.GetValue<string>());
    return reply["result"]??new JsonObject();
   }
  } catch(OperationCanceledException){Stop();throw;}
    catch(IOException){Stop();throw;}
  finally {gate.Release();}
 }
 void Stop(){try{if(worker is {HasExited:false})worker.Kill(true);}catch{}worker?.Dispose();worker=null;}
 public void Dispose(){Stop();gate.Dispose();}
}
