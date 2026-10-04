from __future__ import annotations

import threading
import sys
from pathlib import Path

from PIL import Image
from PySide6.QtCore import Qt, QThread, Signal, QUrl, QSize
from PySide6.QtGui import QAction, QKeySequence, QDesktopServices, QIcon
from PySide6.QtWidgets import (QMainWindow, QWidget, QFrame, QPushButton, QVBoxLayout,
    QHBoxLayout, QComboBox, QFileDialog, QMessageBox, QProgressBar, QListWidget,
    QListWidgetItem, QMenu, QListView, QAbstractItemView, QSizePolicy, QDoubleSpinBox)
from app.design import STYLE, label, pixmap, ImageCanvas, PrintMark, PaperSelector
from app.settings import AdvancedSettings
from app.core import (APP_NAME, VERSION, PRESETS, SUPPORTED, MAX_OUTPUT_PIXELS,
    Options, Cancelled, output_geometry, load_image, device_name, process_image, preview_image)


class Worker(QThread):
    progress = Signal(int, str)
    result = Signal(object)
    preview = Signal(object, object)
    failure = Signal(str)
    itemStarted = Signal(int)
    itemDone = Signal(int, object)

    def __init__(self, jobs, options, preview_center=None):
        super().__init__()
        self.jobs, self.options = jobs, options
        self.preview_center = preview_center
        self.cancel_event = threading.Event()

    def run(self):
        try:
            if self.preview_center is not None:
                a, b = preview_image(self.jobs[0][0], self.options, self.preview_center,
                                     self.cancel_event, self.progress.emit)
                self.preview.emit(a, b)
            else:
                done, errors = [], []
                for index, (source, dest) in enumerate(self.jobs):
                    if self.cancel_event.is_set():
                        raise Cancelled()
                    self.itemStarted.emit(index)
                    def update(value, message, index=index):
                        self.progress.emit(round((index * 100 + value) / len(self.jobs)),
                                           f'{index + 1}/{len(self.jobs)} · {message}')
                    try:
                        result = process_image(source, dest, self.options, self.cancel_event, update)
                    except Cancelled:
                        raise
                    except Exception as exc:
                        result = {'error': str(exc)}
                        errors.append(f'{Path(source).name}：{exc}')
                    else:
                        done.append(result)
                    self.itemDone.emit(index, result)
                self.result.emit({'done': done, 'errors': errors})
        except Cancelled:
            self.failure.emit('工作已取消；已完成的輸出與原圖均保留。')
        except Exception as exc:
            self.failure.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        platform = 'macOS' if sys.platform == 'darwin' else 'Windows' if sys.platform == 'win32' else '桌面'
        self.setWindowTitle(f'{APP_NAME} · {platform} {VERSION}')
        self.resize(1100, 780)
        self.setMinimumSize(820, 620)
        self.files = []
        self.image = None
        self.worker = None
        self.last_output = None
        self.active_jobs = []
        self.preview_center = (0.5, 0.5)
        self.busy = False
        self.last_errors = []
        self._filename_value = ''
        self.device = device_name()
        self.build_ui()
        self.build_menu()
        self.update_estimate()

    def build_ui(self):
        root = QWidget(); root.setObjectName('root'); self.setCentralWidget(root)
        outer = QVBoxLayout(root); outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(0)
        header = QHBoxLayout(); header.setContentsMargins(30, 18, 32, 12); header.setSpacing(12)
        header.addWidget(PrintMark())
        brand = QVBoxLayout(); brand.setSpacing(2)
        brand.addWidget(label(APP_NAME, 'brand')); brand.addWidget(label('AI Upscale King', 'eyebrow'))
        header.addLayout(brand); header.addStretch(); header.addWidget(label('圖片在本機處理', 'muted'))
        outer.addLayout(header)
        body = QVBoxLayout(); body.setContentsMargins(32, 7, 32, 20); body.setSpacing(12)
        outer.addLayout(body, 1)
        self.toolbar = QWidget(); toolbar_layout = QHBoxLayout(self.toolbar); toolbar_layout.setContentsMargins(0, 0, 0, 0)
        self.file_caption = label('', 'filename'); self.file_caption.setMinimumWidth(0)
        self.file_caption.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        toolbar_layout.addWidget(self.file_caption, 1)
        self.queue_title = label('', 'source'); toolbar_layout.addWidget(self.queue_title)
        self.more_button = QPushButton('⋯'); self.more_button.setObjectName('overflow')
        self.more_button.setAccessibleName('更多圖片操作'); self.more_button.setToolTip('加入圖片、比較細節、移出佇列')
        self.more_menu = QMenu(self)
        self.add_action = self.more_menu.addAction('加入圖片…', self.choose_files)
        self.preview_action = self.more_menu.addAction('比較 AI 細節', self.start_preview)
        self.full_action = self.more_menu.addAction('返回全圖', self.show_full)
        self.more_menu.addSeparator()
        self.output_action = self.more_menu.addAction('顯示輸出檔案', self.open_output)
        self.remove_action = self.more_menu.addAction('移出這張圖片', self.remove_selected)
        self.more_button.setMenu(self.more_menu); toolbar_layout.addWidget(self.more_button)
        body.addWidget(self.toolbar); self.toolbar.hide()
        self.canvas = ImageCanvas(); self.canvas.filesDropped.connect(self.add_files)
        self.canvas.browseRequested.connect(self.choose_files); self.canvas.centerPicked.connect(self.set_preview_center)
        self.canvas.previewRequested.connect(self.start_preview)
        body.addWidget(self.canvas, 1); self.add_button = self.canvas.empty_button
        self.preview_hint = label('', 'muted'); self.preview_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body.addWidget(self.preview_hint); self.preview_hint.hide()
        self.queue = QListWidget(); self.queue.setViewMode(QListView.ViewMode.IconMode)
        self.queue.setFlow(QListView.Flow.LeftToRight); self.queue.setWrapping(False)
        self.queue.setMovement(QListView.Movement.Static); self.queue.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.queue.setIconSize(QSize(40, 40)); self.queue.setGridSize(QSize(152, 72)); self.queue.setWordWrap(False)
        self.queue.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        self.queue.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.queue.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.queue.setFixedHeight(78); self.queue.setAccessibleName('批次圖片，左右鍵切換，Delete 移出佇列')
        self.queue.currentRowChanged.connect(self.select_file); body.addWidget(self.queue); self.queue.hide()
        rail = QFrame(); rail.setObjectName('rail'); row = QHBoxLayout(rail)
        row.setContentsMargins(34, 20, 32, 20); row.setSpacing(12)
        size = QVBoxLayout(); size.setSpacing(2); size.addWidget(label('印刷尺寸', 'eyebrow'))
        self.preset = PaperSelector(); self.preset.setObjectName('paperPreset'); self.preset.addItems(list(PRESETS))
        self.preset.setFixedWidth(98); self.preset.setAccessibleName('印刷尺寸'); size.addWidget(self.preset); row.addLayout(size)
        spec = QVBoxLayout(); spec.setSpacing(5)
        self.custom_size = QWidget(); custom_row = QHBoxLayout(self.custom_size)
        custom_row.setContentsMargins(0, 0, 0, 0); custom_row.setSpacing(6)
        self.width_cm = QDoubleSpinBox(); self.height_cm = QDoubleSpinBox()
        for spin, name, value in [(self.width_cm, '自訂第一邊長（厘米）', 40), (self.height_cm, '自訂第二邊長（厘米）', 60)]:
            spin.setRange(.1, 199); spin.setDecimals(2); spin.setValue(value); spin.setFixedWidth(110)
            spin.setAccessibleName(name); spin.setKeyboardTracking(False)
        custom_row.addWidget(self.width_cm); custom_row.addWidget(label('×', 'muted'))
        custom_row.addWidget(self.height_cm); custom_row.addWidget(label('cm', 'muted')); custom_row.addStretch()
        spec.addWidget(self.custom_size); self.custom_size.hide()
        self.paper_dimensions = label('', 'estimate'); self.estimate = label('', 'source')
        self.paper_dimensions.setWordWrap(True); self.estimate.setWordWrap(True)
        spec.addWidget(self.paper_dimensions); spec.addWidget(self.estimate); row.addLayout(spec, 1)
        self.advanced_button = QPushButton('進階設定'); self.advanced_button.setObjectName('textAction')
        self.advanced_button.clicked.connect(self.show_settings); row.addWidget(self.advanced_button)
        self.export_button = QPushButton('放大至 A1'); self.export_button.setObjectName('primary')
        self.export_button.setMinimumWidth(183); self.export_button.clicked.connect(self.start_export); row.addWidget(self.export_button)
        outer.addWidget(rail)
        self.settings_dialog = AdvancedSettings(self)
        self.hardware = label('Apple GPU 加速' if self.device == 'mps' else 'GPU 加速' if self.device == 'cuda' else 'CPU 本地運算', 'muted')
        self.settings_dialog.layout().insertWidget(2, self.hardware)
        self.preset.currentTextChanged.connect(self.apply_preset); self.orientation.currentIndexChanged.connect(self.apply_preset)
        for control in self.controls:
            if isinstance(control, QComboBox): control.currentIndexChanged.connect(self.update_estimate)
            else: control.valueChanged.connect(self.update_estimate)
        status_row = QHBoxLayout(); status_row.setContentsMargins(34, 0, 32, 12); status_row.setSpacing(6)
        self.status = label('', 'status', True); self.status.setMinimumHeight(20); status_row.addWidget(self.status, 1)
        self.percentage = label('', 'percentage'); status_row.addWidget(self.percentage)
        self.error_button = QPushButton('查看原因'); self.error_button.setObjectName('textAction')
        self.error_button.clicked.connect(self.show_errors); self.error_button.hide(); status_row.addWidget(self.error_button)
        self.open_output_button = QPushButton('查看檔案 ↗'); self.open_output_button.setObjectName('textAction')
        self.open_output_button.clicked.connect(self.open_output); self.open_output_button.hide(); status_row.addWidget(self.open_output_button)
        self.cancel_button = QPushButton('取消'); self.cancel_button.setObjectName('textAction')
        self.cancel_button.clicked.connect(self.cancel_work); self.cancel_button.hide(); status_row.addWidget(self.cancel_button)
        self.status_bar = QWidget(); self.status_bar.setLayout(status_row); self.status_bar.hide()
        outer.addWidget(self.status_bar)
        self.progress = QProgressBar(); self.progress.setRange(0, 100); self.progress.setValue(0)
        self.progress.setTextVisible(False); self.progress.hide(); outer.addWidget(self.progress)
        self.setTabOrder(self.add_button, self.preset); self.setTabOrder(self.preset, self.width_cm)
        self.setTabOrder(self.width_cm, self.height_cm); self.setTabOrder(self.height_cm, self.advanced_button)
        self.setTabOrder(self.advanced_button, self.export_button); self.setTabOrder(self.export_button, self.more_button)

    def build_menu(self):
        file_menu = self.menuBar().addMenu('檔案')
        action = QAction('加入圖片…', self); action.setShortcut(QKeySequence.StandardKey.Open); action.triggered.connect(self.choose_files); file_menu.addAction(action)
        export = QAction('放大並匯出…', self); export.setShortcut('Ctrl+Shift+S'); export.triggered.connect(self.start_export); file_menu.addAction(export)
        edit = self.menuBar().addMenu('圖片')
        action = QAction('比較 AI 細節', self); action.setShortcut('P'); action.triggered.connect(self.start_preview); edit.addAction(action)
        action = QAction('返回全圖', self); action.setShortcut('Escape'); action.triggered.connect(self.show_full); edit.addAction(action)
        action = QAction('移出佇列', self); action.setShortcuts(['Backspace', 'Delete']); action.triggered.connect(self.remove_selected); edit.addAction(action)
        action = QAction('進階設定…', self); action.setShortcut('Ctrl+,'); action.triggered.connect(self.show_settings); file_menu.addAction(action)
        about = QAction('關於 AI 圖片放大王', self); about.triggered.connect(self.show_about); self.menuBar().addAction(about)

    def options(self):
        custom = self.preset.currentText() == '自訂'
        width, height = (self.width_cm.value() * 10, self.height_cm.value() * 10) if custom else (self.width_mm.value(), self.height_mm.value())
        if custom and self.orientation.currentData() != 'auto':
            short, long = sorted((width, height))
            width, height = (long, short) if self.orientation.currentData() == 'landscape' else (short, long)
        return Options(width_mm=width, height_mm=height, ppi=self.ppi.value(),
                       auto_orientation=self.orientation.currentData() == 'auto',
                       bleed_mm=self.bleed.value(), fit=self.fit.currentData(), model=self.model.currentData(),
                       strategy=self.strategy.currentData(), format=self.output_format.currentData(), device=self.compute.currentData())

    def apply_preset(self, *_):
        if self.preset.currentText() != '自訂':
            width, height = PRESETS[self.preset.currentText()]
        else:
            width, height = self.width_cm.value() * 10, self.height_cm.value() * 10
        orientation = self.orientation.currentData()
        landscape = orientation == 'landscape' or (orientation == 'auto' and self.image is not None and self.image.width > self.image.height)
        small, large = sorted((width, height))
        self.width_mm.setValue(large if landscape else small); self.height_mm.setValue(small if landscape else large)
        self.custom_size.setVisible(self.preset.currentText() == '自訂')
        self.setMinimumHeight(680 if self.preset.currentText() == '自訂' else 620)
        self.width_mm.setEnabled(self.preset.currentText() == '自訂' and not self.busy)
        self.height_mm.setEnabled(self.preset.currentText() == '自訂' and not self.busy)
        self.update_estimate()

    def update_estimate(self, *_):
        opts = self.options()
        target, actual, ratio = output_geometry(self.image.size, opts) if self.image is not None else (opts.pixels, opts.pixels, 1)
        width, height = actual
        if self.image is not None:
            self.paper_dimensions.setText(f'成品 {width / opts.ppi * 2.54:.1f} × {height / opts.ppi * 2.54:.1f} cm')
        else:
            self.paper_dimensions.setText('保留原圖比例 · 方向跟隨圖片')
        self.estimate.setText(f'{width:,} × {height:,} px · {opts.ppi} DPI' if self.image is not None else f'尺寸範圍 {opts.width_mm / 10:g} × {opts.height_mm / 10:g} cm · {opts.ppi} DPI')
        self.paper_dimensions.setToolTip(f'目標範圍 {target[0]:,} × {target[1]:,} px；成品保持原圖比例，像素四捨五入。')
        over = width * height > MAX_OUTPUT_PIXELS
        if self.image is not None:
            if over:
                message = '超過本版 1.6 億像素上限；A1 請選 300 PPI 或較低。'
            elif opts.model == 'faithful':
                message = '保真縮放維持字形與圖案，不重建 AI 細節。'
            elif ratio > 4:
                message = f'約需 {ratio:.1f}× 放大。' + ('精細模式會再次重建細節，請先檢查局部預覽。' if opts.strategy == 'detail' else '標準模式做 AI 4×，其餘以高品質插值調整尺寸。')
            elif ratio <= 1:
                message = '原圖像素已足夠；按指定尺寸縮小，不需要 AI 放大。'
            else:
                message = f'約需 {ratio:.1f}× 放大；AI 4× 後精確調整至成品尺寸。'
            if opts.format == 'jpeg' and self.image.mode == 'RGBA':
                message += '\nJPEG 不支援透明，匯出時會使用白色背景。'
            self.quality_hint.setText(message)
        else:
            self.quality_hint.setText('A1：594 × 841 mm。出血會增加輸出總尺寸。')
        self.export_button.setEnabled(bool(self.files) and not self.busy and not over)
        self.export_button.setVisible(bool(self.files))
        action = (f'等比例放大 {len(self.files)} 張' if len(self.files) > 1 else '等比例放大') if self.preset.currentText() == '自訂' else (f'放大 {len(self.files)} 張至 {self.preset.currentText()}' if len(self.files) > 1 else f'放大至 {self.preset.currentText()}')
        self.export_button.setText('正在處理…' if self.busy else action)
        self.preview_action.setEnabled(self.image is not None and not self.busy)
        self.full_action.setEnabled(self.image is not None and not self.busy)
        self.remove_action.setEnabled(bool(self.files) and not self.busy)
        self.add_action.setEnabled(not self.busy); self.output_action.setEnabled(self.last_output is not None)
        self.advanced_button.setEnabled(not self.busy); self.more_button.setEnabled(not self.busy)
        self.toolbar.setVisible(bool(self.files)); self.queue.setVisible(len(self.files) > 1)
        self.preview_hint.setVisible(self.image is not None)
        if self.image is not None:
            self.queue_title.setText(f'{self.image.width:,} × {self.image.height:,} px' +
                (f' · {len(self.files)} 張' if len(self.files) > 1 else ''))
        self.width_mm.setEnabled(self.preset.currentText() == '自訂' and not self.busy)
        self.height_mm.setEnabled(self.preset.currentText() == '自訂' and not self.busy)
        if over and not self.busy:
            self.set_status('尺寸超過上限，請在進階設定降低解析度。', error=True)
        elif self.status.property('error') and self.status.text().startswith('尺寸超過'):
            self.set_status('')

    def choose_files(self):
        if self.busy:
            return
        names, _ = QFileDialog.getOpenFileNames(self, '加入要放大的圖片', '', '圖片 (*.png *.jpg *.jpeg *.tif *.tiff *.webp *.bmp)')
        self.add_files(names)

    def add_files(self, names):
        if self.busy:
            return
        for name in names:
            path = Path(name).expanduser().resolve()
            if path.is_file() and path.suffix.lower() in SUPPORTED and path not in self.files:
                self.files.append(path)
                item = QListWidgetItem(path.name); item.setToolTip(path.name)
                try:
                    with Image.open(path) as thumb:
                        thumb.thumbnail((80, 80)); item.setIcon(QIcon(pixmap(thumb)))
                except Exception:
                    pass
                self.queue.addItem(item)
        if self.files and self.queue.currentRow() < 0:
            self.queue.setCurrentRow(0)
        self.update_estimate()

    def select_file(self, row):
        if self.busy or row < 0 or row >= len(self.files):
            return
        try:
            self.image, meta = load_image(self.files[row])
        except Exception as exc:
            self.image = None; self.source_info.setText('來源無法讀取'); self.set_status(str(exc), error=True)
            self._filename_value = self.files[row].name; self.update_caption()
            self.canvas.set_images(None)
            self.update_estimate(); return
        self.preview_center = (0.5, 0.5); self.canvas.point = self.preview_center
        self.canvas.set_images(self.image)
        self.open_output_button.hide()
        self._filename_value = self.files[row].name; self.update_caption()
        self.queue_title.setText(f'{self.image.width:,} × {self.image.height:,} px' + (f' · {len(self.files)} 張' if len(self.files) > 1 else ''))
        self.source_info.setText(f'來源：{self.image.width:,} × {self.image.height:,} px\n{meta["source_profile"]}' + ('\n透明背景將保留' if meta['alpha'] else ''))
        self.preview_hint.setText('雙擊圖片比較細節 · 滾輪放大')
        self.set_status(''); self.apply_preset()

    def remove_selected(self):
        row = self.queue.currentRow()
        if self.busy or row < 0:
            return
        self.files.pop(row); self.queue.takeItem(row)
        if not self.files:
            self.image = None; self.canvas.set_images(None); self._filename_value = ''
            self.source_info.setText('來源：尚未加入圖片')
            self.set_status('')
        else:
            self.select_file(self.queue.currentRow())
        self.update_estimate()

    def set_preview_center(self, point):
        self.preview_center = point
        self.preview_hint.setText('雙擊檢查這個位置 · 滾輪放大')

    def show_full(self):
        if self.image is not None and not self.busy:
            self.canvas.set_images(self.image)
            self.preview_hint.setText('雙擊圖片比較細節 · 滾輪放大')

    def start_preview(self):
        row = self.queue.currentRow()
        if self.busy or row < 0 or self.image is None:
            return
        self.start_worker(Worker([(self.files[row], None)], self.options(), self.preview_center))

    def start_export(self):
        if self.busy or not self.files:
            return
        opts = self.options(); ext = {'png': '.png', 'tiff': '.tiff', 'jpeg': '.jpg'}[opts.format]
        spec_name = f'{self.width_cm.value():g}x{self.height_cm.value():g}cm' if self.preset.currentText() == '自訂' else self.preset.currentText()
        if len(self.files) == 1:
            suggested = self.files[0].with_name(self.files[0].stem + f'_{spec_name}_{opts.ppi}DPI' + ext)
            filename, _ = QFileDialog.getSaveFileName(self, '匯出放大圖片', str(suggested), f'{opts.format.upper()} (*{ext})')
            if not filename:
                return
            destination = Path(filename)
            if destination.suffix.lower() not in (ext, '.jpeg' if opts.format == 'jpeg' else ext, '.tif' if opts.format == 'tiff' else ext):
                destination = destination.with_suffix(ext)
            jobs = [(self.files[0], destination)]
        else:
            folder = QFileDialog.getExistingDirectory(self, '選擇批次輸出資料夾')
            if not folder:
                return
            jobs, reserved = [], set()
            for source in self.files:
                destination = Path(folder) / (source.stem + f'_{spec_name}_{opts.ppi}DPI' + ext)
                index = 2
                while destination.exists() or destination in reserved or destination.resolve() == source.resolve():
                    destination = Path(folder) / (source.stem + f'_{spec_name}_{opts.ppi}DPI_{index}' + ext); index += 1
                reserved.add(destination); jobs.append((source, destination))
        self.active_jobs = jobs
        self.start_worker(Worker(jobs, opts))

    def start_worker(self, worker):
        self.worker = worker; self.busy = True
        for control in self.controls:
            control.setEnabled(False)
        self.add_button.setEnabled(False); self.queue.setEnabled(False)
        self.cancel_button.setEnabled(True); self.cancel_button.setVisible(True)
        self.progress.setValue(0); self.progress.show(); self.percentage.setText('0%')
        self.open_output_button.hide(); self.error_button.hide(); self.last_errors = []
        self.set_status('正在準備圖片…')
        worker.progress.connect(self.on_progress); worker.failure.connect(self.on_failure)
        worker.preview.connect(self.on_preview); worker.result.connect(self.on_result)
        worker.itemStarted.connect(self.on_item_started); worker.itemDone.connect(self.on_item_done)
        worker.finished.connect(self.on_finished); self.update_estimate(); worker.start()

    def on_progress(self, value, message):
        self.progress.setValue(value); self.percentage.setText(f'{value}%')
        batch = message.split(' · ')[0] + ' · ' if self.worker and len(self.worker.jobs) > 1 else ''
        if '模型' in message: message = '準備 AI…'
        elif 'AI 放大中' in message: message = '重建圖片細節…'
        elif '寫入' in message: message = '儲存印刷檔案…'
        elif '完成' in message: message = '已完成'
        elif '讀取' in message: message = '讀取圖片…'
        elif '尺寸' in message: message = '調整印刷尺寸…'
        self.set_status(batch + message)

    def on_preview(self, original, result):
        self.canvas.set_images(original, result)
        method = '保真縮放' if self.worker.options.model == 'faithful' else 'AI 4×'
        self.preview_hint.setText(f'原圖縮放基準 ← 拖動比較線 → {method} · Esc 返回全圖')
        self.canvas.setToolTip('左右方向鍵可調整比較線。AI 預覽顯示第一次 4×；加強模式的第二次重建請核對完整輸出。')
        self.set_status('細節預覽已完成')

    def on_result(self, result):
        done, errors = result['done'], result['errors']
        self.progress.setValue(100)
        self.set_status(f'已完成 {len(done)} 張' + (f' · {len(errors)} 張未完成' if errors else ' · 原圖已保留'), error=bool(errors))
        if done:
            self.last_output = Path(done[-1]['output']); self.open_output_button.setEnabled(True); self.open_output_button.show()
        if errors:
            self.last_errors = errors; self.error_button.show()

    def on_item_started(self, index):
        if index < self.queue.count():
            self.queue.item(index).setText(self.active_jobs[index][0].name + '  ·  處理中')

    def on_item_done(self, index, result):
        if index < self.queue.count():
            self.queue.item(index).setText(self.active_jobs[index][0].name + ('  ·  失敗' if 'error' in result else '  ·  完成 ✓'))
        if 'output' in result:
            self.last_output = Path(result['output']); self.open_output_button.setEnabled(True)

    def on_failure(self, message):
        cancelled = not message or '取消' in message
        self.set_status(message or '工作已取消，原圖保留。', error=not cancelled)
        if not cancelled:
            self.last_errors = [message]; self.error_button.show()
        if self.active_jobs:
            for index, job in enumerate(self.active_jobs):
                item = self.queue.item(index)
                if item is not None and '處理中' in item.text():
                    item.setText(job[0].name + '  ·  已停止')

    def on_finished(self):
        self.busy = False
        for control in self.controls:
            control.setEnabled(True)
        self.add_button.setEnabled(True); self.queue.setEnabled(True); self.cancel_button.setVisible(False)
        self.progress.hide(); self.percentage.setText('')
        self.worker = None; self.active_jobs = []; self.update_estimate()

    def cancel_work(self):
        if self.worker:
            self.worker.cancel_event.set(); self.cancel_button.setEnabled(False)
            self.set_status('正在取消，原圖與已完成檔案會保留…')

    def set_status(self, message, error=False):
        self.status.setText(message); self.status.setProperty('error', error)
        self.status_bar.setVisible(bool(message))
        self.status.style().unpolish(self.status); self.status.style().polish(self.status)

    def show_settings(self):
        if not self.busy:
            self.settings_dialog.show(); self.settings_dialog.raise_(); self.settings_dialog.activateWindow()

    def show_errors(self):
        if self.last_errors:
            QMessageBox.information(self, '未完成的圖片', '\n\n'.join(self.last_errors))

    def update_caption(self):
        if hasattr(self, 'file_caption'):
            self.file_caption.setText(self.file_caption.fontMetrics().elidedText(self._filename_value,
                Qt.TextElideMode.ElideMiddle, max(80, self.file_caption.width())))
            self.file_caption.setToolTip(self._filename_value)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_filename_value'): self.update_caption()

    def open_output(self):
        if self.last_output:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.last_output.parent)))

    def show_about(self):
        QMessageBox.information(self, '關於 AI 圖片放大王',
            f'{APP_NAME} {VERSION}\n\n本地 AI 圖片放大 · A1／A2／A3／A4／A5\n'
            '圖片由本機處理。模型已附帶，不需帳號或網絡。\n'
            '本版：8-bit sRGB；PNG／JPEG／TIFF。\n\n'
            'Real-ESRGAN：BSD-3-Clause\nBasicSR 架構：Apache-2.0\nQt／PySide6：LGPLv3\n'
            '本項目：Apache-2.0 開源授權。\n完整授權及來源連結隨發佈包提供。')

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.cancel_event.set()
            self.set_status('正在停止，完成後可關閉視窗。')
            event.ignore()
        else:
            event.accept()
