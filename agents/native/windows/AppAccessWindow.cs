sealed class AppAccessWindow : Form
{
    internal AppAccessWindow(AppAccessSettings settings, Action changed)
    {
        Text = "Pico apps"; Font = new Font("Segoe UI", 11);
        AutoScaleDimensions = new SizeF(96, 96); AutoScaleMode = AutoScaleMode.Dpi;
        ClientSize = new Size(680, 560); MinimumSize = new Size(560, 480);
        StartPosition = FormStartPosition.CenterScreen; MaximizeBox = false;
        var layout = new TableLayoutPanel { Dock = DockStyle.Fill, Padding = new Padding(24), ColumnCount = 1, RowCount = 7 };
        layout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        foreach (var row in new[] { new RowStyle(SizeType.AutoSize), new RowStyle(SizeType.Percent,50), new RowStyle(SizeType.AutoSize), new RowStyle(SizeType.AutoSize), new RowStyle(SizeType.Percent,50), new RowStyle(SizeType.AutoSize), new RowStyle(SizeType.AutoSize) }) layout.RowStyles.Add(row);
        var status = new Label { AutoSize = true, Dock = DockStyle.Fill, MinimumSize = new Size(0, 42), Margin = new Padding(0,12,0,0) };
        var allowed = new ListBox { Dock = DockStyle.Fill, BorderStyle = BorderStyle.FixedSingle, IntegralHeight = false, DisplayMember = "Name", Margin = new Padding(0,0,0,12) };
        var excluded = new ListBox { Dock = DockStyle.Fill, BorderStyle = BorderStyle.FixedSingle, IntegralHeight = false, DisplayMember = "Name", Margin = new Padding(0,0,0,12) };
        void Reload() { allowed.DataSource = settings.Allowed.ToList(); excluded.DataSource = settings.Excluded.ToList(); }
        void Edit(Action edit) { try { edit(); Reload(); changed(); status.Text = "Saved."; } catch(Exception e) { status.Text = e is InvalidOperationException ? e.Message : "Couldn’t save app permissions. Please try again."; } }
        FlowLayoutPanel Actions(ListBox list, bool exclusion) {
            var actions = new FlowLayoutPanel { AutoSize = true, Dock = DockStyle.Fill, WrapContents = true, Margin = new Padding(0,0,0,12) };
            var add = new Button { Text = "Choose app…", AutoSize = true, MinimumSize = new Size(120,40), Margin = new Padding(0,0,12,0) };
            add.Click += (_,_) => { using var picker = new OpenFileDialog { Title = exclusion ? "Never snapshot this app" : "Allow Pico to open this app", Filter = "Applications (*.exe)|*.exe", CheckFileExists = true, Multiselect = false, InitialDirectory = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles) }; if (picker.ShowDialog(this) == DialogResult.OK) Edit(() => settings.Add(picker.FileName, exclusion)); };
            actions.Controls.Add(add);
            if (!exclusion) {
                var open = new Button { Text = "Open", AutoSize = true, MinimumSize = new Size(90,40), Margin = new Padding(0,0,12,0) };
                open.Click += (_,_) => { if(list.SelectedItem is AppGrant app) status.Text = settings.Open(app.Id).Message; }; actions.Controls.Add(open);
            }
            var remove = new Button { Text = "Remove", AutoSize = true, MinimumSize = new Size(90,40), Margin = Padding.Empty };
            remove.Click += (_,_) => { if(list.SelectedItem is AppGrant app) Edit(() => settings.Remove(app.Id, exclusion)); }; actions.Controls.Add(remove);
            return actions;
        }
        layout.Controls.Add(new Label { Text = "Apps Pico can open", AutoSize = true, Font = new Font(Font, FontStyle.Bold), Margin = new Padding(0,0,0,12) },0,0);
        layout.Controls.Add(allowed,0,1); layout.Controls.Add(Actions(allowed,false),0,2);
        layout.Controls.Add(new Label { Text = "Never snapshot these apps\nWindows snapshots are currently off. Opening an app does not grant snapshot access.", AutoSize = true, Dock = DockStyle.Fill, Margin = new Padding(0,0,0,12) },0,3);
        layout.Controls.Add(excluded,0,4); layout.Controls.Add(Actions(excluded,true),0,5); layout.Controls.Add(status,0,6);
        Controls.Add(layout); Reload();
        Shown += (_,_) => { var work = Screen.FromControl(this).WorkingArea; Size = new Size(Math.Min(Width,work.Width-24),Math.Min(Height,work.Height-24)); };
    }
}
