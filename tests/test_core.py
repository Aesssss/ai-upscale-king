"""Print geometry, transparency, colour metadata and safe output regression checks."""
import io
import tempfile
import threading
import unittest
import struct
import zlib
from pathlib import Path
from unittest.mock import patch

import numpy as np
from PIL import Image
from app.core import (Cancelled, Options, compose_image, load_image,
                      print_pixels, process_image, save_output, srgb_profile, output_geometry)


class PrintTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / 'original.png'
        self.image = Image.new('RGBA', (30, 20), (180, 90, 20, 128))
        self.image.save(self.source, icc_profile=srgb_profile())

    def tearDown(self):
        self.temp.cleanup()

    def test_a1_and_bleed_are_at_least_requested_ppi(self):
        self.assertEqual(print_pixels(594, 841, 300), (7016, 9934))
        self.assertEqual(print_pixels(841, 594, 300), (9934, 7016))
        self.assertEqual(Options(bleed_mm=3).pixels, (7087, 10004))
        for mm, px in zip((594, 841), Options().pixels):
            self.assertGreaterEqual(px / (mm / 25.4), 300)
        with self.assertRaises(ValueError):
            print_pixels(0, 841, 300)

    def test_contain_preserves_alpha_and_does_not_stretch(self):
        result = compose_image(self.image, (100, 100), 'contain')
        self.assertEqual(result.size, (100, 100))
        self.assertEqual(result.getpixel((50, 50))[3], 128)
        self.assertEqual(result.getpixel((50, 0))[3], 0)
        result = compose_image(self.image.convert('RGB'), (100, 100), 'contain')
        self.assertEqual(result.getpixel((50, 0)), (255, 255, 255))
        self.assertEqual(compose_image(self.image, (100, 100), 'cover').size, (100, 100))
        self.assertEqual(compose_image(self.image, (100, 100), 'image').size, (100, 67))

    def test_png_tiff_and_jpeg_metadata_and_alpha(self):
        for fmt in ('png', 'tiff', 'jpeg'):
            destination = self.root / ('output.' + fmt)
            save_output(self.image, destination, Options(format=fmt), threading.Event())
            with Image.open(destination) as output:
                output.load()
                self.assertEqual(output.size, self.image.size)
                self.assertTrue(output.info.get('icc_profile'))
                self.assertAlmostEqual(output.info['dpi'][0], 300, delta=0.02)
                self.assertEqual(output.mode, 'RGB' if fmt == 'jpeg' else 'RGBA')
                if fmt != 'jpeg':
                    self.assertEqual(output.getpixel((0, 0))[3], 128)
                else:
                    self.assertGreater(output.getpixel((0, 0))[0], 180)

    def test_exif_orientation_and_unsupported_precision(self):
        exif = Image.Exif(); exif[274] = 6
        oriented = self.root / 'oriented.jpg'
        self.image.convert('RGB').save(oriented, exif=exif)
        self.assertEqual(load_image(oriented)[0].size, (20, 30))
        sixteen = self.root / '16bit.tiff'
        Image.fromarray(np.ones((8, 8), dtype=np.uint16) * 65535).save(sixteen)
        with self.assertRaisesRegex(ValueError, '8-bit'):
            load_image(sixteen)
        def chunk(kind, data):
            return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
        rgb16 = self.root / '16bit_rgb.png'
        rgb16.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 2, 2, 16, 2, 0, 0, 0)) +
            chunk(b'IDAT', zlib.compress((b'\x00' + b'\xff\xff' * 6) * 2)) + chunk(b'IEND', b''))
        with self.assertRaisesRegex(ValueError, '8-bit'):
            load_image(rgb16)
        multi = self.root / 'multi.tiff'
        self.image.save(multi, save_all=True, append_images=[self.image])
        with self.assertRaisesRegex(ValueError, '單張'):
            load_image(multi)
        cmyk = self.root / 'cmyk.jpg'; self.image.convert('CMYK').save(cmyk)
        with self.assertRaisesRegex(ValueError, 'ICC'):
            load_image(cmyk)

    def test_source_and_existing_destination_survive_cancel(self):
        original = self.source.read_bytes()
        with self.assertRaises(ValueError):
            process_image(self.source, self.source, Options(model='faithful'))
        self.assertEqual(self.source.read_bytes(), original)
        event = threading.Event(); event.set()
        destination = self.root / 'existing.png'; destination.write_bytes(b'existing')
        with self.assertRaises(Cancelled):
            save_output(self.image, destination, Options(), event)
        self.assertEqual(destination.read_bytes(), b'existing')
        self.assertFalse(list(self.root.glob('*.part')))

    def test_offline_pipeline_and_pixel_budget(self):
        destination = self.root / 'local.png'
        with patch('socket.socket.connect', side_effect=AssertionError('Network forbidden')):
            result = process_image(self.source, destination,
                Options(width_mm=25.4, height_mm=25.4, ppi=100, model='faithful'))
        self.assertEqual(result['pixels'], [100, 67])
        self.assertEqual(result['ai_passes'], 0)
        with self.assertRaisesRegex(ValueError, '像素上限'):
            process_image(self.source, destination, Options(ppi=600))

    def test_banner_and_custom_dimensions_preserve_source_aspect(self):
        target, actual, _ = output_geometry((900, 300), Options())
        self.assertEqual(target, (9934, 7016))
        self.assertEqual(actual, (9934, 3311))
        self.assertLessEqual(abs(actual[0] * 300 - actual[1] * 900), 900)
        self.assertEqual(output_geometry((300, 900), Options())[1], (3311, 9934))
        custom = Options(width_mm=400, height_mm=600)
        self.assertEqual(output_geometry((600, 400), custom)[1], (7087, 4725))
        self.assertEqual(output_geometry((400, 600), custom)[1], (4725, 7087))
        self.assertEqual(output_geometry((900, 300), custom)[1], (7087, 2362))
        # Explicit paper-canvas modes remain available; default has neither padding nor crop.
        self.assertEqual(output_geometry((900, 300), Options(fit='contain'))[1], (9934, 7016))
        self.assertEqual(output_geometry((900, 300), Options(fit='cover'))[1], (9934, 7016))

    def test_actual_export_keeps_banner_corners_and_orientation(self):
        image = Image.new('RGB', (90, 30), '#447755')
        for box, color in [((0, 0, 12, 12), 'red'), ((78, 0, 90, 12), 'blue'),
                           ((0, 18, 12, 30), 'yellow'), ((78, 18, 90, 30), 'white')]:
            image.paste(color, box)
        image.save(self.source)
        destination = self.root / 'banner.png'
        result = process_image(self.source, destination, Options(width_mm=25.4, height_mm=50.8, ppi=100, model='faithful'))
        self.assertEqual(result['pixels'], [200, 67])
        with Image.open(destination) as output:
            self.assertEqual([output.getpixel(p) for p in [(0,0),(199,0),(0,66),(199,66)]],
                             [(255,0,0),(0,0,255),(255,255,0),(255,255,255)])
            self.assertAlmostEqual(output.info['dpi'][0], 100, delta=.02)

    def test_exif_orientation_applies_before_output_bounds(self):
        exif = Image.Exif(); exif[274] = 6
        oriented = self.root / 'turned.jpg'; Image.new('RGB', (90,30)).save(oriented, exif=exif)
        result = process_image(oriented, self.root / 'turned.png', Options(width_mm=25.4,height_mm=50.8,ppi=100,model='faithful'))
        self.assertEqual(result['pixels'], [67, 200])


if __name__ == '__main__':
    unittest.main()
