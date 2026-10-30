using System.Text.Json;
string folder=Path.Combine(Path.GetTempPath(),"pico-app-check-"+Guid.NewGuid());Directory.CreateDirectory(folder);
try {
 string file=Path.Combine(folder,"allowed.exe");File.WriteAllText(file,"");
 var launched=new List<string>();
 var settings=new AppAccessSettings(Path.Combine(folder,"grants.json"),path=>{launched.Add(path);return true;});
 settings.Add(file,false);settings.Add(file,false);settings.Add(file,true);
 if(settings.Allowed.Count!=1 || settings.Excluded.Count!=1)throw new Exception("Grants must remain separate and deduplicated");
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
