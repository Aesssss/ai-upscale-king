# AI Upscale King · AI 圖片放大王

**Upscale AI-generated images to print dimensions, entirely on your own computer.**

An open-source desktop tool for designers, illustrators and print production. Supports A1–A5, custom dimensions in centimetres, 300 DPI, batch exports and local detail comparisons. Image orientation and aspect ratio are preserved by default.

[Download releases](https://github.com/Aesssss/ai-upscale-king/releases) · [Traditional Chinese guide](docs/使用教學.md) · [Build from source](docs/BUILDING.md) · [繁體中文](README.md)

![Custom print size](docs/images/custom-size.png)

## Quick start

1. Extract the release for your operating system. No Python, account or separate model installation is needed.
2. Drop in images and choose A1 or custom dimensions. Resolution defaults to 300 DPI.
3. Click the upscale button and choose where to save.

| Package | Supported system |
|---|---|
| `AIUpscaleKing-1.0.0-macOS-arm64.zip` | Apple Silicon, macOS 14+ |
| `AIUpscaleKing-1.0.0-Windows-x64.zip` | Windows 10 / 11, x64 |

Move the Mac App into a local Applications folder. On Windows, extract the entire folder and run `AIUpscaleKing.exe`; keep its `_internal` folder alongside it. The Windows package uses CPU inference without CUDA. The Mac package uses available Apple GPU acceleration. Intel Macs and Windows ARM are not binary release targets for 1.0.

SHA-256 checksums accompany releases. Mac builds are ad-hoc signed, not Developer ID notarized. Windows builds are not code signed. Follow normal operating-system approval flows; do not disable system security globally.

## Proportional print sizing

Selected dimensions form a bounding rectangle, arranged to follow the source orientation. The app fits the largest proportional image within those bounds, without padding, cropping or stretching by default.

| Source | Target | Export |
|---|---|---|
| Landscape 3:1 banner | A1, 300 DPI | 9934 × 3311 px; about 84.1 × 28.0 cm |
| Portrait 2:3 | 40 × 60 cm, 300 DPI | 4725 × 7087 px |
| Landscape 3:2 | 40 × 60 cm, 300 DPI | 7087 × 4725 px |
| Landscape 3:1 | 40 × 60 cm, 300 DPI | 7087 × 2362 px; about 60 × 20 cm |

The actual centimetres and pixel dimensions are shown before export. Custom sides accept 0.1–199 cm. Resolution accepts 50–600 DPI. Integer-pixel rounding can produce a small aspect deviation of approximately one pixel.

## Features and limits

- Bundled Real-ESRGAN photo and anime models with tiled local inference.
- Faithful Lanczos scaling for text and logos.
- PNG, TIFF and JPEG exports; PNG/TIFF retain transparency.
- EXIF orientation, source ICC conversion, embedded sRGB profile and DPI.
- Batch processing, local comparisons, cancellation and per-file errors.
- Standard mode performs AI 4× then resizes to the target. Detail mode can apply a second AI pass; added details can change faces, text or small symbols.
- 8-bit sRGB output only. 16-bit / floating-point sources are rejected; CMYK output is not supported. Convert using your printer's ICC in a design application when required.
- Maximum output: 160 million pixels. Maximum AI intermediate image: 320 million pixels. Large files and CPU inference take longer.

Pixel dimensions and DPI are not a guarantee of true recovered detail or print quality. Inspect important content and make a print proof. Advanced padding/cropping modes are explicit opt-in choices.

## Privacy

There are no image uploads, cloud inference, accounts, telemetry, runtime model downloads or update checks. Input images are not overwritten. Exported images do not copy source EXIF/GPS. Build-time dependency/model downloads are separate from offline runtime operation.

Files in Dropbox/iCloud or other synced folders may still sync through those services. Use local unsynced folders for sensitive work.

## Development and licensing

Python 3.12; see [BUILDING](docs/BUILDING.md) for native builds, tests and release checks. Models are fetched by the build tool from upstream releases and verified against pinned SHA-256 hashes. They are bundled in desktop releases for offline use.

Application code is [Apache-2.0](LICENSE). Bundled models and libraries retain their own licenses; see [THIRD_PARTY_NOTICES](THIRD_PARTY_NOTICES.md) and [NOTICE](NOTICE). Qt/PySide libraries remain dynamically linked and replaceable through rebuilding.

[Contributing](CONTRIBUTING.md) · [Changelog](CHANGELOG.md) · [Security](SECURITY.md)
