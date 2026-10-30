using System.Net;
using System.Net.Http.Json;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json.Nodes;
using Microsoft.Win32;

static class Program
{
    internal static readonly string Folder = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Pico");
    [STAThread]
    static void Main()
    {
        ApplicationConfiguration.Initialize();
        try
        {
            Directory.CreateDirectory(Folder);
            string installed = Path.Combine(Folder, "Pico.exe");
            if (!string.Equals(Environment.ProcessPath, installed, StringComparison.OrdinalIgnoreCase))
            {
                // Install for the current user; no administrator or separate runtime required.
                File.Copy(Environment.ProcessPath!, installed, true);
                var shellType = Type.GetTypeFromProgID("WScript.Shell")!;
                dynamic shell = Activator.CreateInstance(shellType)!;
                string shortcut = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Programs), "Pico.lnk");
                dynamic link = shell.CreateShortcut(shortcut);
                link.TargetPath = installed; link.WorkingDirectory = Folder; link.Save();
                System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo(installed) { UseShellExecute = true });
                return;
            }
            using var mutex = new Mutex(true, "Local\\PicoCompanion", out bool first);
            if (!first) return;
            Application.Run(new Companion());
        }
        catch { MessageBox.Show("Pico couldn’t start. Close any running copy and try again.", "Pico"); }
    }
}

sealed class Companion : Form
{
    const string Relay = RelayConfig.Url;
    readonly AppAccessSettings appAccess = new(Path.Combine(Program.Folder, "app-access.json"));
    readonly HttpClient http = new() { Timeout = TimeSpan.FromSeconds(65) };
    readonly PictureBox picture = new() { SizeMode = PictureBoxSizeMode.Zoom, BackColor = Color.Magenta };
    readonly System.Windows.Forms.Timer timer = new();
    readonly System.Windows.Forms.Timer replyTimer = new() { Interval = 12000 };
    readonly ReplyBubble reply = new() { Visible = false };
    string? replyPlace;
    string mood = "idle";
    long moodUntil;
    int agentSide = 180;
    readonly string tokenFile = Path.Combine(Program.Folder, "connection.dat");
    readonly string stateFile = Path.Combine(Program.Folder, "places.json");
    JsonObject state = new() { ["places"] = new JsonObject(), ["handled"] = new JsonArray(), ["outgoing"] = new JsonArray() };
    readonly FileAccess fileAccess = new(Path.Combine(Program.Folder,"folders.json"));
    readonly System.Collections.Concurrent.ConcurrentDictionary<string,CancellationTokenSource> runningTasks = new();
    bool away;
    string? activePlace;

