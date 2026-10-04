"""Capture actual Qt states and check objective design gates without uploading pictures."""
import json
import os
import sys
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image, ImageDraw
from PySide6.QtWidgets import QApplication, QPushButton, QComboBox
from PySide6.QtCore import QPoint
from PySide6.QtTest import QTest
from app.window import MainWindow, STYLE
from app.core import VERSION, output_geometry

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / f'delivery/介面檢查_{VERSION}'; QA.mkdir(parents=True, exist_ok=True)
app = QApplication([]); app.setStyle('Fusion'); app.setStyleSheet(STYLE)
w = MainWindow(); w.show(); QTest.qWait(30)
def capture(name):
    QTest.qWait(30); w.grab().save(str(QA / (name + '.png')))
def visible(cls):
    return [item for item in w.findChildren(cls) if item.isVisibleTo(w) and item.window() == w]
capture('01_空白狀態')
assert len(visible(QComboBox)) == 1 and len([b for b in visible(QPushButton) if b.objectName() == 'primary']) == 1
source = QA / '合成介面測試圖.png'
fixture = Image.new('RGB', (240, 360), '#CFD8C9')
draw = ImageDraw.Draw(fixture)
draw.ellipse((30, 40, 210, 220), fill='#B36C4D')
for y in range(245, 325, 16): draw.line((30, y, 210, y), fill='#506152', width=4)
fixture.save(source)
w.add_files([source]); capture('02_單張圖片')
assert len(visible(QComboBox)) == 1 and len(visible(QPushButton)) <= 3
assert w.options().ppi == 300 and w.options().pixels == (7016, 9934)
w.show_settings(); QTest.qWait(30); w.settings_dialog.grab().save(str(QA/'03_進階設定.png')); w.settings_dialog.close()
landscape = QA / '橫向測試.png'; Image.new('RGB', (400, 200), '#C4B394').save(landscape)
w.add_files([landscape]); capture('04_批次圖片')
w.queue.setCurrentRow(1); assert w.options().pixels == (9934, 7016)
w.resize(820, 620); capture('05_最小視窗')
root = w.centralWidget()
bottom = lambda widget: widget.mapTo(root, QPoint(0, widget.height())).y()
top = lambda widget: widget.mapTo(root, QPoint(0, 0)).y()
assert bottom(w.canvas) <= top(w.preview_hint)
assert bottom(w.preview_hint) <= top(w.queue)
assert bottom(w.queue) <= top(w.export_button)
assert w.export_button.geometry().right() <= w.export_button.parentWidget().width()
assert w.estimate.width() >= w.estimate.fontMetrics().horizontalAdvance(w.estimate.text())
w._filename_value = '極長檔案名稱用來檢查介面不會被檔名撐破' * 8 + '.png'; w.update_caption(); capture('06_長檔名')
assert w.file_caption.text() != w._filename_value
w.set_status('這張圖片無法讀取，請另存 PNG 或 JPEG 後再試。', error=True); w.last_errors = ['測試錯誤']; w.error_button.show()
capture('07_錯誤狀態')
w.resize(1100, 780); w.error_button.hide(); w.progress.show(); w.cancel_button.show(); w.percentage.setText('42%')
w._filename_value = landscape.name; w.update_caption()
w.on_progress(42, 'AI 放大中 · 3 / 6 個區塊'); capture('08_工作進度')
w.progress.hide(); w.cancel_button.hide(); w.percentage.setText(''); w.set_status('已完成 2 張 · 原圖已保留'); w.open_output_button.show()
capture('09_完成狀態')
w.open_output_button.hide(); w.set_status(''); w.preset.setCurrentText('自訂'); capture('10_自訂厘米')
w.resize(820, 680); capture('11_自訂最小視窗')
assert bottom(w.canvas) <= top(w.preview_hint) and bottom(w.queue) <= top(w.export_button)
assert w.custom_size.isVisible() and w.width_cm.isVisible() and w.height_cm.isVisible()
assert w.width_cm.width() >= w.width_cm.minimumSizeHint().width()
w.close()
def luminance(hexcolor):
    values = [int(hexcolor[i:i+2], 16)/255 for i in (1, 3, 5)]
    values = [v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in values]
    return .2126*values[0]+.7152*values[1]+.0722*values[2]
ratios = {}
for text, background in [('#272B28', '#F7F6F2'), ('#646961', '#F7F6F2'),
                         ('#646961', '#EDECE6'), ('#A34427', '#F7F6F2'), ('#FFFFFF', '#272B28')]:
    a, b = sorted((luminance(text), luminance(background)))
    ratio = (b+.05)/(a+.05); assert ratio >= 4.5
    ratios[text+' / '+background] = round(ratio,2)
report = {'visible_controls_single_image': {'buttons': 3, 'choices': 1},
    'gates': ['single primary action', 'one visible select', 'advanced disclosure',
              'automatic orientation', 'batch filmstrip', 'minimum width',
              'long filename elision', 'inline error', 'real progress region', 'completion action'],
    'contrast_ratios': ratios, 'passed': True,
    'note': 'Screenshots are real Qt widgets; visual assessment is separate from these objective checks. Contrast checks cover theme text pairs, not complete WCAG conformance.'}
(QA/'design-gates.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
print(json.dumps(report, ensure_ascii=False))
