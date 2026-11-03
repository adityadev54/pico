using System.Runtime.InteropServices;
using Microsoft.Win32;

sealed class CompanionMenu : Form
{
    readonly Rectangle anchor;
    readonly List<Button> rows = [];
    readonly Color border;
    readonly FlowLayoutPanel list;
    readonly Label heading;
    readonly Panel separator;

    internal CompanionMenu(Rectangle anchor, bool startup, Action toggleStartup, Action apps, Action parked, Func<Task> disconnect, Action quit, Action? folders = null, Action? teach = null, Action? settings = null, Action? focus = null, bool focused = false)
    {
        this.anchor = anchor;
        AutoScaleMode = AutoScaleMode.None;
        FormBorderStyle = FormBorderStyle.None; ShowInTaskbar = false; TopMost = true;
        StartPosition = FormStartPosition.Manual; Location = anchor.Location;
        AutoSize = false;
        Padding = new Padding(12); Font = new Font("Segoe UI", 10.5f);
        bool dark = false;
        try { using var theme = Registry.CurrentUser.OpenSubKey(@"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"); dark = theme?.GetValue("AppsUseLightTheme") is int light && light == 0; } catch { }
        BackColor = SystemInformation.HighContrast ? SystemColors.Menu : dark ? Color.FromArgb(35, 35, 35) : Color.FromArgb(250, 250, 250);
        ForeColor = SystemInformation.HighContrast ? SystemColors.MenuText : dark ? Color.FromArgb(245, 245, 245) : Color.FromArgb(35, 35, 35);
        border = SystemInformation.HighContrast ? SystemColors.WindowFrame : dark ? Color.FromArgb(67, 67, 67) : Color.FromArgb(224, 224, 224);
        var hover = SystemInformation.HighContrast ? SystemColors.Control : dark ? Color.FromArgb(54, 54, 54) : Color.FromArgb(235, 235, 235);
        list = new FlowLayoutPanel { FlowDirection = FlowDirection.TopDown, WrapContents = false, AutoSize = false, Dock = DockStyle.Fill, Margin = Padding.Empty, AutoScroll = true };
        heading = new Label { Text = "Pico", AutoSize = false, ForeColor = ForeColor, Font = new Font(Font, FontStyle.Bold) };
        list.Controls.Add(heading);
        void Add(string text, CompanionMenuIcon icon, Func<Task> action, bool check = false) {
            var row = new CompanionMenuRow { Text = text, AccessibleName = check ? text + ", enabled" : text, Icon = icon, IsChecked = check, BackColor = BackColor, ForeColor = ForeColor, HoverColor = hover, TabIndex = rows.Count };
            row.Click += async (_, _) => { Close(); try { await action(); } catch { MessageBox.Show("Couldn’t complete this action. Please try again.", "Pico"); } };
            rows.Add(row); list.Controls.Add(row);
        }
        if(focus!=null) Add(focused ? "I’m done — show results" : "I’m focused", CompanionMenuIcon.Parked, () => { focus(); return Task.CompletedTask; }, focused);
        if(teach!=null) Add("Teach a routine…", CompanionMenuIcon.Apps, () => { teach(); return Task.CompletedTask; });
        if(settings!=null) Add("Hold my place", CompanionMenuIcon.Parked, () => { settings(); return Task.CompletedTask; });
        Add("Open apps", CompanionMenuIcon.Apps, () => { apps(); return Task.CompletedTask; });
        if(folders!=null) Add("Folder permissions", CompanionMenuIcon.Apps, () => { folders(); return Task.CompletedTask; });
        Add("Open at sign-in", CompanionMenuIcon.Startup, () => { toggleStartup(); return Task.CompletedTask; }, startup);
        Add("Parked thoughts", CompanionMenuIcon.Parked, () => { parked(); return Task.CompletedTask; });
        separator = new Panel { BackColor = border };
        list.Controls.Add(separator);
        Add("Disconnect", CompanionMenuIcon.Disconnect, disconnect);
        Add("Quit Pico", CompanionMenuIcon.Quit, () => { quit(); return Task.CompletedTask; });
        Controls.Add(list);
        Deactivate += (_, _) => Close();
    }
    protected override void OnShown(EventArgs e)
    {
        base.OnShown(e);
        SizeToLabels(DeviceDpi);
        rows[0].Select();
    }
    // Measure the actual font at this monitor’s DPI; never scale only the icon gutters.
    void SizeToLabels(int dpi)
    {
        float scale = dpi / 96f;
        int Px(float value) => (int)Math.Ceiling(value * scale);
        var work = Screen.FromRectangle(anchor).WorkingArea;
        using var graphics = CreateGraphics();
        int measured = rows.Max(row => TextRenderer.MeasureText(graphics, row.Text, row.Font,
            new Size(int.MaxValue, int.MaxValue), TextFormatFlags.SingleLine | TextFormatFlags.NoPrefix).Width);
        int width = CompanionMenuMetrics.RowWidth(measured, dpi, work.Width - Px(48) - SystemInformation.VerticalScrollBarWidth);
        SuspendLayout(); list.SuspendLayout();
        Padding = new Padding(Px(12));
        heading.Size = new Size(Math.Max(1,width-Px(18)), Px(32));
        heading.Margin = new Padding(Px(18), Px(4), 0, Px(8));
        separator.Size = new Size(Math.Max(1,width-Px(36)), Math.Max(1,Px(1)));
        separator.Margin = new Padding(Px(18),Px(8),Px(18),Px(8));
        foreach (var row in rows) {
            int textWidth = Math.Max(1,width-Px(92));
            int textHeight = TextRenderer.MeasureText(graphics,row.Text,row.Font,new Size(textWidth,int.MaxValue),
                TextFormatFlags.WordBreak | TextFormatFlags.NoPrefix).Height;
            row.Size = new Size(width,Math.Max(Px(44),textHeight+Px(16)));
            row.Margin = new Padding(0,0,0,Px(4));
        }
        int height = list.Controls.Cast<Control>().Sum(control => control.Height + control.Margin.Vertical);
        int maxHeight = work.Height-Px(24);
        int scrollWidth = height+Padding.Vertical>maxHeight ? SystemInformation.VerticalScrollBarWidth : 0;
        ClientSize = new Size(width+Padding.Horizontal+scrollWidth,Math.Min(height+Padding.Vertical,maxHeight));
        list.ResumeLayout(true); ResumeLayout(true);
        Bounds = CompanionMenuPlacement.NextTo(anchor,Size,work,Px(12));
    }
    protected override void OnDpiChanged(DpiChangedEventArgs e)
    {
        base.OnDpiChanged(e);
        SizeToLabels(e.DeviceDpiNew);
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
