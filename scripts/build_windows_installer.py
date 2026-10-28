"""Cross-build a per-user Pico setup executable with bundled .NET."""
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]
relay=os.environ.get('PICO_RELAY_URL','http://127.0.0.1:8765')
config=ROOT/'agents/native/windows/RelayConfig.cs'
config.write_text('internal static class RelayConfig { internal const string Url = '+json.dumps(relay)+'; }\n')
output=ROOT/'build/installer-windows'
subprocess.run(['dotnet','publish',str(ROOT/'agents/native/windows/Pico.csproj'),'-c','Release','-r','win-x64','-o',str(output),'--nologo'],check=True)
shutil.copy2(output/'Pico.exe',ROOT/'downloads/Pico-Setup.exe')
print(ROOT/'downloads/Pico-Setup.exe')
