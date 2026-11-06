"""Portable Windows entry point; no developer drive dependency."""
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication,QMessageBox
from app import MainWindow
from portable_paths import database_path

def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--smoke-test',type=Path,help=argparse.SUPPRESS);args=parser.parse_args()
    app=QApplication(sys.argv);app.setApplicationName('Keylane');app.setOrganizationName('Keylane')
    data=database_path('Keylane')
    try:win=MainWindow(data)
    except Exception as exc:
        QMessageBox.critical(None,'Keylane 无法启动',f'无法初始化学习记录：{data}\n请把 EXE 和 data 一起放到可写文件夹。\n{exc}');return 1
    win.show()
    if args.smoke_test:
        from PySide6.QtCore import QTimer
        import json
        def smoke():
            before=win.store.summary()['attempts'];win.navigate(2);win.formula.choose(0);win.formula.input.setText('=SUM(B2:B5)');win.formula.check()
            report={'visible':win.isVisible(),'database':str(data),'attempts_before':before,'attempts_after':win.store.summary()['attempts'],'formula_solved':win.formula.solved,'runtime':str(getattr(sys,'_MEIPASS',''))}
            win.grab().save(str(args.smoke_test.with_suffix('.png')));args.smoke_test.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');win.close()
        QTimer.singleShot(400,smoke)
    return app.exec()

if __name__=='__main__':sys.exit(main())
