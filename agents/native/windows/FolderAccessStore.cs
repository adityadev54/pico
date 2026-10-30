using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
internal sealed record FolderGrant(string Id,string Path,string Access) { public override string ToString()=>System.IO.Path.GetFileName(Path)+" · "+Access; }
internal class FolderAccessStore {
 readonly string file; internal List<FolderGrant> Grants {get;private set;}=[];
 internal FolderAccessStore(string file) { this.file=file;try { Grants=JsonSerializer.Deserialize<List<FolderGrant>>(File.ReadAllText(file))??[]; }catch{} }
 internal void Add(string path,string access) {
  path=Path.GetFullPath(path);if(!Directory.Exists(path)||path.StartsWith(@"\\")||(File.GetAttributes(path)&FileAttributes.ReparsePoint)!=0)throw new InvalidOperationException("Choose a local folder without a link.");
  var id=Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(path))).ToLowerInvariant()[..32];
  Grants.RemoveAll(g=>g.Id==id);Grants.Add(new(id,path,access));Save();
 }
 internal void Clear(){Grants=[];Save();}
 internal void Remove(string id){Grants.RemoveAll(g=>g.Id==id);Save();}
 void Save(){Directory.CreateDirectory(Path.GetDirectoryName(file)!);File.WriteAllText(file+".tmp",JsonSerializer.Serialize(Grants));File.Move(file+".tmp",file,true);}
 internal static bool Usable(FolderGrant grant){try { for(var d=new DirectoryInfo(grant.Path);d!=null;d=d.Parent)if((d.Attributes&FileAttributes.ReparsePoint)!=0)return false;return Directory.Exists(grant.Path);}catch{return false;}}
 internal JsonObject Catalog()=>new(){["workflow_version"]=2,["workspaces"]=new JsonArray(Grants.Where(Usable).Select(g=>(JsonNode)new JsonObject{["id"]=g.Id,["name"]=Path.GetFileName(g.Path),["access"]=g.Access}).ToArray())};
 internal string Resolve(FolderGrant grant,string relative) {
  if(string.IsNullOrWhiteSpace(relative)||Path.IsPathFullyQualified(relative)||relative.Contains(':')||relative.Split('/', '\\').Any(p=>p.StartsWith('.')&&p!="."))throw new InvalidOperationException("Use a visible relative path in the approved folder.");
  if(!Usable(grant))throw new InvalidOperationException("Folder permission is no longer available.");
  var root=Path.GetFullPath(grant.Path);var full=Path.GetFullPath(Path.Combine(root,relative));
  if(full!=root&&!full.StartsWith(root.TrimEnd(Path.DirectorySeparatorChar)+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase))throw new InvalidOperationException("Path leaves the approved folder.");
  var current=full;while(current!=root&&current.Length>=root.Length){if((File.Exists(current)||Directory.Exists(current))&&(File.GetAttributes(current)&FileAttributes.ReparsePoint)!=0)throw new InvalidOperationException("Linked paths are not allowed.");current=Path.GetDirectoryName(current)!;}
  return full;
 }
}
