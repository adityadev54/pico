using System.Drawing.Drawing2D;
using System.ComponentModel;

internal enum CompanionMenuIcon { Apps, Startup, Parked, Disconnect, Quit }

sealed class CompanionMenuRow : Button
{
    [DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
    internal bool IsChecked { get; init; }
    [DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
    internal CompanionMenuIcon Icon { get; init; }
    [DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
    internal Color HoverColor { get; init; }
    bool hovering;

    internal CompanionMenuRow()
    {
        Size = new Size(288, 52); FlatStyle = FlatStyle.Flat;
        FlatAppearance.BorderSize = 0; TabStop = true;
        Font = new Font("Segoe UI", 10.5f); Cursor = Cursors.Hand;
        Margin = new Padding(0, 0, 0, 4);
        SetStyle(ControlStyles.UserPaint | ControlStyles.OptimizedDoubleBuffer | ControlStyles.AllPaintingInWmPaint, true);
    }
    protected override void OnMouseEnter(EventArgs e) { hovering = true; Invalidate(); base.OnMouseEnter(e); }
    protected override void OnMouseLeave(EventArgs e) { hovering = false; Invalidate(); base.OnMouseLeave(e); }
    protected override void OnGotFocus(EventArgs e) { Invalidate(); base.OnGotFocus(e); }
    protected override void OnLostFocus(EventArgs e) { Invalidate(); base.OnLostFocus(e); }
    protected override void OnPaint(PaintEventArgs e)
    {
        float scale = DeviceDpi / 96f;
        var g = e.Graphics; g.Clear(BackColor); g.SmoothingMode = SmoothingMode.AntiAlias;
        if (hovering || Focused) {
            using var fill = new SolidBrush(HoverColor);
            using var shape = Rounded(new RectangleF(1, 1, Width - 2, Height - 2), 9 * scale);
            g.FillPath(fill, shape);
        }
        int inset = (int)(52 * scale);
        TextRenderer.DrawText(g, Text, Font, new Rectangle(inset, 0, Width - inset - (int)(40 * scale), Height), ForeColor,
            TextFormatFlags.Left | TextFormatFlags.VerticalCenter | TextFormatFlags.EndEllipsis);
        using var pen = new Pen(ForeColor, 1.5f) { StartCap = LineCap.Round, EndCap = LineCap.Round, LineJoin = LineJoin.Round };
        var saved = g.Save(); g.TranslateTransform(18 * scale, Height / 2f - 8 * scale); g.ScaleTransform(scale, scale);
        switch (Icon) {
            case CompanionMenuIcon.Apps:
                g.DrawRectangle(pen, 1, 1, 14, 14); g.DrawLine(pen, 1, 5, 15, 5); g.DrawLine(pen, 5, 5, 5, 15); break;
            case CompanionMenuIcon.Startup:
                g.DrawLine(pen, 3, 12, 3, 3); g.DrawLine(pen, 3, 3, 12, 3);
                g.DrawLine(pen, 7, 11, 13, 5); g.DrawLines(pen, [new PointF(8, 5), new PointF(13, 5), new PointF(13, 10)]); break;
            case CompanionMenuIcon.Parked:
                g.DrawEllipse(pen, 1, 1, 14, 14); g.DrawLines(pen, [new PointF(8, 4), new PointF(8, 8), new PointF(11, 9)]); break;
            case CompanionMenuIcon.Disconnect:
                g.DrawLines(pen, [new PointF(6, 2), new PointF(2, 2), new PointF(2, 14), new PointF(6, 14)]);
                g.DrawLine(pen, 7, 8, 15, 8); g.DrawLines(pen, [new PointF(11, 4), new PointF(15, 8), new PointF(11, 12)]); break;
            case CompanionMenuIcon.Quit:
                g.DrawArc(pen, 1, 1, 14, 14, -50, 280); g.DrawLine(pen, 8, 0, 8, 7); break;
        }
        g.Restore(saved);
        if (IsChecked) {
            using var tick = new Pen(ForeColor, 1.8f * scale) { StartCap = LineCap.Round, EndCap = LineCap.Round };
            float x = Width - 26 * scale, y = Height / 2f;
            g.DrawLines(tick, [new PointF(x - 4 * scale, y), new PointF(x - scale, y + 3 * scale), new PointF(x + 5 * scale, y - 4 * scale)]);
        }
        if (Focused && ShowFocusCues) ControlPaint.DrawFocusRectangle(g, new Rectangle(4, 4, Width - 8, Height - 8), ForeColor, BackColor);
    }
    internal static GraphicsPath Rounded(RectangleF r, float radius)
    {
        float d = radius * 2; var path = new GraphicsPath();
        path.AddArc(r.Left, r.Top, d, d, 180, 90); path.AddArc(r.Right - d, r.Top, d, d, 270, 90);
        path.AddArc(r.Right - d, r.Bottom - d, d, d, 0, 90); path.AddArc(r.Left, r.Bottom - d, d, d, 90, 90); path.CloseFigure(); return path;
    }
}
