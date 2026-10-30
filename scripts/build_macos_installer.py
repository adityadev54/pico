"""Build a self-contained Apple Silicon Pico.app and drag-to-Applications DMG."""
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
(ROOT/'downloads').mkdir(exist_ok=True)
os.chdir(ROOT)
build=ROOT/'build/installer-macos'
build.mkdir(parents=True,exist_ok=True)
config=build/'config';config.mkdir(exist_ok=True)
(config/'companion.json').write_text(json.dumps({'relay':os.environ.get('PICO_RELAY_URL','http://127.0.0.1:8765')}))
subprocess.run([sys.executable,'scripts/make_macos_app.py'],check=True)
subprocess.run(['swiftc','-target','arm64-apple-macos13.0','agents/native/macos_context.swift','-o','agents/native/macos_context'],check=True)
command=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--windowed','--name','Pico','--osx-bundle-identifier','com.pico.companion','--paths',str(ROOT/'agents'),'--distpath',str(build/'dist'),'--workpath',str(build/'work'),'--specpath',str(build),'--icon',str(ROOT/'assets/branding/app-icon.png'),'--add-data',str(ROOT/'assets/characters')+':assets/characters','--add-data',str(ROOT/'agents/prompts')+':agents/prompts','--add-data',str(config)+':config','--add-binary',str(ROOT/'agents/native/macos_context')+':native',str(ROOT/'agents/launch.py')]
subprocess.run(command,check=True)
app=build/'dist/Pico.app'
helpers=app/'Contents/Helpers';helpers.mkdir(exist_ok=True)
shutil.copytree(ROOT/'.local/Pico Overlay.app',helpers/'Pico Overlay.app',dirs_exist_ok=True)
plist=app/'Contents/Info.plist';info=plistlib.loads(plist.read_bytes());info.update({'LSMinimumSystemVersion':'13.0','CFBundleShortVersionString':'0.7.0','CFBundleVersion':'1','LSUIElement':True,'NSLocalNetworkUsageDescription':'Pico connects your phone to this companion.','NSHighResolutionCapable':True});plist.write_bytes(plistlib.dumps(info))
subprocess.run(['codesign','--force','--deep','--sign','-',str(app)],check=True)
disk=build/'disk';shutil.rmtree(disk,ignore_errors=True);disk.mkdir();shutil.copytree(app,disk/'Pico.app',symlinks=True);(disk/'Applications').symlink_to('/Applications')
out=ROOT/'downloads/Pico-macOS.dmg'
subprocess.run(['hdiutil','create','-volname','Pico','-srcfolder',str(disk),'-ov','-format','UDZO',str(out)],check=True)
print(out)
