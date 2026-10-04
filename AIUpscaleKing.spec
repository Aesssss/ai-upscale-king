# Native PyInstaller build: Windows x64 or macOS Apple Silicon.
from pathlib import Path
import sys
root = Path(SPECPATH)
sys.path.insert(0, str(root))
from app.core import VERSION
is_mac = sys.platform == 'darwin'
a = Analysis([str(root / 'main.py')], pathex=[str(root)],
    binaries=[], datas=[(str(root / 'resources'), 'resources'),
                          (str(root / 'LICENSE'), 'resources'),
                          (str(root / 'NOTICE'), 'resources')],
    hiddenimports=['PIL._imagingcms', 'PIL.TiffImagePlugin', 'PIL.JpegImagePlugin'],
    hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=['matplotlib', 'scipy', 'pandas', 'cv2', 'sklearn', 'tkinter',
              'torchvision', 'torchaudio', 'pytest', 'IPython', 'notebook',
              'tensorboard', 'tensorflow', 'triton', 'imageio', 'imageio_ffmpeg',
              'moviepy', 'mediapipe', 'lxml'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True,
    name='AI 圖片放大王' if is_mac else 'AIUpscaleKing',
    icon=str(root / ('resources/AppIcon.icns' if is_mac else 'resources/AppIcon.ico')),
    version=str(root / 'resources/windows-version.txt') if sys.platform == 'win32' else None,
    debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, console=False, disable_windowed_traceback=False,
    argv_emulation=False, target_arch=None, codesign_identity=None, entitlements_file=None)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='AIUpscaleKing')
if is_mac:
    app = BUNDLE(coll, name='AI 圖片放大王.app', icon=str(root / 'resources/AppIcon.icns'),
        bundle_identifier='com.aiupscaleking.desktop', info_plist={
            'CFBundleDisplayName': 'AI 圖片放大王',
            'CFBundleShortVersionString': VERSION, 'CFBundleVersion': VERSION,
            'LSMinimumSystemVersion': '14.0', 'NSHighResolutionCapable': True,
            'NSDesktopFolderUsageDescription': '讀取你選擇的圖片及儲存放大成品。',
            'NSDocumentsFolderUsageDescription': '讀取你選擇的圖片及儲存放大成品。',
            'NSDownloadsFolderUsageDescription': '讀取你選擇的圖片及儲存放大成品。',
            'NSHumanReadableCopyright': 'Copyright 2026 AI Upscale King contributors. Apache-2.0.'})
