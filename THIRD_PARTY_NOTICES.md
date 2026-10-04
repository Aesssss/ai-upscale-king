# Bundled third-party notices

AI 圖片放大王 1.0.0 contains unmodified upstream model weights, an adapted RRDB inference architecture, and dynamically linked open-source libraries. Copyright and license notices are retained in `resources/licenses`. This application's original source code is licensed under Apache-2.0; see LICENSE and NOTICE. Each bundled component retains its own license.

| Component | Version / source | Notice |
|---|---|---|
| Real-ESRGAN model weights | https://github.com/xinntao/Real-ESRGAN | BSD-3-Clause; `Real-ESRGAN.txt` |
| RRDB architecture adapted from BasicSR | https://github.com/XPixelGroup/BasicSR | Apache-2.0; `BasicSR.txt`, attribution in `app/rrdbnet.py` |
| PySide6 / Shiboken6 | 6.11.2, https://code.qt.io/cgit/pyside/pyside-setup.git/ | LGPL-3.0; `Qt-LGPL-3.0-only.txt` |
| Qt dynamic libraries | 6.11.2, https://code.qt.io/cgit/qt/qtbase.git/ | LGPL-3.0 and third-party notices in `QtBase` |
| PyTorch | 2.14.1, https://github.com/pytorch/pytorch | Upstream composite license and bundled dependency notices under `torch` |
| Pillow | 11.3.0, https://github.com/python-pillow/Pillow | MIT-CMU; notice under `Pillow` |
| NumPy | 2.3.5, https://github.com/numpy/numpy | BSD and bundled dependency notices under `numpy` |
| Python runtime | Python 3.12; exact patch in `resources/build-environment.json`, https://www.python.org/ | Python Software Foundation; `Python.txt` |
| PyInstaller bootloader | 6.22.3, https://github.com/pyinstaller/pyinstaller | GPL with bootloader exception; notice under `pyinstaller` |

Supporting Python package notices are copied from their installed distributions. Exact versions and notice paths are recorded in `resources/licenses/package-manifest.json`. Additional Python package metadata in the App also retains the original distributions' notices.

Qt/PySide sources corresponding to the dynamic libraries can be obtained at:

- https://download.qt.io/archive/qt/6.11/6.11.2/single/
- https://code.qt.io/cgit/qt/qtbase.git/?h=v6.11.2
- https://code.qt.io/cgit/pyside/pyside-setup.git/?h=v6.11.2

Qt/PySide libraries are not modified. The supplied application source and build specification allow rebuilding against compatible replacement libraries. Reverse engineering for debugging modifications to those LGPL libraries is not prohibited. The macOS App uses ad-hoc signing; Windows builds are unsigned; it has no DRM or mechanism preventing replacement/rebuilding.

No BigIMG executable, proprietary application code or brand assets are redistributed in this software.
