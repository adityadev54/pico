using System.Runtime.InteropServices;
using Microsoft.Win32;

sealed class CompanionMenu : Form
{
    readonly Rectangle anchor;
    readonly List<Button> rows = [];
    readonly Color border;

    internal CompanionMenu(Rectangle anchor, bool startup, Action toggleStartup, Action apps, Action parked, Func<Task> disconnect, Action quit, Action? folders = null)
    {
        this.anchor = anchor;
        AutoScaleDimensions = new SizeF(96, 96); AutoScaleMode = AutoScaleMode.Dpi;
        FormBorderStyle = FormBorderStyle.None; ShowInTaskbar = false; TopMost = true;
        StartPosition = FormStartPosition.Manual; Location = anchor.Location;
        AutoSize = true; AutoSizeMode = AutoSizeMode.GrowAndShrink;
        Padding = new Padding(12); Font = new Font("Segoe UI", 10.5f);
        bool dark = false;
        try { using var theme = Registry.CurrentUser.OpenSubKey(@"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"); dark = theme?.GetValue("AppsUseLightTheme") is int light && light == 0; } catch { }
        BackColor = SystemInformation.HighContrast ? SystemColors.Menu : dark ? Color.FromArgb(35, 35, 35) : Color.FromArgb(250, 250, 250);
        ForeColor = SystemInformation.HighContrast ? SystemColors.MenuText : dark ? Color.FromArgb(245, 245, 245) : Color.FromArgb(35, 35, 35);
        border = SystemInformation.HighContrast ? SystemColors.WindowFrame : dark ? Color.FromArgb(67, 67, 67) : Color.FromArgb(224, 224, 224);
        var hover = SystemInformation.HighContrast ? SystemColors.Control : dark ? Color.FromArgb(54, 54, 54) : Color.FromArgb(235, 235, 235);
        var list = new FlowLayoutPanel { FlowDirection = FlowDirection.TopDown, WrapContents = false, AutoSize = true, AutoSizeMode = AutoSizeMode.GrowAndShrink, Dock = DockStyle.Fill, Margin = Padding.Empty };
        list.Controls.Add(new Label { Text = "Pico", AutoSize = true, ForeColor = ForeColor, Margin = new Padding(18, 10, 0, 14), Font = new Font(Font, FontStyle.Bold) });
        void Add(string text, CompanionMenuIcon icon, Func<Task> action, bool check = false) {
            var row = new CompanionMenuRow { Text = text, AccessibleName = check ? text + ", enabled" : text, Icon = icon, IsChecked = check, BackColor = BackColor, ForeColor = ForeColor, HoverColor = hover, TabIndex = rows.Count };
            row.Click += async (_, _) => { Close(); try { await action(); } catch { MessageBox.Show("Couldn’t complete this action. Please try again.", "Pico"); } };
            rows.Add(row); list.Controls.Add(row);
        }
        Add("Open apps", CompanionMenuIcon.Apps, () => { apps(); return Task.CompletedTask; });
        if(folders!=null) Add("Folder permissions", CompanionMenuIcon.Apps, () => { folders(); return Task.CompletedTask; });
        Add("Open at sign-in", CompanionMenuIcon.Startup, () => { toggleStartup(); return Task.CompletedTask; }, startup);
        Add("Parked thoughts", CompanionMenuIcon.Parked, () => { parked(); return Task.CompletedTask; });
        list.Controls.Add(new Panel { Width = 252, Height = 1, BackColor = border, Margin = new Padding(18, 10, 18, 10) });
        Add("Disconnect", CompanionMenuIcon.Disconnect, disconnect);
        Add("Quit Pico", CompanionMenuIcon.Quit, () => { quit(); return Task.CompletedTask; });
        Controls.Add(list);
        Deactivate += (_, _) => Close();
    }
    protected override void OnShown(EventArgs e)
    {
        base.OnShown(e);
        Bounds = CompanionMenuPlacement.NextTo(anchor, Size, Screen.FromRectangle(anchor).WorkingArea, (int)(12 * DeviceDpi / 96f));
        rows[0].Select();
    }
    protected override void OnHandleCreated(EventArgs e)
    {
        base.OnHandleCreated(e);
        int corners = 2;
        try { DwmSetWindowAttribute(Handle, 33, ref corners, sizeof(int)); } catch (DllNotFoundException) { }
    }
    protected override void OnSizeChanged(EventArgs e)
    {
        base.OnSizeChanged(e);
        if (Environment.OSVersion.Version.Build < 22000 && Width > 32 && Height > 32) {
            using var path = CompanionMenuRow.Rounded(new RectangleF(0, 0, Width, Height), 12 * DeviceDpi / 96f);
            var previous = Region; Region = new Region(path); previous?.Dispose();
        }
    }
    protected override void OnPaint(PaintEventArgs e)
    {
        base.OnPaint(e);
        using var pen = new Pen(border);
        using var shape = CompanionMenuRow.Rounded(new RectangleF(.5f, .5f, Width - 1, Height - 1), 12 * DeviceDpi / 96f);
        e.Graphics.SmoothingMode = System.Drawing.Drawing2D.SmoothingMode.AntiAlias;
        e.Graphics.DrawPath(pen, shape);
    }
    protected override bool ProcessCmdKey(ref Message msg, Keys keyData)
    {
        if (keyData == Keys.Escape) { Close(); return true; }
        if (keyData is Keys.Down or Keys.Up) { SelectNextControl(ActiveControl, keyData == Keys.Down, true, true, true); return true; }
        return base.ProcessCmdKey(ref msg, keyData);
    }
    [DllImport("dwmapi.dll")] static extern int DwmSetWindowAttribute(IntPtr hwnd, int attribute, ref int value, int length);
}
