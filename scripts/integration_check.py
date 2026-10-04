"""Real inference checks. Uses local fixture; prohibits outbound socket connections."""
import json
import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from PIL import Image, ImageDraw
from app.core import Options, ai_x4, device_name, process_image, srgb_profile

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / 'delivery' / '驗證記錄'; QA.mkdir(parents=True, exist_ok=True)


def fixture():
    w, h = 192, 272
    y, x = np.mgrid[:h, :w]
    rgb = np.stack([80 + 110 * x / w, 50 + 150 * y / h,
                    120 + 35 * np.sin(x / 8) * np.cos(y / 12)], axis=-1).astype('uint8')
    image = Image.fromarray(rgb).convert('RGBA')
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((22, 35, 172, 226), 23, fill=(244, 233, 255, 255), outline=(54, 24, 99, 255), width=3)
    draw.ellipse((44, 70, 142, 168), fill=(129, 92, 245, 255))
    draw.ellipse((68, 94, 83, 110), fill=(255, 255, 255, 255))
    draw.ellipse((106, 94, 121, 110), fill=(255, 255, 255, 255))
    draw.arc((70, 115, 120, 145), 0, 180, fill=(255, 255, 255, 255), width=3)
    for i in range(12):
        draw.line((42 + i * 9, 184, 42 + i * 9, 208), fill=(45, 24, 69, 255), width=1 + i % 3)
    draw.rectangle((0, 0, 17, h), fill=(0, 0, 0, 0))
    source = QA / '本地測試圖.png'; image.save(source, icc_profile=srgb_profile())
    return source, image


def main():
    source, image = fixture(); report = {'device': device_name(), 'checks': []}
    assert report['device'] == 'mps', 'This Mac acceptance run must use its GPU.'
    event = threading.Event()
    with patch('socket.socket.connect', side_effect=AssertionError('Network forbidden')):
        for kind in ('anime', 'photo'):
            small = image.convert('RGB').resize((48, 64))
            with tempfile.TemporaryDirectory() as temporary:
                start = time.monotonic()
                full = ai_x4(small, kind, 'mps', 128, event, lambda *_: None, temporary)
                tiled = ai_x4(small, kind, 'mps', 32, event, lambda *_: None, temporary)
            baseline = small.resize(full.size, Image.Resampling.LANCZOS)
            diff = float(np.abs(np.asarray(full, dtype=float) - np.asarray(baseline, dtype=float)).mean())
            seam = float(np.abs(np.asarray(full, dtype=float) - np.asarray(tiled, dtype=float)).mean())
            assert full.size == (192, 256) and diff > 0.1 and seam < 5
            tiled.save(QA / f'{kind}_AI4x.png')
            report['checks'].append({'model': kind, 'seconds': round(time.monotonic() - start, 2),
                'AI_vs_Lanczos_mean_difference': diff, 'tiled_vs_full_mean_difference': seam})
        for fmt in ('png', 'tiff'):
            result = process_image(source, QA / f'A1_300PPI.{fmt}', Options(model='anime', format=fmt),
                progress=lambda p, s: print(f'{fmt} {p}% {s}', flush=True))
            assert result['pixels'] == [7016, 9934] and result['ai_passes'] == 1
            with Image.open(result['output']) as output:
                output.load()
                assert output.mode == 'RGBA' and output.info.get('icc_profile')
                assert output.getpixel((0, 0))[3] == 0
                assert abs(output.info['dpi'][0] - 300) < 0.1
            report['checks'].append(result)
        # The second pass must actually run and cancellation must stop before writing.
        detail = process_image(source, QA / '精細模式.png',
            Options(width_mm=100, height_mm=140, ppi=300, model='anime', strategy='detail'))
        assert detail['ai_passes'] == 2
        report['checks'].append(detail)
    report['outbound_network'] = 'socket.connect prohibited during all inference and exports'
    (QA / 'integration-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
