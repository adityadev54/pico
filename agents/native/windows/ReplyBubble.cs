using System.Drawing.Drawing2D;

/// Compact Pico speech bubble above the companion, with system colors.
sealed class ReplyBubble : Control
{
    public ReplyBubble() {
        SetStyle(ControlStyles.UserPaint | ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer, true);
        BackColor = Color.Magenta; ForeColor = SystemColors.WindowText;
        Font = new Font("Segoe UI", 9); Cursor = Cursors.Hand;
        AccessibleRole = AccessibleRole.PushButton;
    }
    public void SetReply(string text) { Text = text; AccessibleName = text; Invalidate(); }
    protected override void OnPaint(PaintEventArgs e) {
        e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
        var rect = new Rectangle(3, 3, Width - 7, Height - 15);
        using var path = new GraphicsPath(); const int diameter = 28;
        path.AddArc(rect.Left, rect.Top, diameter, diameter, 180, 90);
        path.AddArc(rect.Right - diameter, rect.Top, diameter, diameter, 270, 90);
        path.AddArc(rect.Right - diameter, rect.Bottom - diameter, diameter, diameter, 0, 90);
        path.AddLine(rect.Right - 14, rect.Bottom, Width / 2 + 5, rect.Bottom);
        path.AddBezier(Width / 2 + 5, rect.Bottom, Width / 2 + 4, rect.Bottom + 4, Width / 2 + 8, rect.Bottom + 6, Width / 2 + 8, rect.Bottom + 6);
        path.AddBezier(Width / 2 + 8, rect.Bottom + 6, Width / 2, rect.Bottom + 6, Width / 2 - 3, rect.Bottom, Width / 2 - 6, rect.Bottom);
        path.AddArc(rect.Left, rect.Bottom - diameter, diameter, diameter, 90, 90); path.CloseFigure();
        using var fill = new SolidBrush(SystemColors.Window); e.Graphics.FillPath(fill, path);
        using var pen = new Pen(SystemColors.ControlDark, .5f); e.Graphics.DrawPath(pen, path);
        TextRenderer.DrawText(e.Graphics, Text, Font, new Rectangle(15, 12, Width - 30, Height - 28), ForeColor,
            TextFormatFlags.WordBreak | TextFormatFlags.EndEllipsis | TextFormatFlags.NoPrefix);
    }
}
