# Native builds and release checks

Use Python 3.12 in a virtual environment. PyInstaller must run on the target OS; a Mac cannot produce a verified native Windows executable by renaming its output.

## Source setup

```sh
git clone https://github.com/Aesssss/ai-upscale-king.git
cd ai-upscale-king
python -m venv .venv
```

Activate with `source .venv/bin/activate` on macOS, or `.venv\Scripts\Activate.ps1` in Windows PowerShell.

macOS Apple Silicon:

```sh
python -m pip install -r requirements.txt
```

Windows x64 (CPU package, no CUDA):

```powershell
python -m pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
```

Run `python scripts/prepare_resources.py` to fetch SHA-256-pinned model weights, generate icons, copy documentation and collect notices for the actual installed dependencies. This build-time step uses the network. The running application does not download models or send images.

## Tests and build

```sh
python -m unittest discover -s tests -v
python scripts/ui_check.py
python scripts/design_review.py
python scripts/build_native.py
python scripts/release_check.py
python scripts/package_release.py
```

The native build is staged in an unsynced temporary folder. On macOS it is ad-hoc signed and signature verified. On Windows it contains `AIUpscaleKing.exe` and dynamically linked dependencies under `_internal`.

`release_check.py` runs the packaged GUI, performs real local AI exports using synthetic fixtures, checks banner/custom geometry, verifies DPI/ICC/alpha, and checks both bundled model hashes. Results are saved in `delivery/`.

`package_release.py` preserves Mac symlinks and UTF-8 names, creates a Windows portable ZIP, adds an archive SHA-256 file, verifies CRCs, and emits a source ZIP. Model weights are not committed to Git or included in the source ZIP; the pinned download manifest and fetching tool support reconstruction.

## GitHub Actions

The workflow runs native Windows x64 and macOS arm64 jobs on pushes and pull requests. Those jobs install pinned packages, fetch/verify weights, execute tests, package, and exercise the actual executables.

To publish, use the **Build and release** workflow's manual run, check `publish`, and select `main`. A release job runs only after both platform jobs succeed. It creates/updates the matching `vVERSION` GitHub release and uploads ZIPs, SHA-256 files and build verification reports. It has `contents: write`; test/build jobs have read-only repository access. Publishing from pull requests is disabled.

The release is not Apple Developer ID notarized or Windows code signed. Adding those services requires the maintainer's own signing identities and credentials; they are not shipped in source or build logs.

## Third-party source and replacement

Qt/PySide libraries are unmodified and dynamically linked. Rebuild against compatible replacement versions, retain license notices, and adjust the pinned requirements when intentionally changing dependencies. Source links and notices are in `THIRD_PARTY_NOTICES.md` and `resources/licenses/`.
