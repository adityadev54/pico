using System.Drawing;
using System.Windows.Forms;

sealed class PairingWindow : Form
{
    readonly TextBox code = new() { MaxLength = 12, Dock = DockStyle.Top, Font = new Font("Segoe UI", 20), PlaceholderText = "Connection code" };
    readonly Label message = new() { AutoSize = true, Dock = DockStyle.Fill, MinimumSize = new Size(0, 48), Margin = new Padding(0, 12, 0, 12) };
    readonly Button connect = new() { Text = "Connect", AutoSize = true, MinimumSize = new Size(120, 40), Anchor = AnchorStyles.Right, Margin = Padding.Empty };
    readonly Func<string, Task<string?>> claim;
    bool connecting;

    internal PairingWindow(Func<string, Task<string?>> claim)
    {
        this.claim = claim;
        Font = new Font("Segoe UI", 10);
        AutoScaleDimensions = new SizeF(96, 96);
        AutoScaleMode = AutoScaleMode.Dpi;
        Text = "Connect Pico";
        ClientSize = new Size(720, 460);
        AutoSize = true;
        AutoSizeMode = AutoSizeMode.GrowOnly;
        MinimumSize = new Size(720, 460);
        StartPosition = FormStartPosition.CenterScreen;
        MaximizeBox = false;
        MinimizeBox = false;
        BackColor = SystemColors.Window;
        ForeColor = SystemColors.WindowText;
        var layout = new TableLayoutPanel {
            Dock = DockStyle.Top, Padding = new Padding(32), AutoScroll = false,
            AutoSize = true, AutoSizeMode = AutoSizeMode.GrowAndShrink,
            ColumnCount = 1, RowCount = 5
        };
        layout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        for (var i = 0; i < 5; i++) layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        layout.Controls.Add(new Label {
            Text = "Connect your companion", AutoSize = true, Dock = DockStyle.Fill,
            Font = new Font("Segoe UI", 18), Margin = new Padding(0, 0, 0, 12)
        }, 0, 0);
        layout.Controls.Add(new Label {
            Text = "Enter the six-digit code from Pico on your phone.", AutoSize = true,
            Dock = DockStyle.Fill, Margin = new Padding(0, 0, 0, 12)
        }, 0, 1);
        code.Margin = Padding.Empty;
        layout.Controls.Add(code, 0, 2);
        layout.Controls.Add(message, 0, 3);
        layout.Controls.Add(connect, 0, 4);
        layout.Layout += (_, _) => {
            int width = Math.Max(1, layout.ClientSize.Width - layout.Padding.Horizontal);
            if (message.MaximumSize.Width != width) message.MaximumSize = new Size(width, 0);
        };
        Controls.Add(layout);
        AcceptButton = connect;
        connect.Click += async (_, _) => await Connect();
        Shown += (_, _) => code.Focus();
        FormClosing += (_, e) => { if (connecting) e.Cancel = true; };
    }

    async Task Connect()
    {
        if (connecting) return;
        string value = string.Concat(code.Text.Where(c => !char.IsWhiteSpace(c)));
        if (value.Length != 6 || !value.All(char.IsAsciiDigit)) {
            message.Text = "Enter the six-digit code from your phone.";
            code.Focus(); return;
        }
        connecting = true; connect.Enabled = false; code.Enabled = false;
        message.Text = "Connecting…";
        string? error;
        try { error = await claim(value); }
        catch { error = "Couldn’t connect. Please try again."; }
        finally { connecting = false; connect.Enabled = true; code.Enabled = true; }
        if (IsDisposed) return;
        if (error == null) { DialogResult = DialogResult.OK; return; }
        message.Text = error;
        code.Focus(); code.SelectAll();
    }
}
