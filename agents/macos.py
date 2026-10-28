"""macOS companion entry point. OS inspection stays in this module."""
import json
import threading
import subprocess
import sys
from pathlib import Path
from paths import resource_root
OS='macos'

def context(snapshot=None):
    binary = resource_root()/'native/macos_context' if getattr(sys, 'frozen', False) else Path(__file__).parent/'native/macos_context'
    if not binary.exists():
        return {'idle':0, 'app':'Unknown app', 'screen_access':False}
    args = [str(binary)] + (['snapshot', str(snapshot)] if snapshot else [])
    result = subprocess.run(args,capture_output=True,text=True,timeout=10,check=True)
    return json.loads(result.stdout)

def configure_background_app():
    """Keep the hidden Tk worker out of the Dock after Tk initializes AppKit."""
    import ctypes
    import ctypes.util
    ctypes.CDLL('/System/Library/Frameworks/AppKit.framework/AppKit')
    objc = ctypes.CDLL(ctypes.util.find_library('objc'))
    objc.objc_getClass.argtypes = [ctypes.c_char_p]
    objc.objc_getClass.restype = ctypes.c_void_p
    objc.sel_registerName.argtypes = [ctypes.c_char_p]
    objc.sel_registerName.restype = ctypes.c_void_p
    address = ctypes.cast(objc.objc_msgSend, ctypes.c_void_p).value
    shared = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(address)
    app = shared(objc.objc_getClass(b'NSApplication'), objc.sel_registerName(b'sharedApplication'))
    set_policy = ctypes.CFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_long)(address)
    if not set_policy(app, objc.sel_registerName(b'setActivationPolicy:'), 1):
        raise RuntimeError('Could not start Pico as a background companion.')

def configure_window(root):
    root.configure(bg='systemTransparent')
    root.wm_attributes('-transparent',True)
    return 'systemTransparent'

def reopen(bundle):
    if bundle and all(c.isalnum() or c in '.-_' for c in bundle):
        subprocess.Popen(['/usr/bin/open','-b',bundle])



def start_overlay(events):
    """Launch Pico’s transparent AppKit companion window."""
    root = resource_root()
    app = Path(sys.executable).resolve().parents[1]/'Helpers/Pico Overlay.app' if getattr(sys, 'frozen', False) else root/'.local/Pico Overlay.app'
    binary = app/'Contents/MacOS/PicoOverlay'
    if not binary.exists():
        raise RuntimeError('Run scripts/run_companion.sh to build the native Pico overlay.')
    process = subprocess.Popen([str(binary), str(root/'assets/characters')], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
    def actions():
        for line in process.stdout:
            action = line.strip()
            if action.startswith('{'):
                try:
                    value = json.loads(action)
                    if value.get('action') == 'pair':events.put(('native_pair',value.get('code','')))
                    elif value.get('action') in ('preferences','place_action','open_place','clear_snapshots','pause','unpair'):events.put(('native_panel',value))
                except (ValueError, TypeError):pass
                continue
            if action in ('permissions', 'parked', 'unpair', 'quit'):
                events.put(('overlay_action', action))
    threading.Thread(target=actions, daemon=True).start()
    return process

if __name__ == '__main__':
    from companion import run
    run(sys.modules[__name__])
