using System.Drawing.Drawing2D;
/// Retains PictureBox's original GIF playback and adds a small flow reaction.
internal sealed class MoodPictureBox : PictureBox {
    readonly System.Windows.Forms.Timer motion = new() { Interval = 40 };
    string reaction = "idle";
    long started;
    internal void SetReaction(string value) {
            if(reaction==value)return;
            reaction=value;started=Environment.TickCount64;
            if(new[]{"angry","curious","happy","sleepy","surprised"}.Contains(value) && SystemInformation.IsMenuAnimationEnabled)motion.Start();else motion.Stop();
            Invalidate();
    }
    internal MoodPictureBox(){motion.Tick+=(_,_)=>Invalidate();}
    protected override void OnPaint(PaintEventArgs e){
        var state=e.Graphics.Save();
        if(SystemInformation.IsMenuAnimationEnabled){
            double seconds=(Environment.TickCount64-started)/1000.0;
            float wave=(float)Math.Sin(seconds*Math.PI*2/2.4);
            e.Graphics.TranslateTransform(Width/2f,Height/2f);
            switch(reaction){
                case "angry":e.Graphics.TranslateTransform((float)Math.Sin(seconds*20)*2,0);break;
                case "curious":e.Graphics.RotateTransform(-2+wave*.6f);break;
                case "happy":e.Graphics.TranslateTransform(0,-wave*3);break;
                case "sleepy":e.Graphics.RotateTransform(wave*.8f);break;
                case "surprised":float scale=seconds<.6?1+(float)Math.Sin(seconds/.6*Math.PI)*.05f:1;e.Graphics.ScaleTransform(scale,scale);break;
            }
            e.Graphics.TranslateTransform(-Width/2f,-Height/2f);
        }
        base.OnPaint(e);e.Graphics.Restore(state);
    }
    protected override void Dispose(bool disposing){if(disposing)motion.Dispose();base.Dispose(disposing);}
}
