"""Compatibility entrypoint for the native macOS build."""
import runpy
import sys
from pathlib import Path
if sys.platform != 'darwin':
    raise SystemExit('Use build_native.py on Windows')
runpy.run_path(str(Path(__file__).with_name('build_native.py')), run_name='__main__')
