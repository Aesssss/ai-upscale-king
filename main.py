"""Desktop entry and local integration-test entry. No runtime networking."""
import argparse
import json
import os
import sys
from pathlib import Path


def main():
    # PyInstaller's Windows GUI bootloader has no attached console.
    for stream in ('stdout', 'stderr'):
        if getattr(sys, stream) is None:
            setattr(sys, stream, open(os.devnull, 'w', encoding='utf-8'))
    if '--self-test' in sys.argv:
        from app.core import Options, PRESETS, process_image
        parser = argparse.ArgumentParser()
        parser.add_argument('--self-test', type=Path, required=True)
        parser.add_argument('--output', type=Path, required=True)
        parser.add_argument('--preset', default='A1', choices=list(PRESETS))
        parser.add_argument('--ppi', type=int, default=300)
        parser.add_argument('--width-cm', type=float)
        parser.add_argument('--height-cm', type=float)
        parser.add_argument('--fit', default='image', choices=['image', 'contain', 'cover'])
        parser.add_argument('--model', default='anime', choices=['photo', 'anime', 'faithful'])
        parser.add_argument('--format', default='png', choices=['png', 'tiff', 'jpeg'])
        parser.add_argument('--strategy', default='standard', choices=['standard', 'detail'])
        parser.add_argument('--device', default='auto', choices=['auto', 'cpu'])
        parser.add_argument('--report', type=Path)
        args = parser.parse_args()
        width, height = PRESETS[args.preset]
        if (args.width_cm is None) != (args.height_cm is None):
            parser.error('--width-cm and --height-cm must be supplied together')
        if args.width_cm is not None: width, height = args.width_cm * 10, args.height_cm * 10
        result = process_image(args.self_test, args.output,
            Options(width_mm=width, height_mm=height, ppi=args.ppi, model=args.model,
                    format=args.format, strategy=args.strategy, device=args.device, fit=args.fit),
            progress=lambda p, s: print(json.dumps({'progress': p, 'status': s}, ensure_ascii=False), flush=True))
        if args.report:
            args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        if sys.stdout is not None:
            print(json.dumps(result, ensure_ascii=False), flush=True)
        return
    from PySide6.QtWidgets import QApplication
    from app.window import MainWindow, STYLE
    application = QApplication(sys.argv)
    application.setApplicationName('AI 圖片放大王')
    application.setOrganizationName('ImageUpscaleKing')
    application.setStyle('Fusion')
    application.setStyleSheet(STYLE)
    window = MainWindow(); window.show()
    if '--check-gui' in sys.argv:
        from PySide6.QtCore import QTimer
        from app.core import VERSION
        parser = argparse.ArgumentParser()
        parser.add_argument('--check-gui', action='store_true')
        parser.add_argument('--report', type=Path, required=True)
        args = parser.parse_args()
        def check_gui():
            report = {'version': VERSION, 'title': window.windowTitle(),
                      'visible': window.isVisible(), 'preset': window.preset.currentText(),
                      'dpi': window.options().ppi, 'fit': window.options().fit}
            args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            application.quit()
        QTimer.singleShot(250, check_gui)
        sys.exit(application.exec())
    if len(sys.argv) > 1:
        window.add_files(sys.argv[1:])
    sys.exit(application.exec())


if __name__ == '__main__':
    main()
