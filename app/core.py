"""Offline processing. This module makes no network requests."""
from __future__ import annotations

import gc
import hashlib
import io
import json
import math
import os
import shutil
import sys
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, asdict
from functools import lru_cache
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image, ImageCms, ImageOps

APP_NAME = 'AI 圖片放大王'
VERSION = '1.0.0'
PRESETS = {'A1': (594, 841), 'A2': (420, 594), 'A3': (297, 420),
           'A4': (210, 297), 'A5': (148, 210), '自訂': (400, 600)}
MAX_OUTPUT_PIXELS = 160_000_000
MAX_AI_PIXELS = 320_000_000
Image.MAX_IMAGE_PIXELS = 90_000_000
SUPPORTED = {'.png', '.jpg', '.jpeg', '.tif', '.tiff', '.webp', '.bmp'}
Progress = Callable[[int, str], None]


class Cancelled(Exception):
    pass


@dataclass(frozen=True)
class Options:
    width_mm: float = 594
    height_mm: float = 841
    ppi: int = 300
    bleed_mm: float = 0
    fit: str = 'image'
    auto_orientation: bool = True
    model: str = 'photo'
    strategy: str = 'standard'
    format: str = 'png'
    jpeg_quality: int = 95
    tile: int = 128
    device: str = 'auto'

    @property
    def pixels(self):
        return print_pixels(self.width_mm + self.bleed_mm * 2,
                            self.height_mm + self.bleed_mm * 2, self.ppi)


def resource_path(relative: str) -> Path:
    root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1]))
    return root / 'resources' / relative


def print_pixels(width_mm, height_mm, ppi):
    if not (0 < width_mm <= 2000 and 0 < height_mm <= 2000 and 50 <= ppi <= 600):
        raise ValueError('尺寸須在 1–2000 mm 內，解析度須在 50–600 PPI 內。')
    return math.ceil(width_mm * ppi / 25.4), math.ceil(height_mm * ppi / 25.4)


def content_size(source_size, target_size, fit):
    sw, sh = source_size
    tw, th = target_size
    if fit not in {'contain', 'cover', 'image'}:
        raise ValueError('不支援的比例處理方式。')
    ratio = max(tw / sw, th / sh) if fit == 'cover' else min(tw / sw, th / sh)
    return max(1, round(sw * ratio)), max(1, round(sh * ratio)), ratio


def output_geometry(source_size, options):
    """Paper dimensions are bounds; orientation follows EXIF-corrected source pixels."""
    target = options.pixels
    if options.auto_orientation:
        short, long = sorted(target)
        target = (long, short) if source_size[0] > source_size[1] else (short, long)
    width, height, ratio = content_size(source_size, target, options.fit)
    return target, (width, height) if options.fit == 'image' else target, ratio


@lru_cache(maxsize=1)
def srgb_profile():
    return ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()


def load_image(path: Path):
    """Apply orientation and transform tagged 8-bit input to sRGB; retain alpha."""
    with Image.open(path) as opened:
        if opened.width * opened.height > 90_000_000:
            raise ValueError('來源超過本版 9000 萬像素上限，請先縮小來源副本。')
        if getattr(opened, 'n_frames', 1) > 1:
            raise ValueError('請使用單張圖片；多頁 TIFF／動畫請先匯出要放大的那一張。')
        bits = opened.tag_v2.get(258, (8,)) if opened.format == 'TIFF' else (8,)
        bits = (bits,) if isinstance(bits, int) else bits
        # Pillow silently reduces 16-bit RGB PNG to 8-bit on decode: inspect IHDR first.
        png_depth = 8
        if opened.format == 'PNG':
            with Path(path).open('rb') as header:
                png_depth = header.read(25)[24]
        if opened.mode in ('I', 'F', 'I;16', 'I;16B', 'I;16L') or (
                opened.format == 'TIFF' and max(bits) > 8) or png_depth > 8:
            raise ValueError('本版處理 8-bit 圖片。請先將 16-bit／浮點來源轉成 8-bit 副本。')
        profile = opened.info.get('icc_profile')
        im = ImageOps.exif_transpose(opened)
        alpha = im.convert('RGBA').getchannel('A') if ('A' in im.getbands() or 'transparency' in im.info) else None
        if im.mode == 'CMYK' and not profile:
            raise ValueError('這張 CMYK 圖片沒有 ICC 描述檔，請先用設計軟件轉成有描述檔的 RGB 副本。')
        color = im if im.mode == 'CMYK' else im.convert('RGB')
        if profile:
            try:
                color = ImageCms.profileToProfile(color, ImageCms.ImageCmsProfile(io.BytesIO(profile)),
                                                 ImageCms.createProfile('sRGB'), outputMode='RGB')
            except Exception as exc:
                raise ValueError('無法讀取來源 ICC 色彩描述檔，請先另存有效的 RGB 副本。') from exc
        else:
            color = color.convert('RGB')
        color.load()
        color = color.copy()
        if alpha is not None:
            color.putalpha(alpha)
        return color, {'size': color.size, 'alpha': alpha is not None,
                       'source_profile': 'ICC 已轉換為 sRGB' if profile else '未附 ICC，按 sRGB 處理'}


