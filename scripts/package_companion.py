"""Package a buildable public checkout, excluding credentials and local runtime state."""
import hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EXCLUDED_DIRS={'.git','.local','.venv','.venv-runtime','.dart_tool','.gradle','.symlinks','__pycache__','bin','obj','build','Pods','ephemeral','Flutter.framework','App.framework','node_modules'}
SECRET_NAMES={'key.properties','local.properties','.env','.DS_Store','connection.json','GoogleService-Info.plist','google-services.json'}
SECRET_SUFFIXES={'.jks','.keystore','.p12','.pfx','.pem','.key','.pyc','.sqlite','.db'}
def public_file(path):
    rel=path.relative_to(ROOT)
    return path.is_file() and not path.is_symlink() and not any(p in EXCLUDED_DIRS for p in rel.parts) and path.name not in SECRET_NAMES and not path.name.startswith('.env') and path.suffix not in SECRET_SUFFIXES and not any(p.startswith('AGENTS.md') or p in ('SKILL.md','CLAUDE.md') for p in rel.parts)
def main():
    output=ROOT/'downloads';output.mkdir(exist_ok=True)
    with zipfile.ZipFile(output/'Pico-source.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for folder in ('agents','assets','lib','website','relay','scripts','config','server','android','ios','macos','windows','web','test','docs'):
            for path in (ROOT/folder).rglob('*'):
                if public_file(path):archive.write(path,path.relative_to(ROOT))
        for name in ('README.md','pubspec.yaml','pubspec.lock','fly.toml','.dockerignore','requirements-document-tools.txt','RELEASE-NOTES.md'):
            path=ROOT/name
            if path.is_file():archive.write(path,name)
    names=['Pico-macOS.dmg','Pico-Setup.exe','Pico-Android.apk','Pico-source.zip']
    hashes={name:hashlib.sha256((output/name).read_bytes()).hexdigest() for name in names}
    (output/'SHA256SUMS').write_text(''.join(value+'  '+name+'\n' for name,value in hashes.items()))
    (output/'release.json').write_text(json.dumps({'version':'0.8.4','build':24,'mac_version':'0.8.3','relay':'https://pico-companion.fly.dev','iphone':'/phone/','files':{name:{'sha256':digest,'bytes':(output/name).stat().st_size} for name,digest in hashes.items()},'windows_version':'0.8.7','windows_limits':'Local window previews only; browsers and sensitive apps excluded. Word to PDF needs LibreOffice. Native Windows visual verification pending.'},indent=2)+'\n')
    with zipfile.ZipFile(output/'Pico-source.zip') as z:
        assert 'android/key.properties' not in z.namelist()
        assert 'agents/skills/contracts.py' in z.namelist()
        assert 'ios/Runner/Info.plist' in z.namelist()
    print('Public source archive and download checksums prepared; signing credentials excluded.')
if __name__=='__main__':main()
