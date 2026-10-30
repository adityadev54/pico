using System.Drawing;

internal static class CompanionMenuPlacement
{
    internal static Rectangle NextTo(Rectangle agent, Size menu, Rectangle work, int gap)
    {
        int x = agent.Right + gap;
        int y = agent.Bottom - menu.Height;
        if (x + menu.Width > work.Right - gap) {
            x = agent.Left - gap - menu.Width;
            if (x < work.Left + gap) {
                x = agent.Left;
                y = agent.Top - gap - menu.Height >= work.Top + gap
                    ? agent.Top - gap - menu.Height : agent.Bottom + gap;
            }
        }
        x = Math.Clamp(x, work.Left + gap, Math.Max(work.Left + gap, work.Right - gap - menu.Width));
        y = Math.Clamp(y, work.Top + gap, Math.Max(work.Top + gap, work.Bottom - gap - menu.Height));
        return new Rectangle(x, y, menu.Width, menu.Height);
    }
}
