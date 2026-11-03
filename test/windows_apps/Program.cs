using System.Text.Json;
string folder=Path.Combine(Path.GetTempPath(),"pico-app-check-"+Guid.NewGuid());Directory.CreateDirectory(folder);
try {
 string file=Path.Combine(folder,"allowed.exe");File.WriteAllText(file,"");
 var launched=new List<string>();
 var settings=new AppAccessSettings(Path.Combine(folder,"grants.json"),path=>{launched.Add(path);return true;});
 settings.Add(file,false);settings.Add(file,false);settings.Add(file,true);
 if(settings.Allowed.Count!=1 || settings.Excluded.Count!=1)throw new Exception("Grants must remain separate and deduplicated");
 var normalized=InstalledApps.Normalize(new[]{new InstalledApp("Friendly app",file,"Running now"),new InstalledApp("Duplicate",file,"Start menu"),new InstalledApp("Bad script",Path.Combine(folder,"bad.cmd"),"Start menu")});
 if(normalized.Count!=1||normalized[0].Name!="Friendly app")throw new Exception("Catalog must deduplicate real executable targets and reject scripts");
 if(!InstalledApps.IsStoreTarget(@"shell:AppsFolder\Microsoft.WindowsCalculator_8wekyb3d8bbwe!App")||InstalledApps.IsStoreTarget(@"shell:AppsFolder\bad!App & calc.exe")||InstalledApps.IsStoreTarget(@"shell:AppsFolder\..\cmd.exe"))throw new Exception("Store targets must be bounded app identities, not commands");
 if(OperatingSystem.IsWindows()) {
  string programs=Environment.GetFolderPath(Environment.SpecialFolder.Programs);Directory.CreateDirectory(programs);
  string shortcutFile=Path.Combine(programs,"Pico catalog check "+Guid.NewGuid()+".lnk");
  object? shellObject=null;
  try {
   shellObject=Activator.CreateInstance(Type.GetTypeFromProgID("WScript.Shell")!);dynamic shell=shellObject!;dynamic shortcut=shell.CreateShortcut(shortcutFile);shortcut.TargetPath=file;shortcut.Save();
   var catalog=await InstalledApps.ScanAsync();if(!catalog.Any(a=>a.Target.Equals(file,StringComparison.OrdinalIgnoreCase)&&a.Source=="Start menu"))throw new Exception("Windows Start menu discovery must return the actual approved target");
  } finally {File.Delete(shortcutFile);if(shellObject!=null)System.Runtime.InteropServices.Marshal.ReleaseComObject(shellObject);}
 }
 string id=settings.Allowed[0].Id;
 using(var catalog=JsonDocument.Parse(settings.Catalog())) if(catalog.RootElement[0].TryGetProperty("Path",out _) || catalog.RootElement[0].TryGetProperty("path",out _))throw new Exception("Paths must remain on the computer");
 if(settings.Open(file).Opened || settings.Open(id,"0").Opened || launched.Count!=0)throw new Exception("Unknown or expired requests must not launch");
 if(!settings.Open(id).Opened || launched.Single()!=file)throw new Exception("Approved app did not launch");
 var restored=new AppAccessSettings(Path.Combine(folder,"grants.json"),_=>true);
 if(restored.Allowed.Single().Id!=id)throw new Exception("App permissions must persist");
 var payload=new System.Text.Json.Nodes.JsonObject { ["task_id"]="t",["call_id"]="c",["tool"]="open_app",["app_id"]=id,["expires_at"]=DateTimeOffset.UtcNow.AddMinutes(1).ToUnixTimeMilliseconds().ToString() };
 if(SafeTaskExecution.Execute(payload,settings)["status"]!.GetValue<string>()!="succeeded")throw new Exception("Approved tool task did not launch");
 payload["tool"]="process_run";
 if(SafeTaskExecution.Execute(payload,settings)["error_code"]!.GetValue<string>()!="unsupported_tool")throw new Exception("Process execution must stay disabled");
 settings.Remove(id,false);
 if(settings.Open(id).Opened || settings.Excluded.Count!=1)throw new Exception("Revoked opening grants must remain separate from capture exclusions");
 string script=Path.Combine(folder,"not-an-app.cmd");File.WriteAllText(script,"");
 try{settings.Add(script,false);throw new Exception("Scripts must not be approved as apps");}catch(InvalidOperationException){}
 Console.WriteLine("Windows approval, launch, expiry, revocation, persistence and catalog privacy checks passed.");
} finally {Directory.Delete(folder,true);}
