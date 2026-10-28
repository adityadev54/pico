"""Windows companion entry point. Snapshot capture is unavailable in this first demo."""
import ctypes
from ctypes import wintypes
import sys
OS='windows'
class LastInput(ctypes.Structure):
    _fields_=[('cbSize',wintypes.UINT),('dwTime',wintypes.DWORD)]
def context(snapshot=None):
    info=LastInput();info.cbSize=ctypes.sizeof(info)
    ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info))
    idle=((ctypes.windll.kernel32.GetTickCount() - info.dwTime)&0xffffffff)/1000
    title=ctypes.create_unicode_buffer(512)
    ctypes.windll.user32.GetWindowTextW(ctypes.windll.user32.GetForegroundWindow(),title,512)
    return {'idle':idle,'app':title.value[:120] or 'Unknown app','screen_access':False}
def configure_window(root):
    root.configure(bg='#010101');root.wm_attributes('-transparentcolor','#010101');return '#010101'
def reopen(bundle):
    pass  # No arbitrary command or app launch from a remotely supplied string.
if __name__ == '__main__':
    from companion import run
    run(sys.modules[__name__])
