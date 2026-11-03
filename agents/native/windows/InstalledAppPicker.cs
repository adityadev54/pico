internal sealed class InstalledAppPicker : Form {
 internal InstalledApp? SelectedApp {get;private set;}
 readonly TextBox search=new(){Dock=DockStyle.Top,PlaceholderText="Search your apps…"};
 readonly ListView list=new(){Dock=DockStyle.Fill,View=View.Details,FullRowSelect=true,MultiSelect=false,HideSelection=false};
 readonly Label status=new(){Dock=DockStyle.Bottom,Height=42,Text="Finding your apps…"};
 readonly Button choose=new(){Text="Select app",AutoSize=true,Enabled=false};
 List<InstalledApp> apps=[];
 internal InstalledAppPicker(bool executableOnly=false) {
  Text="Choose an app";ClientSize=new Size(650,510);MinimumSize=new Size(540,400);StartPosition=FormStartPosition.CenterParent;Font=new Font("Segoe UI",10);Padding=new Padding(16);
  list.Columns.Add("Application",390);list.Columns.Add("Available from",170);
  var actions=new FlowLayoutPanel{Dock=DockStyle.Bottom,Height=44,FlowDirection=FlowDirection.RightToLeft};
  var cancel=new Button{Text="Cancel",AutoSize=true,DialogResult=DialogResult.Cancel};
  var browse=new Button{Text="Browse for .exe…",AutoSize=true};
  browse.Click+=(_,_)=>{using var picker=new OpenFileDialog{Title="Choose an installed application",Filter="Applications|*.exe",CheckFileExists=true};if(picker.ShowDialog(this)==DialogResult.OK){SelectedApp=new(Path.GetFileNameWithoutExtension(picker.FileName),picker.FileName,"Selected file");DialogResult=DialogResult.OK;}};
  void Select(){if(list.SelectedItems.Count!=1)return;SelectedApp=(InstalledApp)list.SelectedItems[0].Tag!;DialogResult=DialogResult.OK;}
  choose.Click+=(_,_)=>Select();list.DoubleClick+=(_,_)=>Select();list.SelectedIndexChanged+=(_,_)=>choose.Enabled=list.SelectedItems.Count==1;
  void Filter(){list.BeginUpdate();list.Items.Clear();foreach(var app in apps.Where(a=>a.Name.Contains(search.Text.Trim(),StringComparison.CurrentCultureIgnoreCase)))list.Items.Add(new ListViewItem(new[]{app.Name,app.Source}){Tag=app});list.EndUpdate();status.Text=list.Items.Count==0?"No matching apps. Open the app and reopen this picker, or browse for its .exe.":$"{list.Items.Count} apps · Choose the app by name.";}
  search.TextChanged+=(_,_)=>Filter();
  actions.Controls.AddRange([choose,cancel,browse]);Controls.Add(list);Controls.Add(search);Controls.Add(status);Controls.Add(actions);CancelButton=cancel;AcceptButton=choose;
  Shown+=async(_,_)=>{try{var found=await InstalledApps.ScanAsync();if(IsDisposed)return;apps=executableOnly?found.Where(a=>!InstalledApps.IsStoreTarget(a.Target)).ToList():found;Filter();}catch{if(!IsDisposed)status.Text="Couldn’t list apps. Open the app and retry, or browse for its .exe.";}};
 }
}
