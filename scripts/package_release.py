"""Package verified native releases, preserving Mac signatures and UTF-8 names."""
import hashlib
import json
import shutil
import struct
import subprocess
import sys
import zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from app.core import VERSION


def mark_utf8(path):
    with zipfile.ZipFile(path,metadata_encoding='utf-8') as archive:
        entries=archive.infolist(); central=archive.start_dir
    with path.open('r+b') as file:
        for entry in entries:
            file.seek(entry.header_offset+6); flag=struct.unpack('<H',file.read(2))[0]
            file.seek(entry.header_offset+6); file.write(struct.pack('<H',flag|0x800))
        position=central
        for _ in entries:
            file.seek(position); header=file.read(46); assert header[:4]==b'PK\x01\x02'
            flag=struct.unpack('<H',header[8:10])[0]
            file.seek(position+8); file.write(struct.pack('<H',flag|0x800))
            position+=46+sum(struct.unpack('<HHH',header[28:34]))


def source_archive(path):
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for directory in ('app','scripts','tests','resources','docs','.github'):
            for file in sorted((ROOT/directory).rglob('*')):
                if not file.is_file() or '__pycache__' in file.parts or file.name=='.DS_Store': continue
                if file.suffix in ('.pth','.pyc','.part') or 'AppIcon.iconset' in file.parts: continue
                z.write(file,file.relative_to(ROOT))
        for name in ('main.py','requirements.txt','AIUpscaleKing.spec','README.md','README.en.md',
                     'THIRD_PARTY_NOTICES.md','LICENSE','NOTICE','CHANGELOG.md','CONTRIBUTING.md','SECURITY.md','.gitignore'):
            z.write(ROOT/name,name)


if __name__=='__main__':
    delivery=ROOT/'delivery'
    build=json.loads((delivery/f'build-result-{VERSION}.json').read_text(encoding='utf-8'))
    verified=json.loads((delivery/f'AIUpscaleKing-{VERSION}-{build["platform"]}-verification.json').read_text(encoding='utf-8'))
    assert verified['passed'] and verified['version']==VERSION
    name=f'AIUpscaleKing-{VERSION}-{build["platform"]}-'+('arm64' if build['platform']=='macOS' else 'x64')
    archive=delivery/f'{name}.zip'; app=Path(build['app'])
    if build['platform']=='macOS':
        subprocess.run(['/usr/bin/ditto','-c','-k','--norsrc','--noextattr','--keepParent',str(app),str(archive)],check=True)
        mark_utf8(archive)
    else:
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            for file in sorted(app.rglob('*')):
                if file.is_file(): z.write(file,Path('AIUpscaleKing')/file.relative_to(app))
    with zipfile.ZipFile(archive) as z: assert z.testzip() is None
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    (delivery/f'{name}.sha256').write_text(f'{digest}  {archive.name}\n',encoding='utf-8')
    if build['platform']=='macOS':
        source=delivery/f'AIUpscaleKing-{VERSION}-source.zip'; source_archive(source)
        with zipfile.ZipFile(source) as z: assert z.testzip() is None
        (delivery/f'AIUpscaleKing-{VERSION}-source.sha256').write_text(
            f'{hashlib.sha256(source.read_bytes()).hexdigest()}  {source.name}\n',encoding='utf-8')
    print('Verified release ZIP:',archive)
