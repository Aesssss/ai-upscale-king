"""Collect dependency notices from the actual native build environment."""
from importlib import metadata
import json
import platform
import shutil
import sys
import urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'resources/licenses'; OUT.mkdir(parents=True, exist_ok=True)
packages = ('torch', 'Pillow', 'numpy', 'filelock', 'fsspec', 'jinja2', 'networkx',
            'sympy', 'typing_extensions', 'markupsafe', 'PySide6', 'PySide6_Essentials',
            'PySide6_Addons', 'shiboken6', 'pyinstaller', 'packaging', 'setuptools')
report = []
for name in packages:
    dist = metadata.distribution(name); copied = []
    for file in dist.files or []:
        if any(word in Path(file).name.lower() for word in ('license', 'copying', 'notice')):
            source = Path(dist.locate_file(file))
            if source.is_file():
                target = OUT / name / str(file)
                target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(source, target)
                copied.append(str(target.relative_to(OUT)))
    report.append({'package':name,'version':dist.version,'notices':copied})
python_license = [Path(sys.base_prefix)/'LICENSE.txt',
                  Path(sys.base_prefix)/f'lib/python{sys.version_info.major}.{sys.version_info.minor}/LICENSE.txt']
for candidate in python_license:
    if candidate.is_file():
        shutil.copyfile(candidate, OUT/'Python.txt'); break
else:
    url=f'https://raw.githubusercontent.com/python/cpython/v{platform.python_version()}/LICENSE'
    (OUT/'Python.txt').write_bytes(urllib.request.urlopen(url,timeout=45).read())
qt_version=metadata.version('PySide6')
for name in ('LGPL-3.0-only','GPL-3.0-only','Qt-GPL-exception-1.0','BSD-3-Clause','Apache-2.0'):
    target=OUT/f'Qt-{name}.txt'
    if target.is_file(): continue
    url=f'https://raw.githubusercontent.com/qt/qtbase/v{qt_version}/LICENSES/{name}.txt'
    target.write_bytes(urllib.request.urlopen(url,timeout=45).read())
(OUT/'package-manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
(ROOT/'resources/build-environment.json').write_text(json.dumps({'python':platform.python_version(),
    'system':platform.system(),'architecture':platform.machine(),'packages':{r['package']:r['version'] for r in report}},indent=2),encoding='utf-8')
print('Collected native dependency notices for',len(report),'packages')
