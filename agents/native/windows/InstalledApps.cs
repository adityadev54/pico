using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text.RegularExpressions;
internal sealed record InstalledApp(string Name,string Target,string Source);
internal static class InstalledApps {
 internal const string StorePrefix="shell:AppsFolder\\";
 internal static bool IsStoreTarget(string value)=>value.StartsWith(StorePrefix,StringComparison.Ordinal)&&Regex.IsMatch(value[StorePrefix.Length..],@"\A[A-Za-z0-9._-]+![A-Za-z0-9._-]+\z");
 internal static bool IsExecutable(string path)=>Path.IsPathFullyQualified(path)&&!path.StartsWith(@"\\")&&Path.GetExtension(path).Equals(".exe",StringComparison.OrdinalIgnoreCase)&&File.Exists(path);
 internal static List<InstalledApp> Normalize(IEnumerable<InstalledApp> apps)=>apps.Where(a=>!string.IsNullOrWhiteSpace(a.Name)&&(IsExecutable(a.Target)||IsStoreTarget(a.Target)))
  .GroupBy(a=>a.Target,StringComparer.OrdinalIgnoreCase).Select(g=>g.First()).OrderBy(a=>a.Source=="Running now"?0:1).ThenBy(a=>a.Name,StringComparer.CurrentCultureIgnoreCase).ToList();

 [ComImport,Guid("2E941141-7F97-4756-BA1D-9DECDE894A3D"),InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
 interface ActivationManager {
  [PreserveSig]int ActivateApplication([MarshalAs(UnmanagedType.LPWStr)]string appId,[MarshalAs(UnmanagedType.LPWStr)]string arguments,uint options,out uint processId);
  [PreserveSig]int ActivateForFile([MarshalAs(UnmanagedType.LPWStr)]string appId,IntPtr items,[MarshalAs(UnmanagedType.LPWStr)]string verb,out uint processId);
  [PreserveSig]int ActivateForProtocol([MarshalAs(UnmanagedType.LPWStr)]string appId,IntPtr items,out uint processId);
 }
 internal static bool ActivateStore(string target) {
  if(!OperatingSystem.IsWindows()||!IsStoreTarget(target))return false;
  object? manager=null;
  try {
   manager=Activator.CreateInstance(Type.GetTypeFromCLSID(new Guid("45BA127D-10A8-46EA-8AB7-56EA9078943C"))!);
   int code=((ActivationManager)manager!).ActivateApplication(target[StorePrefix.Length..],"",2,out uint pid);
   if(code<0)Marshal.ThrowExceptionForHR(code);
   return pid>0;
  }finally{if(manager!=null)Marshal.ReleaseComObject(manager);}
 }
 internal static Task<List<InstalledApp>> ScanAsync(){
  var done=new TaskCompletionSource<List<InstalledApp>>(TaskCreationOptions.RunContinuationsAsynchronously);
  var thread=new Thread(()=>{try{done.SetResult(Scan());}catch(Exception e){done.SetException(e);}}){IsBackground=true};
  if(OperatingSystem.IsWindows())thread.SetApartmentState(ApartmentState.STA);thread.Start();return done.Task;
 }
 internal static List<InstalledApp> Scan(){
  if(!OperatingSystem.IsWindows())return [];
  var apps=new List<InstalledApp>();
  foreach(var process in Process.GetProcesses())using(process){try{if(process.MainWindowHandle==IntPtr.Zero||process.Id==Environment.ProcessId)continue;string path=process.MainModule?.FileName??"";if(path.Contains(@"\WindowsApps\",StringComparison.OrdinalIgnoreCase))continue;string name=FileVersionInfo.GetVersionInfo(path).FileDescription??process.ProcessName;apps.Add(new(name,path,"Running now"));}catch{}}
  object? shellObject=null,scriptObject=null;
  try {
   shellObject=Activator.CreateInstance(Type.GetTypeFromProgID("Shell.Application")!);dynamic shell=shellObject!;
   dynamic folder=shell.NameSpace("shell:AppsFolder");
   if(folder!=null)foreach(dynamic item in folder.Items())try {
    string name=Convert.ToString(item.Name)??"";string path=Convert.ToString(item.Path)??"";
    string appId=Convert.ToString(item.ExtendedProperty("System.AppUserModel.ID"))??"";
    if(IsExecutable(path))apps.Add(new(name,path,"Installed"));
    else if(IsStoreTarget(StorePrefix+appId))apps.Add(new(name,StorePrefix+appId,"Microsoft Store"));
    else if(IsStoreTarget(StorePrefix+path))apps.Add(new(name,StorePrefix+path,"Microsoft Store"));
   }catch{}
  }catch{}
  finally {if(shellObject!=null)Marshal.ReleaseComObject(shellObject);}
  try {
   scriptObject=Activator.CreateInstance(Type.GetTypeFromProgID("WScript.Shell")!);dynamic script=scriptObject!;
   foreach(var root in new[]{Environment.GetFolderPath(Environment.SpecialFolder.Programs),Environment.GetFolderPath(Environment.SpecialFolder.CommonPrograms)}) {
    if(!Directory.Exists(root))continue;
    foreach(string link in Directory.EnumerateFiles(root,"*.lnk",new EnumerationOptions{RecurseSubdirectories=true,IgnoreInaccessible=true,AttributesToSkip=FileAttributes.ReparsePoint}).Take(2000))try {
     dynamic shortcut=script.CreateShortcut(link);string target=Environment.ExpandEnvironmentVariables(Convert.ToString(shortcut.TargetPath)??"");
     // Never import shortcut command arguments or scripts as app permissions.
     if(string.IsNullOrWhiteSpace(Convert.ToString(shortcut.Arguments))&&IsExecutable(target))apps.Add(new(Path.GetFileNameWithoutExtension(link),target,"Start menu"));
    }catch{}
   }
  }catch{}
  finally {if(scriptObject!=null)Marshal.ReleaseComObject(scriptObject);}
  return Normalize(apps);
 }
}
