"""Qt acceptance for the simplified interface; no image uploads or external services."""
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image, ImageDraw
from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QPushButton, QComboBox
from PySide6.QtTest import QTest
from app.window import MainWindow, STYLE, Worker
from app.core import VERSION, output_geometry

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / f'delivery/介面檢查_{VERSION}'; QA.mkdir(parents=True, exist_ok=True)
source = QA / '直向操作測試.png'; landscape = QA / '橫向操作測試.png'
im = Image.new('RGBA', (80, 160), (0, 0, 0, 0)); draw = ImageDraw.Draw(im)
draw.rectangle((10, 10, 70, 140), fill='#A34427'); im.save(source)
Image.new('RGB', (160, 80), '#C4B394').save(landscape)
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
application = QApplication([]); application.setStyle('Fusion'); application.setStyleSheet(STYLE)
w = MainWindow(); w.show(); w.activateWindow(); QTest.qWait(50)
visible = lambda cls: [item for item in w.findChildren(cls) if item.isVisibleTo(w) and item.window() == w]
assert w.preset.currentText() == 'A1' and w.options().pixels == (7016, 9934)
assert len(visible(QComboBox)) == 1 and len(visible(QPushButton)) == 2
assert not w.settings_dialog.isVisible()
# One main paper choice; infrequent controls stay in the actual dialog.
QTest.mouseClick(w.advanced_button, Qt.MouseButton.LeftButton); QTest.qWait(30)
assert w.settings_dialog.isVisible()
QTest.mouseClick(w.model, Qt.MouseButton.LeftButton)
QTest.keyClick(w.model, Qt.Key.Key_Down); QTest.keyClick(w.model, Qt.Key.Key_Return); QTest.qWait(30)
assert w.model.currentData() == 'anime' and w.settings_dialog.isVisible()
w.model.setCurrentIndex(0)
w.orientation.setCurrentIndex(2); assert w.options().pixels == (9934, 7016)
w.orientation.setCurrentIndex(0); w.bleed.setValue(3); assert w.options().pixels == (7087, 10004)
w.bleed.setValue(0); w.settings_dialog.close(); w.activateWindow()
with patch.object(QFileDialog, 'getOpenFileNames', return_value=([str(source)], '')):
    QTest.mouseClick(w.add_button, Qt.MouseButton.LeftButton)
w.add_files([str(source.resolve()), os.path.relpath(source, ROOT)])
assert w.queue.count() == 1 and w.image is not None
assert len(visible(QPushButton)) == 3 and len(visible(QComboBox)) == 1
banner = QA / 'banner操作測試.png'; Image.new('RGB', (90, 30), '#447755').save(banner)
w.add_files([banner]); w.queue.setCurrentRow(1); QTest.qWait(30)
assert w.fit.currentData() == 'image' and output_geometry(w.image.size, w.options())[1] == (9934, 3311)
assert '9,934 × 3,311' in w.estimate.text()
w.preset.setCurrentText('自訂'); QTest.qWait(30)
assert w.custom_size.isVisible() and w.width_cm.value() == 40 and w.height_cm.value() == 60
w.preset.setFocus(); QTest.keyClick(w.preset, Qt.Key.Key_Tab); assert application.focusWidget() == w.width_cm
QTest.keyClick(w.width_cm, Qt.Key.Key_Tab); assert application.focusWidget() == w.height_cm
QTest.keyClick(w.height_cm, Qt.Key.Key_Tab); assert application.focusWidget() == w.advanced_button
assert output_geometry(w.image.size, w.options())[1] == (7087, 2362)
w.remove_selected(); w.preset.setCurrentText('A1')
w.model.setCurrentIndex(2)
def wait():
    deadline = time.monotonic() + 90
    while w.busy and time.monotonic() < deadline: QTest.qWait(25)
    assert not w.busy, 'Worker did not finish within 90 seconds'
    QTest.qWait(30)
