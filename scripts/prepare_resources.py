"""Prepare model weights, icons, user documentation and dependency notices at build time."""
import shutil
import subprocess
import sys
from pathlib import Path
from download_models import ensure_resources
ROOT = Path(__file__).resolve().parents[1]
ensure_resources()
for script in ('make_icon.py', 'collect_licenses.py'):
    subprocess.run([sys.executable, str(ROOT / 'scripts' / script)], check=True)
for filename in ('README.md', 'README.en.md', 'THIRD_PARTY_NOTICES.md', 'LICENSE', 'NOTICE'):
    shutil.copyfile(ROOT / filename, ROOT / 'resources' / filename)
shutil.copyfile(ROOT / 'docs/使用教學.md', ROOT / 'resources/使用說明.md')
print('Prepared offline application resources')
