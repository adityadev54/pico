using System.Diagnostics;
using System.Text.Json.Nodes;
internal sealed class TeachWindow : Form {
 readonly Func<JsonObject,Task<JsonNode>> call;readonly Action<JsonArray,string,string,string> publish;
 readonly ComboBox roots=new(){DropDownStyle=ComboBoxStyle.DropDownList,Width=540};
 readonly TextBox name=new(){Text="Prepare my result",Width=540};
 readonly Label status=new(){AutoSize=true,MaximumSize=new Size(540,0)};
 readonly FlowLayoutPanel content=new(){Dock=DockStyle.Fill,FlowDirection=FlowDirection.TopDown,WrapContents=false,AutoScroll=true,Padding=new Padding(16)};
 readonly ListBox recipes=new(){Width=540,Height=100,DisplayMember="Name"};
 string? session;bool busy;
 internal bool IsTeaching => busy || session!=null;
 internal TeachWindow(FileAccess folders,Func<JsonObject,Task<JsonNode>> call,Action<JsonArray,string,string,string> publish) {
  this.call=call;this.publish=publish;Text="Teach Pico";ClientSize=new Size(590,490);MinimumSize=new Size(590,440);StartPosition=FormStartPosition.CenterScreen;Font=new Font("Segoe UI",10);
  content.Controls.Add(new Label{Text="Watch how I do this",AutoSize=true,Font=new Font(Font.FontFamily,18,FontStyle.Bold)});
  content.Controls.Add(new Label{Text="Choose inputs and show Pico an example result. Only selected files are read.",AutoSize=true,MaximumSize=new Size(540,0)});
  foreach(var g in folders.Grants.Where(g=>g.Access is "write" or "delete"&&FolderAccessStore.Usable(g)))roots.Items.Add(g);
  if(roots.Items.Count>0)roots.SelectedIndex=0;
  content.Controls.Add(roots);content.Controls.Add(name);
  Add("Select files and example…",async()=> {
   if(roots.SelectedItem is not FolderGrant grant)throw new InvalidOperationException("Choose a write workspace in Permissions first.");
   using var picker=new OpenFileDialog{Title="Choose one to four input documents",Multiselect=true,InitialDirectory=grant.Path,Filter="Documents|*.txt;*.md;*.csv;*.docx;*.pdf"};
   if(picker.ShowDialog(this)!=DialogResult.OK)return;
   using var output=new SaveFileDialog{Title="Choose the example you will edit",InitialDirectory=grant.Path,FileName="My example.md",Filter="Markdown|*.md",OverwritePrompt=true};
   if(output.ShowDialog(this)!=DialogResult.OK)return;
   var result=await call(new(){["operation"]="start",["root"]=grant.Path,["sources"]=new JsonArray(picker.FileNames.Select(f=>(JsonNode)JsonValue.Create(Path.GetRelativePath(grant.Path,f).Replace('\\','/'))!).ToArray()),["output"]=Path.GetRelativePath(grant.Path,output.FileName).Replace('\\','/')});
   session=result["id"]!.GetValue<string>();Process.Start(new ProcessStartInfo("notepad.exe"){ArgumentList={output.FileName},UseShellExecute=false});status.Text="Edit and save your example, then finish teaching.";
  });
  Add("Finish teaching…",async()=> {
   if(session==null)throw new InvalidOperationException("Choose files and edit an example first.");
   if(!Confirm("Send the selected inputs and your saved example to Muse to learn this routine?"))return;
   await call(new(){["operation"]="finish",["session"]=session,["name"]=name.Text});session=null;await Reload();status.Text="Routine learned. Change the inputs, then run it again.";
  });
  content.Controls.Add(status);content.Controls.Add(recipes);
  Add("Run selected routine…",async()=>{var row=Selected();if(!Confirm("Send this routine’s selected input files to Muse and create a new result?"))return;await Run(row.Id,Guid.NewGuid().ToString());});
  Add("Change input files…",async()=>{var row=Selected();using var picker=new OpenFileDialog{Title="Choose replacement inputs",Multiselect=true,InitialDirectory=row.Root,Filter="Documents|*.txt;*.md;*.csv;*.docx;*.pdf"};if(picker.ShowDialog(this)!=DialogResult.OK)return;await call(new(){["operation"]="sources",["id"]=row.Id,["sources"]=new JsonArray(picker.FileNames.Select(f=>(JsonNode)JsonValue.Create(Path.GetRelativePath(row.Root,f).Replace('\\','/'))!).ToArray())});await Reload();});
  Add("Open latest result",async()=>{var result=await call(new(){["operation"]="latest",["id"]=Selected().Id});Process.Start(new ProcessStartInfo(result["path"]!.GetValue<string>()){UseShellExecute=true});});
  Controls.Add(content);Shown+=async(_,_)=>{try{await Reload();}catch(Exception e){status.Text=e.Message;}};
  FormClosing+=(_,e)=>{if(busy){e.Cancel=true;status.Text="Wait for the current request to finish.";}else if(session!=null){_ = call(new(){["operation"]="cancel"});session=null;}};
 }
 sealed record Routine(string Id,string Name,string Root){public override string ToString()=>Name;}
 Routine Selected()=>recipes.SelectedItem as Routine??throw new InvalidOperationException("Select a taught routine first.");
 bool Confirm(string message)=>MessageBox.Show(this,message,"Use Muse?",MessageBoxButtons.OKCancel,MessageBoxIcon.Question)==DialogResult.OK;
 void Add(string title,Func<Task> action){var b=new Button{Text=title,AutoSize=true,MinimumSize=new Size(220,34)};b.Click+=async(_,_)=>{if(busy)return;busy=true;try{status.Text="Working…";await action();}catch(Exception e){status.Text=e.Message;}finally{busy=false;}};content.Controls.Add(b);}
 async Task Reload(){var rows=(await call(new(){["operation"]="catalog"})).AsArray();recipes.Items.Clear();foreach(var r in rows)recipes.Items.Add(new Routine(r!["id"]!.GetValue<string>(),r["name"]!.GetValue<string>(),r["root"]!.GetValue<string>()));if(recipes.Items.Count>0)recipes.SelectedIndex=0;publish(rows,"","catalog","");}
 internal async Task Run(string id,string request){try{var result=await call(new(){["operation"]="run",["id"]=id,["request_id"]=request});var rows=(await call(new(){["operation"]="catalog"})).AsArray();publish(rows,request,"completed","Saved and verified: "+result["output"]!.GetValue<string>());status.Text="Saved and verified: "+result["output"]!.GetValue<string>();}catch(Exception e){publish(new(),request,"failed",e.Message);throw;}}
}
