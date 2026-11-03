using System.Diagnostics;
using System.Text.Json;

internal sealed record AppGrant(string Id, string Name, string Path);
internal sealed record AppOpenResult(bool Opened, string Message);
internal sealed record AppGrantFile(List<AppGrant> Allowed, List<AppGrant> Excluded);

internal sealed class AppAccessSettings
{
    readonly string file;
    readonly Func<string, bool> launch;
    List<AppGrant> allowed = [], excluded = [];
    internal IReadOnlyList<AppGrant> Allowed => allowed;
    internal IReadOnlyList<AppGrant> Excluded => excluded;
    internal AppAccessSettings(string file, Func<string, bool>? launch = null)
    {
        this.file = file; this.launch = launch ?? Launch;
        try {
            var saved = JsonSerializer.Deserialize<AppGrantFile>(File.ReadAllText(file));
            allowed = (saved?.Allowed ?? []).Where(Valid).DistinctBy(a => a.Path, StringComparer.OrdinalIgnoreCase).Take(20).ToList();
            excluded = (saved?.Excluded ?? []).Where(Valid).DistinctBy(a => a.Path, StringComparer.OrdinalIgnoreCase).Take(100).ToList();
        } catch { }
    }
    static bool Valid(AppGrant a) => a != null && Guid.TryParse(a.Id, out _) && !string.IsNullOrWhiteSpace(a.Name) && a.Name.Length <= 40 &&
        (InstalledApps.IsStoreTarget(a.Path) || Path.IsPathFullyQualified(a.Path) && !a.Path.StartsWith(@"\\") && Path.GetExtension(a.Path).Equals(".exe", StringComparison.OrdinalIgnoreCase));
    internal void Add(string path, bool exclusion)
    {
        Add(new InstalledApp(Path.GetFileNameWithoutExtension(path),Path.GetFullPath(path),"Selected file"),exclusion);
    }
    internal void Add(InstalledApp selected,bool exclusion)
    {
        string path=selected.Target;
        var app = new AppGrant(Guid.NewGuid().ToString(), selected.Name[..Math.Min(40,selected.Name.Length)], path);
        if (!Valid(app) || !(InstalledApps.IsStoreTarget(path) ? !exclusion && InstalledApps.Scan().Any(a=>a.Target==path) : File.Exists(path))) throw new InvalidOperationException("Choose an installed application from the list, or browse for its .exe.");
        var list = new List<AppGrant>(exclusion ? excluded : allowed);
        if (list.Any(a => string.Equals(a.Path, path, StringComparison.OrdinalIgnoreCase))) return;
        if (list.Count >= (exclusion ? 100 : 20)) throw new InvalidOperationException("The app list is full. Remove an entry first.");
        list.Add(app); Commit(exclusion ? allowed : list, exclusion ? list : excluded);
    }
    internal void Clear() => Commit([],[]);
    internal void Remove(string id, bool exclusion) => Commit(exclusion ? allowed : allowed.Where(a => a.Id != id).ToList(), exclusion ? excluded.Where(a => a.Id != id).ToList() : excluded);
    void Commit(List<AppGrant> nextAllowed, List<AppGrant> nextExcluded)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(file)!);
        File.WriteAllText(file + ".tmp", JsonSerializer.Serialize(new AppGrantFile(nextAllowed, nextExcluded)));
        File.Move(file + ".tmp", file, true); allowed = nextAllowed; excluded = nextExcluded;
    }
    internal string Catalog() => JsonSerializer.Serialize(allowed.Select(a => new { id = a.Id, name = a.Name }));
    internal AppOpenResult Open(string id, string? expiresAt = null)
    {
        if (expiresAt != null && (!long.TryParse(expiresAt, out long until) || until < DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()))
            return new(false, "This request expired. Tap the app again.");
        var app = allowed.FirstOrDefault(a => a.Id == id);
        if (app == null) return new(false, "Approve this app on your computer first.");
        try { if ((InstalledApps.IsStoreTarget(app.Path)||File.Exists(app.Path)) && launch(app.Path)) return new(true, "Opened " + app.Name + "."); } catch { }
        return new(false, "Couldn’t open this app. Check that it is still installed.");
    }
    static bool Launch(string path) {
        if(InstalledApps.IsStoreTarget(path)) {
            return InstalledApps.ActivateStore(path);
        }
        return Process.Start(new ProcessStartInfo(path){UseShellExecute=false,WorkingDirectory=Path.GetDirectoryName(path)!})!=null;
    }
}
