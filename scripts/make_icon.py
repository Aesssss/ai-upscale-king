"""Local vector-style paper / expansion mark matching the desktop interface."""
from pathlib import Path
from PIL import Image, ImageDraw
root = Path(__file__).resolve().parents[1] / 'resources'
image = Image.new('RGBA', (1024, 1024)); draw = ImageDraw.Draw(image)
draw.rounded_rectangle((35, 35, 989, 989), radius=214, fill='#272B28')
draw.rounded_rectangle((219, 326, 696, 828), radius=23, fill='#191E1A')
draw.rounded_rectangle((204, 311, 681, 813), radius=23, fill='#F7F6F2')
draw.rectangle((255, 397, 629, 759), fill='#E9E2D3')
for offset in range(9):
    yy = 735 - offset * 35
    draw.line([(255, yy), (335, yy-30), (415, yy-32), (500, yy-10), (570, yy+1), (629, yy-10)],
              fill='#A34427' if offset % 3 == 0 else '#BBAE95', width=4, joint='curve')
draw.line([(536, 472), (810, 198)], fill='#272B28', width=112)
draw.line([(536, 472), (810, 198)], fill='#CF7556', width=48)
draw.line([(644, 198), (810, 198), (810, 364)], fill='#CF7556', width=48, joint='curve')
iconset = root / 'AppIcon.iconset'; iconset.mkdir(exist_ok=True)
for size in (16, 32, 128, 256, 512):
    for scale in (1, 2):
        suffix = '@2x' if scale == 2 else ''
        image.resize((size * scale, size * scale), Image.Resampling.LANCZOS).save(iconset / f'icon_{size}x{size}{suffix}.png')
image.save(root / 'AppIcon.png'); image.save(root / 'AppIcon.icns')
image.save(root / 'AppIcon.ico', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
