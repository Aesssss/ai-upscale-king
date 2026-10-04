"""Print-studio visual system and canvas. All assets are drawn locally."""
from PIL import Image
from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QFont, QImage, QPixmap, QPainterPath
from PySide6.QtWidgets import QWidget, QLabel, QPushButton, QComboBox

PAPER = '#F7F6F2'
INK = '#272B28'
MUTED = '#646961'
ACCENT = '#A34427'

STYLE = '''
QMainWindow, QWidget#root, QDialog { background: #F7F6F2; }
QWidget#settingsBody, QWidget#settingsViewport { background: #F7F6F2; }
QWidget { font-family: "PingFang TC", ".AppleSystemUIFont", "Microsoft JhengHei", sans-serif;
          font-size: 13px; color: #272B28; }
QLabel#brand { font-size: 19px; font-weight: 600; }
QLabel#muted, QLabel#source { color: #646961; font-size: 12px; }
QLabel#eyebrow { color: #646961; font-size: 11px; }
QLabel#filename { font-size: 14px; font-weight: 500; }
QLabel#estimate { font-family: "SF Pro Text", "PingFang TC", sans-serif; font-size: 13px; }
QLabel#section { font-weight: 600; font-size: 14px; }
QLabel#dialogTitle { font-size: 23px; font-weight: 600; }
QLabel#status { color: #646961; font-size: 12px; }
QLabel#status[error="true"] { color: #A34427; }
QLabel#percentage { font-family: "SF Mono", "Menlo", monospace; font-size: 11px; color: #646961; }
QFrame#rule { background: #DDDCD4; max-height: 1px; border: none; }
QFrame#rail { border-top: 1px solid #DDDCD4; background: #F7F6F2; }
QFrame#workspace { background: #EDECE6; border: none; border-radius: 12px; }
QPushButton { background: transparent; border: 1px solid transparent; border-radius: 7px;
              padding: 8px 13px; min-height: 19px; font-weight: 500; }
QPushButton:hover { background: #E8E6DE; }
QPushButton:pressed { background: #DDDAD0; }
QPushButton:focus { border: 1px solid #A34427; }
QPushButton:disabled { color: #A4A69F; }
QPushButton#primary { background: #272B28; color: #FFFFFF; border: 1px solid #272B28;
                      padding: 11px 24px; font-size: 14px; font-weight: 600; min-height: 23px; }
QPushButton#primary:hover { background: #404A3F; border-color: #404A3F; }
QPushButton#primary:pressed { background: #1B201B; border-color: #1B201B; }
QPushButton#primary:focus { border: 2px solid #A34427; padding: 10px 23px; }
QPushButton#primary:disabled { background: #DEDFD8; border-color: #DEDFD8; color: #757A70; }
QPushButton#textAction { padding: 6px 10px; font-size: 12px; color: #646961; }
QPushButton#textAction:hover { color: #272B28; background: #E8E6DE; }
QPushButton#overflow { font-size: 23px; padding: 0px; min-height: 30px; min-width: 36px; }
QPushButton#overflow::menu-indicator { image: none; width: 0px; height: 0px; }
QComboBox, QSpinBox, QDoubleSpinBox { background: #FFFFFF; border: 1px solid #D9DAD2;
    border-radius: 6px; padding: 7px 10px; min-height: 20px; selection-background-color: #E8E3D9; }
QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus { border-color: #A34427; }
QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled { background: #EEEDE7; color: #858A80; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox::down-arrow { image: none; }
QComboBox QAbstractItemView { background: #FFFFFF; color: #272B28; border: 1px solid #D9DAD2;
    selection-color: #272B28; selection-background-color: #ECE9E1; padding: 5px; }
QComboBox#paperPreset { background: transparent; border: none; padding: 0px 28px 0px 0px;
    font-size: 25px; font-weight: 600; min-height: 31px; }
QComboBox#paperPreset:hover { color: #A34427; }
QComboBox#paperPreset:focus { border-bottom: 1px solid #A34427; }
QComboBox#paperPreset::down-arrow { image: none; }
QComboBox#paperPreset QAbstractItemView { font-size: 15px; }
QListWidget { border: none; background: transparent; outline: none; }
QListWidget::item { color: #646961; padding: 5px 8px; margin: 0px 3px; border: 1px solid transparent; border-radius: 7px; }
QListWidget::item:selected { background: #E9E6DE; color: #272B28; border-color: #CCC6B8; }
QListWidget::item:hover { background: #EEEBE4; }
QListWidget:focus { border-bottom: 1px solid #A34427; }
QProgressBar { border: none; background: #DDDCD4; min-height: 3px; max-height: 3px; }
QProgressBar::chunk { background: #A34427; }
QMenu { background: #FFFFFF; color: #272B28; border: 1px solid #D9DAD2; padding: 6px; }
QMenu::item { padding: 8px 20px; border-radius: 4px; }
QMenu::item:selected { background: #ECE9E1; }
QMenu::item:disabled { color: #A4A69F; }
QMenu::separator { height: 1px; background: #E6E5DE; margin: 5px 8px; }
QScrollArea { background: transparent; border: none; }
QScrollBar:horizontal, QScrollBar:vertical { background: transparent; height: 5px; width: 5px; }
QScrollBar::handle { background: #C4C6BB; border-radius: 2px; min-width: 25px; min-height: 25px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0px; height: 0px; }
QToolTip { background: #FFFFFF; color: #272B28; padding: 6px; border: 1px solid #D9DAD2; }
'''