    readonly ToolTip activity = new();
    string? current;
    string? token;
    int failures;
    bool busy;
    MemoryStream? imageStream;
    public Companion()
    {
        if (File.Exists(stateFile)) { try { state = JsonNode.Parse(File.ReadAllText(stateFile))!.AsObject(); } catch { } }
        state["task_journal"] ??= new JsonObject();
        foreach(var entry in state["task_journal"]!.AsObject().ToArray()) {
            var item=entry.Value!.AsObject();if(item["status"]?.GetValue<string>()!="running")continue;
            var p=item["payload"]!.AsObject();state["outgoing"]!.AsArray().Add(new JsonObject{["id"]=Guid.NewGuid().ToString(),["kind"]="tool_result",["payload"]=new JsonObject{["task_id"]=p["task_id"]!.DeepClone(),["call_id"]=p["call_id"]!.DeepClone(),["status"]="failed",["error_code"]="interrupted",["message"]="Pico restarted during this action. Check the computer before retrying."}});state["handled"]!.AsArray().Add(entry.Key);item["status"]="interrupted";
        }
        FormBorderStyle = FormBorderStyle.None; ShowInTaskbar = false; TopMost = true;
        BackColor = Color.Magenta; TransparencyKey = Color.Magenta; ClientSize = new Size(280, 280);
        StartPosition = FormStartPosition.Manual;
        var area = Screen.PrimaryScreen!.WorkingArea; Location = new Point(area.Right - 200, area.Bottom - 200);
        Controls.Add(picture); Controls.Add(reply);
        LayoutAgent();
        reply.Click += (_, _) => { if (replyPlace != null) ShowPlaceDetails(replyPlace); };
        replyTimer.Tick += (_, _) => { replyTimer.Stop(); reply.Visible = false; SetCharacter(current ?? "tuck", "idle"); };
        picture.MouseDown += (_, e) => { if (e.Button == MouseButtons.Left) { ReleaseCapture(); SendMessage(Handle, 0xA1, new IntPtr(2), IntPtr.Zero); } };
        picture.MouseUp += (_, e) => { if (e.Button == MouseButtons.Right) ShowCompanionMenu(); };
        timer.Tick += async (_, _) => { timer.Stop(); await Poll(); };
        Shown += async (_, _) =>
        {
            try { if (File.Exists(tokenFile)) token = Encoding.UTF8.GetString(ProtectedData.Unprotect(File.ReadAllBytes(tokenFile), null, DataProtectionScope.CurrentUser)); }
            catch { File.Delete(tokenFile); }
            var characterFile = Path.Combine(Program.Folder, "character.txt");
            SetCharacter(File.Exists(characterFile) ? File.ReadAllText(characterFile).Trim() : "tuck");
            if (token == null) await Pair(); else Schedule(1000);
        };
        FormClosed += (_, _) => { timer.Stop(); replyTimer.Dispose(); http.Dispose(); };
    }
    CompanionMenu? companionMenu;
    void ShowCompanionMenu()
    {
        if (companionMenu is { IsDisposed: false }) { companionMenu.Close(); return; }
        bool startup = false;
        using (var run = Registry.CurrentUser.OpenSubKey(@"Software\Microsoft\Windows\CurrentVersion\Run")) startup = run?.GetValue("Pico") is string;
        companionMenu = new CompanionMenu(picture.RectangleToScreen(picture.ClientRectangle), startup, () => {
            using var run = Registry.CurrentUser.CreateSubKey(@"Software\Microsoft\Windows\CurrentVersion\Run");
            if (!startup) run.SetValue("Pico", "\"" + Environment.ProcessPath + "\""); else run.DeleteValue("Pico", false);
        }, ShowAppAccess, ShowParked, Disconnect, Close, () => fileAccess.Show(this));
        companionMenu.Show(this);
    }
    void ShowAppAccess() { using var window = new AppAccessWindow(appAccess, QueueAppCatalog); window.ShowDialog(); }
    void QueueAppCatalog()
    {
        var outgoing = state["outgoing"]!.AsArray();
        foreach (var old in outgoing.Where(m => m?["kind"]?.GetValue<string>() == "app_catalog").ToArray()) outgoing.Remove(old);
        outgoing.Add(new JsonObject { ["id"] = Guid.NewGuid().ToString(), ["kind"] = "app_catalog", ["payload"] = new JsonObject { ["catalog"] = appAccess.Catalog() } }); Save();
    }
    protected override bool ProcessCmdKey(ref Message msg, Keys keyData)
    {
        if (keyData == Keys.Apps || keyData == (Keys.Shift | Keys.F10)) { ShowCompanionMenu(); return true; }
        return base.ProcessCmdKey(ref msg, keyData);
    }
    async Task<(HttpStatusCode, JsonObject)> Api(string path, JsonObject body, bool authorized = true)
    {
        using var request = new HttpRequestMessage(HttpMethod.Post, Relay + path) { Content = RelayRequestBody.Create(body) };
        if (authorized) request.Headers.Authorization = new("Bearer", token);
        using var response = await http.SendAsync(request);
        var json = await response.Content.ReadFromJsonAsync<JsonObject>() ?? new JsonObject();
        return (response.StatusCode, json);
    }
    async Task Pair()
    {
        using var form = new PairingWindow(async code => {
            var result = await PairingConnection.ClaimAsync(http, Relay, code, Environment.MachineName);
            if (result.Error != null) return result.Error;
            try {
                File.WriteAllBytes(tokenFile, ProtectedData.Protect(Encoding.UTF8.GetBytes(result.Token!), null, DataProtectionScope.CurrentUser));
                if(token!=result.Token) {
                    if(File.Exists(stateFile))File.Copy(stateFile,stateFile+"."+Guid.NewGuid().ToString("N")+".archive");
                    state=new(){["places"]=new JsonObject(),["handled"]=new JsonArray(),["outgoing"]=new JsonArray(),["task_journal"]=new JsonObject()};fileAccess.Clear();appAccess.Clear();Save();
                }
                token = result.Token;
                return null;
            }
            catch (Exception error) when (error is IOException or UnauthorizedAccessException or CryptographicException) {
                return "Pico connected, but Windows couldn’t save the connection. Unpair this computer on your phone, check folder permissions, then try again.";
            }
        });
        if (form.ShowDialog() != DialogResult.OK) { Close(); return; }
        Schedule(1000); await Task.CompletedTask;
    }
    async Task ExecuteTask(string mailId,JsonObject data) {
        string task=data["task_id"]!.GetValue<string>();using var stop=new CancellationTokenSource();runningTasks[task]=stop;
        try {
            JsonObject outcome;
            if(data["tool"]?.GetValue<string>()=="manage_permissions") {
                fileAccess.Show(this);outcome=new(){["task_id"]=task,["call_id"]=data["call_id"]!.DeepClone(),["status"]="succeeded",["data_json"]="{}",["evidence_json"]="{}",["message"]="Permissions opened."};
            } else outcome = data["tool"]?.GetValue<string>()=="open_app"
                ? SafeTaskExecution.Execute(data,appAccess)
                : await Task.Run(()=>FileTaskExecution.Execute(data,fileAccess,review=>(bool)Invoke(()=>FileAccess.Approve(this,review)),async(path,body)=>{var (code,value)=await Api(path,body);if(code!=HttpStatusCode.OK)throw new InvalidOperationException("transfer_failed");return value;},stop.Token));
            state["outgoing"]!.AsArray().Add(new JsonObject{["id"]=Guid.NewGuid().ToString(),["kind"]="tool_result",["payload"]=outcome});
            state["task_journal"]![mailId]=new JsonObject{["status"]="finished"};var handled=state["handled"]!.AsArray();handled.Add(mailId);while(handled.Count>200)handled.RemoveAt(0);Save();ShowReply(outcome["message"]?.GetValue<string>()??"Request finished.");
        } finally {runningTasks.TryRemove(task,out _);}
    }
    void SetCharacter(string name, string? activity = null)
    {
        if (name is not ("tuck" or "mica")) name = "tuck";
        activity ??= mood;
        if (activity is not ("idle" or "listening" or "talking" or "working" or "thinking" or "done" or "stuck" or "needsYou")) return;
        if (current == name && mood == activity) return;
        current = name; mood = activity; File.WriteAllText(Path.Combine(Program.Folder, "character.txt"), name);
        using var stream = typeof(Program).Assembly.GetManifestResourceStream(name + "." + mood + ".gif");
        if (stream == null) throw new InvalidOperationException("Missing character");
        var next = new MemoryStream(); stream.CopyTo(next); next.Position = 0;
        var old = picture.Image; picture.Image = Image.FromStream(next); old?.Dispose(); imageStream?.Dispose(); imageStream = next;
    }
    void LayoutAgent() {
        ClientSize = new Size(Math.Max(280, agentSide + 20), agentSide + 100);
        picture.Bounds = new Rectangle((ClientSize.Width - agentSide) / 2, 100, agentSide, agentSide);
        reply.Bounds = new Rectangle(6, 8, ClientSize.Width - 12, 80);
    }
    void ShowReply(string text, string? placeId = null) {
        replyPlace = placeId; reply.SetReply(text); reply.Visible = true;
        replyTimer.Stop(); replyTimer.Start();
    }
    void Schedule(int milliseconds) { if (!IsDisposed) { timer.Interval = milliseconds; timer.Start(); } }
    async Task Poll()
    {
        if (busy || token == null) return; busy = true;
        try
        {
            var (status, json) = await Api("/agent/poll", new(){["capabilities"]=fileAccess.Catalog()});
            if (status == HttpStatusCode.Unauthorized) { ClearConnection(); await Pair(); return; }
            if (status != HttpStatusCode.OK) throw new InvalidOperationException();
            failures = 0;
            foreach (var item in json["mail"]?.AsArray() ?? new JsonArray())
            {
                string id = item!["id"]!.GetValue<string>();
                var handled = state["handled"]!.AsArray();
                if (!handled.Any(x => x?.GetValue<string>() == id))
                {
                    var data = item["payload"]!.AsObject();
                    string kind = item["kind"]!.GetValue<string>();
                    if (kind == "cancel") {var taskId=data["task_id"]?.GetValue<string>()??"";if(runningTasks.TryGetValue(taskId,out var active))active.Cancel();}
                    if (kind == "tool_call") {
                        if(state["task_journal"]![id]?["status"]?.GetValue<string>()=="running")continue;
                        state["task_journal"]![id]=new JsonObject{["status"]="running",["payload"]=data.DeepClone()};Save();
                        _ = ExecuteTask(id,(JsonObject)data.DeepClone());continue;
                    }
                    if (kind == "apps_request") QueueAppCatalog();
                    if (kind == "open_app") {
                        string appId = data["app_id"]!.GetValue<string>();
                        string requestId = data["request_id"]!.GetValue<string>();
                        var result = appAccess.Open(appId, data["expires_at"]?.GetValue<string>() ?? "0");
                        state["outgoing"]!.AsArray().Add(new JsonObject { ["id"] = Guid.NewGuid().ToString(), ["kind"] = "app_result", ["payload"] = new JsonObject { ["app_id"] = appId, ["request_id"] = requestId, ["result"] = result.Opened ? "opened" : "failed", ["message"] = result.Message } });
                        ShowReply(result.Message);
                    }
                    if (kind == "companion") {
                        long.TryParse(data["mood_until"]?.GetValue<string>(), out moodUntil);
                        var activity = moodUntil > DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() ? data["mood"]?.GetValue<string>() ?? "idle" : "idle";
                        SetCharacter(data["character"]?.GetValue<string>() ?? "tuck", activity);
                        agentSide = data["size"]?.GetValue<string>() switch { "small" => 138, "large" => 224, _ => 180 };
                        LayoutAgent();
                        if (activity == "listening") ShowReply("Listening on your phone…");
                    }
                    if(kind=="parked") {
                        string placeId=data["place_id"]!.GetValue<string>();
                        string placeStatus=data["status"]?.GetValue<string>()??"parked";
                        if(placeStatus is "parked" or "ready" or "finished") {
                            var places=state["places"]!.AsObject();
                            var place=places[placeId]?.AsObject()??new JsonObject{["sentence"]=""};
                            if(places[placeId]==null)places[placeId]=place;
                            if(place["status"]?.GetValue<string>()=="finished")placeStatus="finished";
                            place["status"]=placeStatus;
                            if(replyPlace==placeId&&placeStatus!="ready")reply.Visible=false;
                            if(placeStatus=="ready")activePlace=placeId;
                        }
                    }
                    if (kind == "place") {
                        string placeId = data["place_id"]!.GetValue<string>();
                        var places = state["places"]!.AsObject();
                        var place = places[placeId]?.AsObject() ?? new JsonObject();
                        if (places[placeId] == null) places[placeId] = place;
                        place["sentence"] = data["sentence"]!.GetValue<string>();
                        if(place["status"]?.GetValue<string>() is not ("parked" or "finished"))place["status"] = "ready";
                        activePlace = placeId;
                    }
                    handled.Add(id); while (handled.Count > 200) handled.RemoveAt(0);
                    Save();
                    if ((kind == "place" || kind=="parked"&&data["status"]?.GetValue<string>()=="ready") && activePlace != null && state["places"]![activePlace]?["status"]?.GetValue<string>()=="ready") ShowPlace(activePlace);
                }
                await Api("/agent/ack", new() { ["ids"] = new JsonArray(id) });
            }
            var outgoing = state["outgoing"]!.AsArray();
            foreach (var item in outgoing.ToArray()) {
                var (sent, _) = await Api("/agent/mail", item!.AsObject());
                if (sent == HttpStatusCode.OK || (sent==HttpStatusCode.NotFound && item?["kind"]?.GetValue<string>()=="tool_result")) { outgoing.Remove(item); Save(); }
            }
            if (moodUntil > 0 && moodUntil < DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()) { moodUntil = 0; SetCharacter(current ?? "tuck", "idle"); }
            var input = new LastInput { Size = (uint)Marshal.SizeOf<LastInput>() };
            bool idle = GetLastInputInfo(ref input) && unchecked((uint)Environment.TickCount - input.Time) >= 120000;
            if (idle && !away) {
                string id = Guid.NewGuid().ToString();
                var title = new StringBuilder(256); GetWindowText(GetForegroundWindow(), title, title.Capacity);
                state["places"]!.AsObject()[id] = new JsonObject { ["sentence"] = "", ["status"] = "waiting" };
                outgoing.Add(new JsonObject { ["id"] = Guid.NewGuid().ToString(), ["kind"] = "idle", ["payload"] = new JsonObject { ["place_id"] = id, ["app"] = title.ToString()[..Math.Min(title.Length,120)] } }); Save();
            }
            if (away && !idle && activePlace != null) ShowPlace(activePlace);
            away = idle;
        }
        catch { failures = Math.Min(failures + 1, 4); }
        finally { busy = false; if (token != null) Schedule(Math.Min(60000, 1000 * (1 << failures))); }
    }
    void ClearConnection() { timer.Stop(); replyTimer.Stop(); reply.Visible = false; SetCharacter(current ?? "tuck", "idle"); token = null; File.Delete(tokenFile);  }
    async Task Disconnect()
    {
        try
        {
            var (status, _) = await Api("/agent/revoke", new());
            if (status != HttpStatusCode.OK && status != HttpStatusCode.Unauthorized) throw new InvalidOperationException();
            ClearConnection(); await Pair();
        }
        catch { MessageBox.Show("Try again when you’re online, or disconnect from your phone.", "couldn’t disconnect"); }
    }
    void Save() { string temp = stateFile + ".tmp"; File.WriteAllText(temp, state.ToJsonString()); File.Move(temp, stateFile, true); }
    void ShowParked() {
        var parked = state["places"]!.AsObject().LastOrDefault(x => x.Value?["status"]?.GetValue<string>() == "parked");
        if (parked.Key != null) ShowPlace(parked.Key); else MessageBox.Show("No parked Places.", "Pico");
    }
    void ShowPlace(string id) {
        var place = state["places"]![id]!;
        if (place["status"]?.GetValue<string>() == "finished") return;
        var text = place["head_start"]?.GetValue<string>() ?? place["sentence"]?.GetValue<string>() ?? "";
        if (text.Length == 0) return;
        SetCharacter(current ?? "tuck", place["head_start"] != null ? "talking" : "idle");
        ShowReply(text, id);
    }
    void ShowPlaceDetails(string id) {
        var place = state["places"]![id]!;
        string sentence = place["sentence"]?.GetValue<string>() ?? "";
        if (sentence.Length == 0 || place["status"]?.GetValue<string>() == "finished") return;
        var form = new Form { Text = "Welcome back", ClientSize = new Size(380,220), StartPosition = FormStartPosition.CenterScreen, Font = new Font("Segoe UI",10), MaximizeBox = false, FormBorderStyle = FormBorderStyle.FixedDialog };
        var title = new Label { Text = "Welcome back", Location = new Point(20,20), AutoSize = true, Font = new Font("Segoe UI",17,FontStyle.Bold) };
        var text = new Label { Text = sentence, Location = new Point(20,62), Size = new Size(340,85) };
        var resume = new Button { Text = "Continue", Location = new Point(20,160), Size = new Size(164,36) };
        var park = new Button { Text = "Park it", Location = new Point(196,160), Size = new Size(164,36) };
        resume.Click += (_,_) => { Clipboard.SetText(sentence); place["status"] = "finished"; Save(); form.Close(); };
        park.Click += (_,_) => { place["status"] = "parked"; state["outgoing"]!.AsArray().Add(new JsonObject { ["id"] = Guid.NewGuid().ToString(), ["kind"] = "parked", ["payload"] = new JsonObject { ["place_id"] = id, ["sentence"] = sentence } }); Save(); form.Close(); };
        form.Controls.AddRange([title,text,resume,park]); form.Show();
    }
    [StructLayout(LayoutKind.Sequential)] struct LastInput { public uint Size; public uint Time; }
    [DllImport("user32.dll")] static extern bool GetLastInputInfo(ref LastInput input);
    [DllImport("user32.dll")] static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetWindowText(IntPtr window, StringBuilder title, int maximum);
    [DllImport("user32.dll")] static extern bool ReleaseCapture();
    [DllImport("user32.dll")] static extern IntPtr SendMessage(IntPtr window, int message, IntPtr wParam, IntPtr lParam);
}