def compose_image(image, target, fit):
    width, height, _ = content_size(image.size, target, fit)
    resized = image.resize((width, height), Image.Resampling.LANCZOS)
    if fit == 'image':
        return resized
    if fit == 'cover':
        x, y = max(0, (width - target[0]) // 2), max(0, (height - target[1]) // 2)
        return resized.crop((x, y, x + target[0], y + target[1]))
    background = (0, 0, 0, 0) if image.mode == 'RGBA' else (255, 255, 255)
    canvas = Image.new(image.mode, target, background)
    # Do not supply alpha as a mask: it would multiply alpha twice.
    canvas.paste(resized, ((target[0] - width) // 2, (target[1] - height) // 2))
    return canvas


def device_name(preference='auto'):
    import torch
    if preference == 'cpu':
        return 'cpu'
    if torch.cuda.is_available():
        return 'cuda'
    if torch.backends.mps.is_available():
        return 'mps'
    return 'cpu'


_model_cache = {}


def load_model(kind, device):
    import torch
    from app.rrdbnet import RRDBNet
    if kind not in ('photo', 'anime'):
        raise ValueError('不支援的 AI 模型。')
    key = (kind, device)
    if key not in _model_cache:
        # Retain only one model so switching modes does not accumulate GPU memory.
        _model_cache.clear()
        gc.collect()
        if device == 'mps':
            torch.mps.empty_cache()
        file = 'RealESRGAN_x4plus.pth' if kind == 'photo' else 'RealESRGAN_x4plus_anime_6B.pth'
        path = resource_path('models/' + file)
        manifest = json.loads(resource_path('model-manifest.json').read_text())
        entry = next((e for e in manifest if e['file'] == 'models/' + file), None)
        if not path.is_file() or entry is None or hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('本地 AI 模型缺失或校驗失敗，請重新解壓完整的應用程式。')
        model = RRDBNet(num_block=23 if kind == 'photo' else 6)
        state = torch.load(path, map_location='cpu', weights_only=True)
        model.load_state_dict(state.get('params_ema', state.get('params', state)), strict=True)
        model.eval().to(device)
        _model_cache[key] = model
    return _model_cache[key]


def check_cancel(event):
    if event.is_set():
        raise Cancelled('工作已取消；原圖保留。')


def ai_x4(image, kind, device, tile, event, progress, temp_dir, low=5, high=80):
    import torch
    width, height = image.size
    if width * height * 16 > MAX_AI_PIXELS:
        raise ValueError('來源太大，AI 中間圖會超過本版的記憶體預算。請使用保真模式或先縮小來源副本。')
    check_cancel(event)
    progress(low, '正在載入本地 AI 模型…')
    model = load_model(kind, device)
    raw = np.asarray(image.convert('RGB'))
    tiles_x, tiles_y = math.ceil(width / tile), math.ceil(height / tile)
    total = tiles_x * tiles_y
    path = Path(temp_dir) / (uuid.uuid4().hex + '.rgb')
    data = np.memmap(path, dtype=np.uint8, mode='w+', shape=(height * 4, width * 4, 3))
    os.chmod(path, 0o600)
    pad = 24
    completed = 0
    try:
        with torch.inference_mode():
            for row in range(tiles_y):
                for col in range(tiles_x):
                    check_cancel(event)
                    x, y = col * tile, row * tile
                    end_x, end_y = min(x + tile, width), min(y + tile, height)
                    left, top = max(0, x - pad), max(0, y - pad)
                    right, bottom = min(width, end_x + pad), min(height, end_y + pad)
                    array = raw[top:bottom, left:right].copy()
                    tensor = torch.from_numpy(array).permute(2, 0, 1).unsqueeze(0).to(device=device, dtype=torch.float32) / 255
                    result = model(tensor).squeeze(0).clamp_(0, 1)
                    if not bool(torch.isfinite(result).all().item()):
                        raise RuntimeError('AI 運算出現無效數值，請改用 CPU 或保真模式。')
                    result = result.permute(1, 2, 0).mul(255).round().byte().cpu().numpy()
                    cx, cy = (x - left) * 4, (y - top) * 4
                    data[y * 4:end_y * 4, x * 4:end_x * 4] = result[cy:cy + (end_y - y) * 4, cx:cx + (end_x - x) * 4]
                    del tensor, result
                    completed += 1
                    progress(low + round((high - low) * completed / total),
                             f'AI 放大中 · {completed} / {total} 個區塊')
        data.flush()
        output = Image.fromarray(data).copy()
    finally:
        del data
        if device == 'mps':
            torch.mps.empty_cache()
    return output


def save_output(image, destination, options, event):
    """Write beside destination, verify metadata, then atomically replace."""
    check_cancel(event)
    destination.parent.mkdir(parents=True, exist_ok=True)
    expected_size = image.size
    temporary = destination.with_name('.' + destination.name + '.' + uuid.uuid4().hex + '.part')
    fmt = options.format.upper()
    try:
        if fmt in ('JPG', 'JPEG'):
            if image.mode == 'RGBA':
                background = Image.new('RGB', image.size, 'white')
                background.paste(image, mask=image.getchannel('A'))
                image = background
            image.save(temporary, format='JPEG', quality=options.jpeg_quality, subsampling=0,
                       dpi=(options.ppi, options.ppi), icc_profile=srgb_profile())
        elif fmt == 'TIFF':
            image.save(temporary, format='TIFF', compression='tiff_lzw',
                       dpi=(options.ppi, options.ppi), icc_profile=srgb_profile())
        elif fmt == 'PNG':
            image.save(temporary, format='PNG', compress_level=3,
                       dpi=(options.ppi, options.ppi), icc_profile=srgb_profile())
        else:
            raise ValueError('不支援的輸出格式。')
        check_cancel(event)
        with Image.open(temporary) as verified:
            if verified.size != expected_size or not verified.info.get('icc_profile'):
                raise RuntimeError('輸出尺寸或色彩資訊驗證失敗。')
            actual_ppi = verified.info.get('dpi', (0, 0))
            if any(abs(float(v) - options.ppi) > 0.1 for v in actual_ppi[:2]):
                raise RuntimeError('輸出解析度資訊驗證失敗。')
            verified.verify()
        temporary.replace(destination)
    finally:
        if temporary.exists():
            temporary.unlink()


def process_image(source, destination, options, event=None, progress=None):
    event = event or threading.Event()
    progress = progress or (lambda *_: None)
    source, destination = Path(source), Path(destination)
    if source.resolve() == destination.resolve():
        raise ValueError('輸出不能覆寫來源圖片，請使用另一個檔名。')
    started = time.monotonic()
    progress(1, '正在讀取圖片與色彩資訊…')
    image, meta = load_image(source)
    target, expected, ratio = output_geometry(image.size, options)
    if expected[0] * expected[1] > MAX_OUTPUT_PIXELS:
        raise ValueError('輸出超過本版 1.6 億像素上限，請降低尺寸或解析度。')
    scratch_bytes = max(image.width * image.height * 16 * 3, expected[0] * expected[1] * 6)
    if shutil.disk_usage(tempfile.gettempdir()).free < scratch_bytes + 512_000_000:
        raise ValueError('本機暫存空間不足，請釋放空間後再試。')
    device = device_name(options.device) if options.model != 'faithful' else 'cpu'
    ai_passes = 0
    alpha = image.getchannel('A') if image.mode == 'RGBA' else None
    rgb = image.convert('RGB')
    if options.model != 'faithful' and ratio > 1:
        with tempfile.TemporaryDirectory(prefix='image-upscale-king-') as temporary:
            os.chmod(temporary, 0o700)
            first_high = 45 if options.strategy == 'detail' and ratio > 4 else 85
            try:
                enhanced = ai_x4(rgb, options.model, device, options.tile, event, progress,
                                 temporary, 5, first_high)
            except RuntimeError as exc:
                if 'out of memory' not in str(exc).lower() or options.tile <= 64:
                    raise
                progress(5, '記憶體不足，改用較小區塊重試…')
                enhanced = ai_x4(rgb, options.model, device, 64, event, progress, temporary, 5, first_high)
            ai_passes = 1
            if options.strategy == 'detail' and ratio > 4:
                check_cancel(event)
                second_scale = min(ratio / 4, 4)
                second_input = enhanced.resize((max(1, round(rgb.width * second_scale)),
                                               max(1, round(rgb.height * second_scale))), Image.Resampling.LANCZOS)
                enhanced.close()
                enhanced = ai_x4(second_input, options.model, device, options.tile, event,
                                 progress, temporary, 45, 85)
                ai_passes = 2
            rgb = enhanced
    else:
        progress(80, '正在以保真方式調整尺寸…')
    check_cancel(event)
    if alpha is not None:
        rgb.putalpha(alpha.resize(rgb.size, Image.Resampling.LANCZOS))
    progress(88, '正在調整成品尺寸與比例…')
    # Use the original aspect ratio even when a second AI pass rounded intermediate sizes.
    final = rgb.resize(expected, Image.Resampling.LANCZOS) if options.fit == 'image' else compose_image(rgb, target, options.fit)
    check_cancel(event)
    progress(94, '正在寫入圖片與印刷資訊…')
    save_output(final, destination, options, event)
    elapsed = time.monotonic() - started
    result = {'output': str(destination), 'pixels': list(final.size), 'ppi': options.ppi,
              'device': device, 'ai_passes': ai_passes, 'seconds': round(elapsed, 2),
              'bytes': destination.stat().st_size, 'source': meta, 'options': asdict(options),
              'size_cm': [round(px / options.ppi * 2.54, 3) for px in final.size],
              'target_bounds_pixels': list(target)}
    final.close()
    progress(100, '已完成 · 尺寸、PPI 與 ICC 已核對')
    return result


def preview_image(source, options, center=(0.5, 0.5), event=None, progress=None):
    event = event or threading.Event()
    progress = progress or (lambda *_: None)
    image, _ = load_image(Path(source))
    size = min(160, image.width, image.height)
    x = max(0, min(image.width - size, round(center[0] * image.width - size / 2)))
    y = max(0, min(image.height - size, round(center[1] * image.height - size / 2)))
    crop = image.crop((x, y, x + size, y + size))
    device = device_name(options.device) if options.model != 'faithful' else 'cpu'
    if options.model == 'faithful':
        result = crop.resize((size * 4, size * 4), Image.Resampling.LANCZOS)
    else:
        with tempfile.TemporaryDirectory(prefix='image-upscale-preview-') as temporary:
            result = ai_x4(crop, options.model, device, options.tile, event, progress, temporary, 5, 95)
        if crop.mode == 'RGBA':
            result.putalpha(crop.getchannel('A').resize(result.size, Image.Resampling.LANCZOS))
    check_cancel(event)
    progress(100, '局部 AI 預覽完成 · 拖動比較線查看差異')
    return crop.resize(result.size, Image.Resampling.LANCZOS), result
