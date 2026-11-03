using System.Diagnostics;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json;
internal sealed class CaptureSettings {
 public bool Enabled {get;set;}=true;public int Minutes {get;set;}=2;public bool Snapshots {get;set;}
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
 internal static (string App,string Title,string? Snapshot) Capture(IntPtr window,CaptureSettings settings,string place) {
  try {
   GetWindowThreadProcessId(window,out uint pid);using var process=Process.GetProcessById((int)pid);string exe=process.MainModule?.FileName??"";
   string app=process.ProcessName;var text=new StringBuilder(512);GetWindowText(window,text,text.Capacity);string title=text.ToString();
   string[] sensitive=["chrome","msedge","firefox","brave","opera","vivaldi","arc","outlook","teams","slack","signal","whatsapp","telegram","1password","keepass","bitwarden"];
   bool blocked=sensitive.Any(x=>app.Contains(x,StringComparison.OrdinalIgnoreCase))||new[]{"private","incognito","password","inprivate"}.Any(x=>title.Contains(x,StringComparison.OrdinalIgnoreCase));
   if(blocked)return ("Private window","",null);
   if(!settings.Snapshots||!settings.AllowedCaptureApps.Contains(exe,StringComparer.OrdinalIgnoreCase)||GetForegroundWindow()!=window)return(app,title,null);
   if(GetWindowDisplayAffinity(window,out uint affinity)&&affinity!=0)return(app,title,null);
   if(!GetWindowRect(window,out var r))return(app,title,null);int width=r.Right-r.Left,height=r.Bottom-r.Top;
   if(width<32||height<32||width>7680||height>4320)return(app,title,null);
   using var bitmap=new Bitmap(width,height);using(var graphics=Graphics.FromImage(bitmap)){IntPtr dc=graphics.GetHdc();try{if(!PrintWindow(window,dc,2))return(app,title,null);}finally{graphics.ReleaseHdc(dc);}}
   if(GetForegroundWindow()!=window)return(app,title,null);
   string folder=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyPictures),"PICO Places");Directory.CreateDirectory(folder);
   string path=Path.Combine(folder,place+".png");bitmap.Save(path,ImageFormat.Png);return(app,title,path);
  }catch{return("Unknown app","",null);}
 }
}
