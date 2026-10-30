"""Keep developer source separate from installer downloads; exclude secrets and builds."""
import hashlib
from pathlib import Path
import zipfile
ROOT=Path(__file__).resolve().parents[1]

def main():
    output=ROOT/'downloads';output.mkdir(exist_ok=True)
    with zipfile.ZipFile(output/'Pico-source.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for folder in ['agents','assets/characters','lib','website','relay','scripts','config','server']:
            for path in (ROOT/folder).rglob('*'):
                if not path.is_file() or any(part in ('__pycache__','bin','obj','.local') for part in path.parts):continue
                if path.name=='Info.md' or path.suffix not in ('.py','.dart','.md','.swift','.gif','.png','.json','.cs','.csproj','.ico','.sh','.css','.html','.js','.mjs'):continue
                archive.write(path,path.relative_to(ROOT))
        for name in ['README.md','pubspec.yaml','pubspec.lock','fly.toml','relay/Dockerfile']:
            archive.write(ROOT/name,name)
    names=['Pico-macOS.dmg','Pico-Setup.exe','Pico-Android.apk','Pico-source.zip']
    (output/'SHA256SUMS').write_text(''.join(hashlib.sha256((output/name).read_bytes()).hexdigest()+'  '+name+'\n' for name in names if (output/name).exists()))
    print('Updated source archive and installer SHA256 checksums.')
if __name__=='__main__':main()
