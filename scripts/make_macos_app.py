"""Build Pico's transparent AppKit character window. Networking stays in Python."""
import plistlib
import platform
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
app = ROOT / '.local/Pico Overlay.app'
contents = app / 'Contents'
binary = contents / 'MacOS/PicoOverlay'
source = ROOT / 'agents/native/PicoOverlay.swift'
panels = ROOT / 'agents/native/PicoPanels.swift'
bubble = ROOT / 'agents/native/PicoReplyBubble.swift'
binary.parent.mkdir(parents=True, exist_ok=True)
if not binary.exists() or max(source.stat().st_mtime, panels.stat().st_mtime, bubble.stat().st_mtime) > binary.stat().st_mtime:
    subprocess.run(['swiftc', '-target', platform.machine() + '-apple-macos13.0', str(source), str(panels), str(bubble), '-o', str(binary)], check=True)
info = {'CFBundleExecutable': 'PicoOverlay', 'CFBundleIdentifier': 'local.pico.overlay', 'CFBundleName': 'Pico', 'CFBundleDisplayName': 'Pico', 'CFBundlePackageType': 'APPL', 'CFBundleVersion': '1', 'CFBundleShortVersionString': '0.1.0', 'LSUIElement': True, 'NSHighResolutionCapable': True}
(contents / 'Info.plist').write_bytes(plistlib.dumps(info))
print('Built Pico native character window.')
