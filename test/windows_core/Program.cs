using System.Text.Json.Nodes;
internal sealed class FileAccess(string file):FolderAccessStore(file){}
internal sealed class WorkflowRuntime {
 internal int Calls;
 internal Task<JsonNode> Call(JsonObject p,Func<string,JsonObject,Task<JsonNode?>> callback,CancellationToken cancel){Calls++;return Task.FromResult<JsonNode>(new JsonObject{["data"]=new JsonObject(),["evidence"]=new JsonObject()});}
}
internal static class Program {
 static async Task Main(){string root=Path.Combine(OperatingSystem.IsMacOS()?"/private/tmp":Path.GetTempPath(),"pico-win-"+Guid.NewGuid());Directory.CreateDirectory(root);
 try {var grants=new FileAccess(Path.Combine(root,"grants.json"));grants.Add(root,"read");var runtime=new WorkflowRuntime();int reviews=0;
 JsonObject Payload(string tool)=>new(){["task_id"]="t",["call_id"]="c",["tool"]=tool,["grant_id"]=grants.Grants[0].Id,["expires_at"]=DateTimeOffset.UtcNow.AddSeconds(30).ToUnixTimeMilliseconds().ToString()};
 Task<JsonObject> Api(string p,JsonObject b)=>Task.FromResult(new JsonObject{["phone_approved"]=true});
 async Task<JsonObject> Run(JsonObject p,bool allow=true)=>await SharedFileTools.Execute(p,grants,runtime,r=>{reviews++;return allow;},Api,default);
 void Check(bool condition,string text){if(!condition)throw new Exception(text);Console.WriteLine("PASS "+text);}
 foreach(int dpi in new[]{96,120,144,192,240,288}) {
  int measured=(int)Math.Ceiling(160*dpi/96d);int gutter=(int)Math.Ceiling(92*dpi/96d);
  Check(CompanionMenuMetrics.RowWidth(measured,dpi,4000)>=measured+gutter,"full label width at DPI "+dpi);
 }
 Check(CompanionMenuMetrics.RowWidth(500,192,320)==320,"narrow screens cap width for text wrapping");
 var p=Payload("delete_files");Check((await Run(p))["status"]!.ToString()=="failed"&&runtime.Calls==0,"read permission cannot trash");
 grants.Add(root,"write");p=Payload("delete_files");Check((await Run(p))["status"]!.ToString()=="failed"&&runtime.Calls==0,"write permission cannot trash");
 grants.Add(root,"delete");p=Payload("empty_trash");Check((await Run(p,false))["status"]!.ToString()=="failed"&&runtime.Calls==0&&reviews==1,"permanent empty requires local approval despite phone approval");
 p=Payload("archive");p["expires_at"]="1";Check((await Run(p))["status"]!.ToString()=="failed"&&runtime.Calls==0,"expired request never executes");
 p=Payload("archive");Check((await Run(p))["status"]!.ToString()=="succeeded"&&runtime.Calls==1,"approved archive reaches shared worker");
 var g=grants.Grants[0];bool escaped=false;try{grants.Resolve(g,"../outside");}catch{escaped=true;}Check(escaped,"relative escape blocked");
 Check(grants.Catalog()["document_tools"]!.AsArray().Count==2,"document capabilities advertised");
 var focus=new JsonObject{["places"]=new JsonObject(),["focused"]=true};
 Check(FocusGate.Active(focus),"focus state is active");
 FocusGate.Hold(focus,"Saved output","task1");FocusGate.Hold(focus,"Saved output","task1");
 FocusGate.Hold(focus,"Saved output","task2");Check(focus["places"]!.AsObject().Count==2,"replay deduplicated without losing distinct tasks");
 var restored=JsonNode.Parse(focus.ToJsonString())!.AsObject();Check(FocusGate.Active(restored),"focus survives restart");
 restored["places"]!["result:task1"]!["status"]="finished";FocusGate.Hold(restored,"Saved output","task1");
 Check(restored["places"]!["result:task1"]!["status"]!.ToString()=="finished","dismissed result never resurrected");
 Check(!FocusGate.MayRun("tool_call",new(){["tool"]="fs_write"}),"writes wait while focused");
 Check(FocusGate.MayRun("tool_call",new(){["tool"]="fs_read"}),"reads can finish silently");
 Check(!FocusGate.MayRun("open_app",new()),"apps never steal focus");
 }finally{Directory.Delete(root,true);}}
}