# Double click is a real widget event, not a simulated completion.
QTest.qWait(30); QTest.mouseDClick(w.canvas, Qt.MouseButton.LeftButton, pos=w.canvas.image_rect.center().toPoint())
wait(); assert w.canvas.result is not None and '保真縮放' in w.preview_hint.text() and 'AI 4×' not in w.preview_hint.text()
w.canvas.setFocus(); QTest.keyClick(w.canvas, Qt.Key.Key_Right); assert abs(w.canvas.split - .55) < .001
QTest.keyClick(w.canvas, Qt.Key.Key_Escape); QTest.qWait(30); assert w.canvas.result is None
QTest.keyClick(w.canvas, Qt.Key.Key_P); wait(); assert w.canvas.result is not None
QTest.keyClick(w.canvas, Qt.Key.Key_Escape); QTest.qWait(30)
# Keyboard focus remains visible and every main choice can be reached.
w.preset.setFocus(); QTest.keyClick(w.preset, Qt.Key.Key_Tab); assert application.focusWidget() == w.advanced_button
QTest.keyClick(w.advanced_button, Qt.Key.Key_Tab); assert application.focusWidget() == w.export_button
w.preset.setCurrentText('自訂'); w.width_cm.setValue(2.54); w.height_cm.setValue(5.08); w.ppi.setValue(100)
output = QA / '單張介面匯出.png'
with patch.object(QFileDialog, 'getSaveFileName', return_value=(str(output), '')):
    QTest.mouseClick(w.export_button, Qt.MouseButton.LeftButton); wait()
assert output.is_file() and w.last_output == output
with Image.open(output) as result:
    assert result.size == (100, 200) and result.mode == 'RGBA'
    assert result.info.get('icc_profile') and abs(result.info['dpi'][0] - 100) < .02
    assert result.getpixel((0, 0))[3] == 0
# Mixed orientation batches adapt per image and isolate unreadable inputs.
bad = QA / '損壞操作測試.png'; bad.write_bytes(b'Not an image')
w.add_files([landscape, bad]); w.queue.setCurrentRow(1); QTest.qWait(30)
assert output_geometry(w.image.size, w.options())[1] == (200, 100)
batch = QA / '批次操作輸出'; batch.mkdir(exist_ok=True)
with patch.object(QFileDialog, 'getExistingDirectory', return_value=str(batch)), patch.object(QMessageBox, 'information') as alert:
    w.start_export(); wait(); assert not alert.called
assert len(w.last_errors) == 1 and w.error_button.isVisible() and '2 張' in w.status.text()
assert '完成 ✓' in w.queue.item(0).text() and '完成 ✓' in w.queue.item(1).text() and '失敗' in w.queue.item(2).text()
for name, expected in [('直向操作測試', (100, 200)), ('橫向操作測試', (200, 100))]:
    outputs = list(batch.glob(name + '_*.png')); assert outputs
    for file in outputs:
        with Image.open(file) as result: assert result.size == expected
with patch.object(QMessageBox, 'information') as alert:
    QTest.mouseClick(w.error_button, Qt.MouseButton.LeftButton); assert alert.called
# Cancelled jobs restore controls; cancellation remains available on the next job.
for number in (1, 2):
    destination = QA / f'取消不應產生{number}.png'
    worker = Worker([(source, destination)], w.options()); worker.cancel_event.set()
    w.start_worker(worker); assert w.cancel_button.isEnabled(); w.cancel_work(); wait()
    assert not destination.exists() and w.export_button.isEnabled() and not w.cancel_button.isVisible()
# Remove only a queue item; the source on disk remains intact.
w.queue.setCurrentRow(2); w.canvas.setFocus(); QTest.keyClick(w.canvas, Qt.Key.Key_Delete); QTest.qWait(30)
assert w.queue.count() == 2 and bad.is_file()
assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
w.close()
report = {'passed': True, 'checks': ['single main paper choice / progressive disclosure',
    'dropdown keyboard selection keeps settings open',
    'A1 banner retains 3:1 aspect / no paper canvas', 'custom cm inputs visible on main screen', 'canonical input deduplication', 'double-click and P preview / Escape full image',
    'honest faithful preview caption', 'keyboard comparison / focus chain / queue removal',
    'single export alpha / ICC / PPI', 'mixed-orientation batch / per-file failure isolation',
    'inline errors without automatic dialogs', 'cancel / restart', 'source unchanged']}
(QA / 'ui-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
print(json.dumps(report, ensure_ascii=False))
