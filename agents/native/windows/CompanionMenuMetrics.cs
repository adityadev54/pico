internal static class CompanionMenuMetrics {
 internal static int RowWidth(int measuredTextWidth,int dpi,int availableWidth) {
  double scale=Math.Max(1,dpi)/96d;
  int preferred=Math.Max((int)Math.Ceiling(288*scale),measuredTextWidth+(int)Math.Ceiling(92*scale));
  return Math.Min(preferred,Math.Max(1,availableWidth));
 }
}
