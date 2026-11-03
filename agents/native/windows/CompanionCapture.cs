using System.Text.Json.Nodes;
sealed partial class Companion {
 readonly CaptureSettings captureSettings=CaptureSettings.Load();
 readonly System.Windows.Forms.Timer idleTimer=new(){Interval=1000};bool capturing;
 void StartIdleDetection(){idleTimer.Tick+=async(_,_)=>await CheckIdle();idleTimer.Start();}
 async Task CheckIdle() {
  if(token==null||capturing||IsDisposed)return;
  var input=new LastInput{Size=(uint)System.Runtime.InteropServices.Marshal.SizeOf<LastInput>()};
  bool idle=captureSettings.Enabled&&GetLastInputInfo(ref input)&&unchecked((uint)Environment.TickCount-input.Time)>=Math.Clamp(captureSettings.Minutes,1,60)*60000;
  if(idle&&!away) {
   away=true;capturing=true;string id=Guid.NewGuid().ToString();IntPtr window=GetForegroundWindow();string? account=token;
   try {
    var result=await Task.Run(()=>WindowsCapture.Capture(window,captureSettings,id));
    if(account!=token)return;
    state["places"]![id]=new JsonObject{["sentence"]="",["status"]="waiting",["app"]=result.App,["title"]=result.Title,["snapshot"]=result.Snapshot,["created"]=DateTimeOffset.UtcNow.ToUnixTimeSeconds()};
    state["outgoing"]!.AsArray().Add(new JsonObject{["id"]=Guid.NewGuid().ToString(),["kind"]="idle",["payload"]=new JsonObject{["place_id"]=id,["app"]=result.App[..Math.Min(120,result.App.Length)]}});Save();
    SetCharacter(current??"tuck","surprised");moodUntil=DateTimeOffset.UtcNow.AddSeconds(4).ToUnixTimeMilliseconds();
   }finally{capturing=false;}
  }
  if(away&&!idle){away=false;if(activePlace!=null)ShowPlace(activePlace);}
 }
 void ShowCaptureSettings() {
  using var form=new Form{Text="Hold my place",ClientSize=new Size(590,310),StartPosition=FormStartPosition.CenterScreen,Font=new Font("Segoe UI",10),Padding=new Padding(16)};
  var rows=new FlowLayoutPanel{Dock=DockStyle.Fill,FlowDirection=FlowDirection.TopDown,WrapContents=false};
  var enabled=new CheckBox{Text="Notice when I step away",Checked=captureSettings.Enabled,AutoSize=true};
  var minutes=new NumericUpDown{Minimum=1,Maximum=60,Value=Math.Clamp(captureSettings.Minutes,1,60),Width=100};
  var snapshots=new CheckBox{Text="Save a local preview from selected apps",Checked=captureSettings.Snapshots,AutoSize=true};
  var apps=new Button{Text="Choose an app for previews…",AutoSize=true};
  apps.Click+=(_,_)=>{using var pick=new OpenFileDialog{Title="Allow this app’s window in local previews",Filter="Applications|*.exe"};if(pick.ShowDialog(form)==DialogResult.OK){captureSettings.AllowedCaptureApps.Add(pick.FileName);captureSettings.Save();}};
  var clear=new Button{Text="Remove all preview app permissions",AutoSize=true};clear.Click+=(_,_)=>{captureSettings.AllowedCaptureApps.Clear();captureSettings.Save();};
  var hint=new Label{Text="Minutes before stepping away. Previews stay on this computer. Browsers, messaging and password apps are excluded. No screen images are sent to Muse.",AutoSize=true,MaximumSize=new Size(550,0)};
  enabled.CheckedChanged+=(_,_)=>{captureSettings.Enabled=enabled.Checked;captureSettings.Save();};minutes.ValueChanged+=(_,_)=>{captureSettings.Minutes=(int)minutes.Value;captureSettings.Save();};snapshots.CheckedChanged+=(_,_)=>{captureSettings.Snapshots=snapshots.Checked;captureSettings.Save();};
  rows.Controls.AddRange([enabled,minutes,snapshots,apps,clear,hint]);form.Controls.Add(rows);form.ShowDialog(this);
 }
}