def label(text, name=None, wrap=False):
    result = QLabel(text)
    result.setTextFormat(Qt.TextFormat.PlainText)
    if name:
        result.setObjectName(name)
    result.setWordWrap(wrap)
    return result


def pixmap(image: Image.Image):
    im = image.copy()
    im.thumbnail((1800, 1800), Image.Resampling.LANCZOS)
    im = im.convert('RGBA')
    return QPixmap.fromImage(QImage(im.tobytes(), im.width, im.height, im.width * 4,
        QImage.Format.Format_RGBA8888).copy())


class PrintMark(QWidget):
    def __init__(self):
        super().__init__(); self.setFixedSize(34, 34)

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor(ACCENT), 1.8))
        p.drawRoundedRect(QRectF(6, 11, 17, 17), 1.5, 1.5)
        p.drawLine(17, 17, 29, 5); p.drawLine(20, 5, 29, 5); p.drawLine(29, 5, 29, 14)


class PaperSelector(QComboBox):
    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor(MUTED), 1.3))
        x, y = self.width() - 13, self.height() / 2
        p.drawLine(round(x - 4), round(y - 2), round(x), round(y + 2))
        p.drawLine(round(x), round(y + 2), round(x + 4), round(y - 2))


class ImageCanvas(QWidget):
    filesDropped = Signal(list)
    centerPicked = Signal(tuple)
    previewRequested = Signal()
    browseRequested = Signal()
    splitChanged = Signal(int)

    def __init__(self):
        super().__init__(); self.setAcceptDrops(True); self.setMinimumSize(360, 180)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.original = self.result = None
        self.split = .5; self.zoom = 1.; self.point = (.5, .5); self.point_visible = False
        self.image_rect = QRectF(); self.dropping = False
        self.empty_button = QPushButton('選擇圖片', self); self.empty_button.setObjectName('primary')
        self.empty_button.clicked.connect(self.browseRequested)
        self.empty_button.setAccessibleName('選擇圖片，可一次加入多張')
        self.setAccessibleName('圖片工作區')
        self.setAccessibleDescription('拖入圖片。加入後雙擊圖片或按 P 比較 AI 細節，滾輪放大。')

    def set_images(self, original, result=None):
        self.original = pixmap(original) if original is not None else None
        self.result = pixmap(result) if result is not None else None
        self.zoom = 1.; self.point_visible = False
        self.empty_button.setVisible(original is None); self.update()

    def empty_layout(self):
        cy = self.height() / 2
        return self.width() * .51, cy

    def resizeEvent(self, event):
        x, cy = self.empty_layout()
        self.empty_button.setGeometry(round(x), round(cy + 35), 155, 47)
        super().resizeEvent(event)

    def crop_marks(self, p, rect, color='#AAAFA1'):
        p.setPen(QPen(QColor(color), 1))
        for x, y, sx, sy in [(rect.left(), rect.top(), -1, -1), (rect.right(), rect.top(), 1, -1),
                             (rect.left(), rect.bottom(), -1, 1), (rect.right(), rect.bottom(), 1, 1)]:
            p.drawLine(round(x + sx * 6), round(y), round(x + sx * 15), round(y))
            p.drawLine(round(x), round(y + sy * 6), round(x), round(y + sy * 15))

    def paint_empty(self, p):
        text_x, cy = self.empty_layout()
        width = min(187, self.width() * .22); height = width * 1.414
        sheet = QRectF(self.width() * .285 - width / 2, cy - height / 2, width, height)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor('#DFDED5'))
        p.drawRoundedRect(sheet.translated(8, 9), 2, 2)
        p.setBrush(QColor('#FFFEFA')); p.drawRoundedRect(sheet, 2, 2)
        self.crop_marks(p, sheet.adjusted(-4, -4, 4, 4))
        inner = sheet.adjusted(18, 22, -18, -22)
        p.save(); p.setClipRect(inner)
        p.fillRect(inner, QColor('#E9E2D3'))
        p.setBrush(Qt.BrushStyle.NoBrush)
        # Graphic contour print: the large image is the product's single focal point.
        for i in range(14):
            path = QPainterPath(); yy = inner.bottom() - i * 12
            path.moveTo(inner.left() - 30, yy)
            path.cubicTo(inner.left() + 35, yy - 78, inner.right() - 22, yy + 95, inner.right() + 25, yy - 38)
            p.setPen(QPen(QColor(ACCENT if i % 3 == 0 else '#BBAE95'), 1.1)); p.drawPath(path)
        p.restore()
        p.setPen(QColor(MUTED)); f = QFont(self.font()); f.setPixelSize(11); f.setWeight(QFont.Weight.Medium)
        p.setFont(f); p.drawText(QRectF(text_x, cy - 80, self.width() - text_x - 25, 25), '為印刷而放大')
        f.setPixelSize(31 if self.width() >= 900 else 27); f.setWeight(QFont.Weight.DemiBold)
        p.setFont(f); p.setPen(QColor(INK))
        p.drawText(QRectF(text_x, cy - 45, self.width() - text_x - 20, 47), '把小圖，印成大作。')
        f.setPixelSize(13); f.setWeight(QFont.Weight.Normal); p.setFont(f); p.setPen(QColor(MUTED))
        p.drawText(QRectF(text_x, cy + 4, self.width() - text_x - 25, 25), '拖入圖片，或從本機選擇。')
        f.setPixelSize(11); p.setFont(f)
        p.drawText(QRectF(text_x, cy + 94, self.width() - text_x - 25, 25), 'PNG、JPG、TIFF、WebP · 支援批次')

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor('#E9E6DC' if self.dropping else '#EDECE6'))
        p.drawRoundedRect(QRectF(self.rect()), 12, 12)
        if self.original is None:
            self.paint_empty(p); return
        ratio = min((self.width() - 76) / self.original.width(),
                    (self.height() - 62) / self.original.height()) * self.zoom
        width, height = self.original.width() * ratio, self.original.height() * ratio
        rect = QRectF((self.width() - width) / 2, (self.height() - height) / 2, width, height)
        self.image_rect = rect
        p.save(); p.setClipRect(self.rect()); p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor('#DAD9D0')); p.drawRect(rect.translated(0, 3))
        p.fillRect(rect, QColor('#FFFFFF'))
        p.save(); p.setClipRect(rect)
        for y in range(int(max(0, rect.top())), int(min(self.height(), rect.bottom())), 12):
            for x in range(int(max(0, rect.left())), int(min(self.width(), rect.right())), 12):
                if (x // 12 + y // 12) % 2 == 0: p.fillRect(x, y, 12, 12, QColor('#ECECE8'))
        p.drawPixmap(rect, self.original, QRectF(self.original.rect()))
        if self.result is not None:
            split_x = rect.left() + rect.width() * self.split
            p.setClipRect(QRectF(split_x, rect.top(), rect.right() - split_x, rect.height()))
            p.drawPixmap(rect, self.result, QRectF(self.result.rect())); p.restore()
            p.setPen(QPen(QColor(ACCENT), 1.4))
            p.drawLine(round(split_x), max(0, round(rect.top())), round(split_x), min(self.height(), round(rect.bottom())))
            p.setBrush(QColor('#FFFEFA')); p.drawEllipse(QRectF(split_x - 12, self.height() / 2 - 12, 24, 24))
            p.setPen(QColor(INK)); p.drawText(QRectF(split_x - 12, self.height() / 2 - 12, 24, 24), Qt.AlignmentFlag.AlignCenter, '↔')
        else:
            p.restore()
            if self.point_visible:
                x, y = rect.left() + self.point[0] * width, rect.top() + self.point[1] * height
                p.setPen(QPen(QColor(ACCENT), 1.3)); p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawEllipse(QRectF(x - 9, y - 9, 18, 18))
        if self.zoom == 1: self.crop_marks(p, rect.adjusted(-3, -3, 3, 3))
        p.restore()

    def choose_point(self, event):
        if not self.image_rect.contains(event.position()): return
        x = (event.position().x() - self.image_rect.left()) / self.image_rect.width()
        y = (event.position().y() - self.image_rect.top()) / self.image_rect.height()
        if self.result is not None:
            self.split = min(1, max(0, x)); self.splitChanged.emit(round(self.split * 100))
        else:
            self.point = (x, y); self.point_visible = True; self.centerPicked.emit(self.point)
        self.update()

    def mousePressEvent(self, event):
        self.setFocus(); self.choose_point(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton: self.choose_point(event)

    def mouseDoubleClickEvent(self, event):
        if self.original is not None and self.result is None:
            self.choose_point(event); self.previewRequested.emit()

    def wheelEvent(self, event):
        if self.original is not None:
            self.zoom = min(4, max(1, self.zoom * (1.12 if event.angleDelta().y() > 0 else 1 / 1.12))); self.update()

    def keyPressEvent(self, event):
        if self.result is not None and event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right):
            self.split = min(1, max(0, self.split + (.05 if event.key() == Qt.Key.Key_Right else -.05)))
            self.splitChanged.emit(round(self.split * 100)); self.update(); event.accept()
        else:
            super().keyPressEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            self.dropping = True; self.update(); event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self.dropping = False; self.update()

    def dropEvent(self, event):
        self.dropping = False; self.update()
        self.filesDropped.emit([url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()])
        event.acceptProposedAction()
