"""Progressive disclosure for settings used less often than the paper size."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox,
    QDoubleSpinBox, QSpinBox, QPushButton, QWidget, QScrollArea, QFrame)
from app.design import label, PaperSelector


class AdvancedSettings(QDialog):
    def __init__(self, owner):
        super().__init__(owner); self.setWindowTitle('進階設定'); self.resize(490, 710)
        self.setMinimumSize(460, 530)
        layout = QVBoxLayout(self); layout.setContentsMargins(30, 28, 30, 24); layout.setSpacing(14)
        layout.addWidget(label('進階設定', 'dialogTitle'))
        layout.addWidget(label('預設已適合印刷。需要時才調整。', 'muted'))
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        body = QWidget(); body.setObjectName('settingsBody'); scroll.viewport().setObjectName('settingsViewport')
        content = QVBoxLayout(body); content.setContentsMargins(0, 8, 8, 8); content.setSpacing(17)
        owner.orientation = PaperSelector()
        for text, data in [('跟隨原圖', 'auto'), ('直向', 'portrait'), ('橫向', 'landscape')]:
            owner.orientation.addItem(text, data)
        owner.ppi = QSpinBox(); owner.ppi.setObjectName('printPPI'); owner.ppi.setRange(50, 600)
        owner.ppi.setValue(300); owner.ppi.setSuffix(' PPI')
        owner.bleed = QDoubleSpinBox(); owner.bleed.setRange(0, 5); owner.bleed.setDecimals(1); owner.bleed.setSuffix(' mm／邊')
        owner.output_format = PaperSelector()
        for text, data in [('PNG · 無損，保留透明', 'png'), ('TIFF · 印刷交付', 'tiff'), ('JPEG · 檔案較小', 'jpeg')]:
            owner.output_format.addItem(text, data)
        owner.model = PaperSelector()
        for text, data in [('一般圖片', 'photo'), ('動漫／插畫', 'anime'), ('文字／Logo 保真', 'faithful')]:
            owner.model.addItem(text, data)
        owner.strategy = PaperSelector(); owner.strategy.addItem('自然 · 標準', 'standard'); owner.strategy.addItem('加強 · 較慢', 'detail')
        owner.fit = PaperSelector()
        for text, data in [('等比例原圖 · 不加邊、不裁切', 'image'), ('完整紙張 · 留白', 'contain'), ('完整紙張 · 置中裁切', 'cover')]:
            owner.fit.addItem(text, data)
        owner.compute = PaperSelector(); owner.compute.addItem('自動選擇', 'auto'); owner.compute.addItem('CPU 相容模式', 'cpu')
        owner.width_mm = QDoubleSpinBox(); owner.height_mm = QDoubleSpinBox()
        for spin, value in ((owner.width_mm, 594), (owner.height_mm, 841)):
            spin.setRange(1, 1990); spin.setDecimals(1); spin.setSuffix(' mm'); spin.setValue(value)
        owner.controls = [owner.preset]

        def section(title, rows):
            content.addWidget(label(title, 'section'))
            form = QFormLayout(); form.setSpacing(11); form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
            for caption, control in rows:
                form.addRow(caption, control); control.setAccessibleName(caption); owner.controls.append(control)
            content.addLayout(form)

        section('印刷交付', [('尺寸方向', owner.orientation), ('解析度', owner.ppi), ('出血', owner.bleed), ('檔案格式', owner.output_format)])
        rule = QFrame(); rule.setObjectName('rule'); content.addWidget(rule)
        section('圖片處理', [('圖片類型', owner.model), ('細節', owner.strategy), ('比例', owner.fit), ('運算', owner.compute)])
        owner.controls.extend([owner.width_mm, owner.height_mm, owner.width_cm, owner.height_cm])
        owner.quality_hint = label('', 'muted', True); content.addWidget(owner.quality_hint)
        owner.source_info = label('', 'muted', True); content.addWidget(owner.source_info)
        content.addWidget(label('sRGB、8-bit。印刷前請核對細節與印刷商的色彩規格。', 'muted', True))
        content.addStretch(); scroll.setWidget(body); layout.addWidget(scroll, 1)
        row = QHBoxLayout(); row.addWidget(label('圖片始終在本機處理', 'muted')); row.addStretch()
        done = QPushButton('完成'); done.setObjectName('primary')
        done.setAutoDefault(False); done.setDefault(False)
        done.clicked.connect(self.close); row.addWidget(done)
        layout.addLayout(row)
