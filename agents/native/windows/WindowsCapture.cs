using System.Diagnostics;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json;
internal sealed class CaptureSettings {
 public bool Enabled {get;set;}=true;public int Minutes {get;set;}=1;public bool Reopen {get;set;}=true;public bool Snapshots {get;set;}
 public List<string> AllowedCaptureApps {get;set;}=[];
 internal static string FileName=>Path.Combine(Program.Folder,"capture-settings.json");
 internal static CaptureSettings Load(){try{return JsonSerializer.Deserialize<CaptureSettings>(File.ReadAllText(FileName))??new();}catch{return new();}}
 internal void Save(){File.WriteAllText(FileName+".tmp",JsonSerializer.Serialize(this));File.Move(FileName+".tmp",FileName,true);}
}
internal static class WindowsCapture {
 [StructLayout(LayoutKind.Sequential)]struct Rect{public int Left,Top,Right,Bottom;}
 [DllImport("user32.dll")]static extern uint GetWindowThreadProcessId(IntPtr h,out uint pid);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)]static extern int GetWindowText(IntPtr h,StringBuilder s,int max);
 [DllImport("user32.dll")]static extern bool GetWindowRect(IntPtr h,out Rect r);
 [DllImport("user32.dll")]static extern bool PrintWindow(IntPtr h,IntPtr dc,uint flags);
 [DllImport("user32.dll")]static extern bool GetWindowDisplayAffinity(IntPtr h,out uint affinity);
 [DllImport("user32.dll")]static extern IntPtr GetForegroundWindow();
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode)]static extern int GetApplicationUserModelId(IntPtr process,ref uint length,StringBuilder? identity);
 static string ReopenTarget(Process process,string exe) {
  try {
   uint size=0;
   if(GetApplicationUserModelId(process.Handle,ref size,null)==122&&size>1&&size<=512) {
    var identity=new StringBuilder((int)size);
    if(GetApplicationUserModelId(process.Handle,ref size,identity)==0) {
     string target=InstalledApps.StorePrefix+identity.ToString();
     if(InstalledApps.IsStoreTarget(target))return target;
    }
   }
  }catch{}
  return exe;
 }
 internal static (string App,string Title,string? Snapshot,string Target) Capture(IntPtr window,CaptureSettings settings,string place,IReadOnlyList<string>? excluded=null) {
  try {
   GetWindowThreadProcessId(window,out uint pid);using var process=Process.GetProcessById((int)pid);string exe=process.MainModule?.FileName??"";
   string target=ReopenTarget(process,exe);
   string app=process.ProcessName;var text=new StringBuilder(512);GetWindowText(window,text,text.Capacity);string title=text.ToString();
   string[] sensitive=["chrome","msedge","firefox","brave","opera","vivaldi","arc","outlook","teams","slack","signal","whatsapp","telegram","1password","keepass","bitwarden"];
   bool blocked=(excluded?.Contains(exe,StringComparer.OrdinalIgnoreCase)??false)||sensitive.Any(x=>app.Contains(x,StringComparison.OrdinalIgnoreCase))||new[]{"private","incognito","password","inprivate"}.Any(x=>title.Contains(x,StringComparison.OrdinalIgnoreCase));
   if(blocked)return ("Private window","",null,"");
   if(!settings.Snapshots||!settings.AllowedCaptureApps.Contains(exe,StringComparer.OrdinalIgnoreCase)||GetForegroundWindow()!=window)return(app,title,null,target);
   if(GetWindowDisplayAffinity(window,out uint affinity)&&affinity!=0)return(app,title,null,target);
   if(!GetWindowRect(window,out var r))return(app,title,null,target);int width=r.Right-r.Left,height=r.Bottom-r.Top;
   if(width<32||height<32||width>7680||height>4320)return(app,title,null,target);
   using var bitmap=new Bitmap(width,height);using(var graphics=Graphics.FromImage(bitmap)){IntPtr dc=graphics.GetHdc();try{if(!PrintWindow(window,dc,2))return(app,title,null,target);}finally{graphics.ReleaseHdc(dc);}}
   if(GetForegroundWindow()!=window)return(app,title,null,target);
   string folder=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyPictures),"PICO Places");Directory.CreateDirectory(folder);
   string path=Path.Combine(folder,place+".png");bitmap.Save(path,ImageFormat.Png);return(app,title,path,target);
  }catch{return("Unknown app","",null,"");}
 }
}
