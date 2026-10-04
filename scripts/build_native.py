"""Build the actual native desktop executable on its target operating system."""
import json
import os
import platform
import subprocess
import sys
import tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.core import VERSION

if sys.platform not in ('darwin', 'win32'):
    raise SystemExit('Binary release builds require macOS or Windows')
if sys.platform == 'darwin' and platform.machine() != 'arm64':
    raise SystemExit('1.0 macOS releases require Apple Silicon')
if sys.platform == 'win32' and platform.machine().lower() not in ('amd64', 'x86_64'):
    raise SystemExit('1.0 Windows releases require x64')
stage = Path(tempfile.mkdtemp(prefix=f'aiupscale-{VERSION}-'))
env = {**os.environ, 'PYINSTALLER_CONFIG_DIR': str(stage / 'pyinstaller-cache')}
subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm',
    '--workpath', str(stage / 'build'), '--distpath', str(stage / 'dist'),
    str(ROOT / 'AIUpscaleKing.spec')], cwd=ROOT, env=env, check=True)
is_mac = sys.platform == 'darwin'
app = stage / 'dist' / ('AI 圖片放大王.app' if is_mac else 'AIUpscaleKing')
if is_mac:
    subprocess.run(['/usr/bin/xattr', '-crs', str(app)], check=True)
    subprocess.run(['/usr/bin/codesign', '--force', '--deep', '--sign', '-', str(app)], check=True)
    subprocess.run(['/usr/bin/codesign', '--verify', '--deep', '--strict', str(app)], check=True)
exe = app / ('Contents/MacOS/AI 圖片放大王' if is_mac else 'AIUpscaleKing.exe')
assert exe.is_file()
delivery = ROOT / 'delivery'; delivery.mkdir(exist_ok=True)
report = {'version': VERSION, 'app': str(app), 'executable': str(exe),
          'platform': 'macOS' if is_mac else 'Windows', 'architecture': platform.machine(),
          'signature_verified': is_mac, 'signing': 'ad-hoc' if is_mac else 'unsigned'}
(delivery / f'build-result-{VERSION}.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('Built native executable:', exe)
