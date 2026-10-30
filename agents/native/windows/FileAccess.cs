using System.Text.Json;
using System.Text.Json.Nodes;
internal sealed class FileAccess : FolderAccessStore {
 internal FileAccess(string file):base(file){}
 static string DisplayReview(JsonObject review) {
  var fields=new Dictionary<string,string>{{"tool","Action"},{"workspace","Approved workspace"},{"path","File"},{"content","Contents"},{"url","Website"},{"query","Document name"},{"argv_json","Command arguments"},{"cwd","Working folder"},{"timeout_s","Time limit in seconds"},{"folder","Destination folder"}};
  var clean=new JsonObject();foreach(var f in fields)if(review[f.Key]!=null)clean[f.Value]=review[f.Key]!.DeepClone();
  return clean.ToJsonString(new JsonSerializerOptions{WriteIndented=true});
 }
 internal static bool Approve(Form owner,JsonObject review) {
  using var f=new Form{Text="Approve Pico action?",StartPosition=FormStartPosition.CenterScreen,Size=new Size(620,480),MinimumSize=new Size(520,380),Font=new Font("Segoe UI",10),Padding=new Padding(12),ShowInTaskbar=false};
  var text=new TextBox{Multiline=true,ReadOnly=true,ScrollBars=ScrollBars.Both,WordWrap=false,Dock=DockStyle.Fill,Text=DisplayReview(review)};
  var actions=new FlowLayoutPanel{Dock=DockStyle.Bottom,Height=54,FlowDirection=FlowDirection.RightToLeft};
  var yes=new Button{Text="Approve once",DialogResult=DialogResult.OK,Size=new Size(140,40)};var no=new Button{Text="Cancel",DialogResult=DialogResult.Cancel,Size=new Size(140,40)};actions.Controls.Add(yes);actions.Controls.Add(no);
  var hint=new Label{Text="Review the exact folder and action. Commands run as your user account.",Dock=DockStyle.Top,Height=50};f.Controls.Add(text);f.Controls.Add(hint);f.Controls.Add(actions);f.CancelButton=no;
  return f.ShowDialog(owner)==DialogResult.OK;
 }
 internal void Show(Form owner) {
  using var f=new Form{Text="Pico folder permissions",StartPosition=FormStartPosition.CenterScreen,Size=new Size(640,470),MinimumSize=new Size(540,360),Padding=new Padding(12),Font=new Font("Segoe UI",10)};
  var list=new ListBox{Dock=DockStyle.Fill,IntegralHeight=false};void Reload(){list.Items.Clear();foreach(var g in Grants)list.Items.Add(g);}Reload();
  var controls=new FlowLayoutPanel{Dock=DockStyle.Bottom,Height=100,WrapContents=true};
  foreach(var mode in new[]{"read","write"}){var b=new Button{Text=mode=="read"?"Read-only folder…":"Write workspace…",AutoSize=true,MinimumSize=new Size(165,40)};b.Click+=(_,_)=>{using var picker=new FolderBrowserDialog{Description=mode=="read"?"Choose a folder Pico may read":"Choose a folder for reviewed writes and commands",UseDescriptionForTitle=true};if(picker.ShowDialog(f)==DialogResult.OK){try{Add(picker.SelectedPath,mode);Reload();}catch(Exception e){MessageBox.Show(f,e.Message,"Pico");}}};controls.Controls.Add(b);}
  var remove=new Button{Text="Remove",AutoSize=true,MinimumSize=new Size(100,40)};remove.Click+=(_,_)=>{if(list.SelectedItem is FolderGrant g){Remove(g.Id);Reload();}};controls.Controls.Add(remove);
  f.Controls.Add(list);f.Controls.Add(new Label{Dock=DockStyle.Top,Height=70,Text="Folder permissions\r\nEach write, website, document opening or command also needs your approval. Snapshot exclusions stay separate."});f.Controls.Add(controls);f.ShowDialog(owner);
 }
}
