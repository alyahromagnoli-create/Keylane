"""Reusable UI controls, local spreadsheet and an on-screen keyboard."""
import time
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (QWidget,QLabel,QPushButton,QVBoxLayout,QHBoxLayout,QGridLayout,QFrame,QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,QTableWidgetSelectionRange,QSizePolicy)
from formula import Engine,FormulaError,address

STYLE='''
QWidget { font-family: "Microsoft YaHei UI", "Segoe UI"; font-size: 14px; color:#243248; }
QMainWindow, QWidget#root {background:#f5f6f8;}
QFrame#sidebar {background:#182536; border:0;}
QLabel#brand {color:#ffffff;font-size:26px;font-weight:700;}
QLabel#sideNote {color:#aab9ca;font-size:12px;}
QPushButton#nav {color:#cbd5e1; background:transparent; border:0; text-align:left;padding:14px 18px;border-radius:5px;}
QPushButton#nav:checked {color:#ffffff;background:#2c435f; border-left:3px solid #85aaff;}
QPushButton#nav:hover {background:#25374d;}
QLabel#title {font-size:28px;font-weight:700;color:#182536;}
QLabel#subtitle {font-size:13px;color:#66758a;}
QLabel#section {font-size:18px;font-weight:600;color:#182536;}
QLabel#task {font-size:21px;font-weight:600;color:#1e3454;}
QLabel#number {font-size:36px;font-weight:650;color:#254d92;}
QLabel#feedback {background:#edf2f9; border:1px solid #d8e2f0;border-radius:5px;padding:12px;}
QFrame#panel {background:#ffffff;border:1px solid #dce2e9;border-radius:7px;}
QPushButton {background:#ffffff;border:1px solid #cbd4e0;border-radius:5px;padding:8px 16px;min-height:20px;}
QPushButton:hover {background:#edf2fa;border-color:#8ca8d0;}
QPushButton:pressed {background:#dce7f6;}
QPushButton:disabled {color:#8a97a8;background:#f1f3f6;border-color:#dce1e9;}
QPushButton#primary {background:#315eaa;color:white;border:1px solid #315eaa;font-weight:600;}
QPushButton#primary:hover {background:#244d91;}
QPushButton#primary:disabled {background:#a9bad5;border-color:#a9bad5;}
QPushButton#key {padding:5px 2px;background:#f8fafc;border:1px solid #ccd6e1;border-bottom:3px solid #bdcbdc;font-size:12px;min-width:28px;}
QPushButton#key:checked {background:#315eaa;color:#ffffff;border-color:#244d91;}
QLineEdit,QComboBox,QSpinBox {background:#fff;border:1px solid #c6d0df;border-radius:4px;padding:8px;min-height:20px;selection-background-color:#315eaa;}
QLineEdit:focus {border:2px solid #315eaa;padding:7px;}
QListWidget {background:white;border:1px solid #dce2e9;border-radius:5px;outline:none;}
QListWidget::item {padding:11px 9px;border-bottom:1px solid #edf0f5;}
QListWidget::item:selected {background:#e5eefc;color:#214b92;}
QTableWidget {background:#fff;alternate-background-color:#f8fafc;border:1px solid #d8e0ea;gridline-color:#e2e8ef;selection-background-color:#dbe9ff;selection-color:#182536;}
QHeaderView::section {background:#edf1f6;padding:6px;border:0;border-right:1px solid #d8e0ea;border-bottom:1px solid #d8e0ea;color:#536278;}
QProgressBar {border:0;background:#e5ebf3;border-radius:3px;height:7px;text-align:center;}
QProgressBar::chunk {background:#315eaa;border-radius:3px;}
QScrollArea {background:transparent;border:0;}
QScrollBar:vertical {background:#edf1f6;width:10px;border:0;}
QScrollBar::handle:vertical {background:#b7c4d6;border-radius:4px;min-height:30px;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0;}
QToolTip {background:#182536;color:white;border:0;padding:6px;}
'''

def label(text,kind=None):
    w=QLabel(text);w.setWordWrap(True)
    if kind:w.setObjectName(kind)
    w.setTextFormat(Qt.TextFormat.PlainText)
    return w

def button(text,callback=None,primary=False):
    w=QPushButton(text)
    if primary:w.setObjectName('primary')
    if callback:w.clicked.connect(callback)
    return w

def panel():
    frame=QFrame();frame.setObjectName('panel');layout=QVBoxLayout(frame);layout.setContentsMargins(22,20,22,20);layout.setSpacing(12)
    return frame,layout

class Clock:
    def __init__(self):self.reset()
    def reset(self):self.total=0.;self.started=None
    def resume(self):
        if self.started is None:self.started=time.monotonic()
    def pause(self):
        if self.started is not None:self.total+=time.monotonic()-self.started;self.started=None
    def ms(self):return int(1000*(self.total+(time.monotonic()-self.started if self.started is not None else 0)))

def combo_from_event(event):
    mods=event.modifiers();keys=[]
    for flag,name in ((Qt.KeyboardModifier.ControlModifier,'Ctrl'),(Qt.KeyboardModifier.AltModifier,'Alt'),(Qt.KeyboardModifier.ShiftModifier,'Shift'),(Qt.KeyboardModifier.MetaModifier,'Win')):
        if mods&flag:keys.append(name)
    key=event.key()
    if key in (Qt.Key.Key_Control,Qt.Key.Key_Shift,Qt.Key.Key_Alt,Qt.Key.Key_Meta,Qt.Key.Key_AltGr):return None
    specials={Qt.Key.Key_Space:'Space',Qt.Key.Key_Delete:'Delete',Qt.Key.Key_Home:'Home',Qt.Key.Key_End:'End',Qt.Key.Key_Down:'Down',Qt.Key.Key_Up:'Up',Qt.Key.Key_Left:'Left',Qt.Key.Key_Right:'Right',Qt.Key.Key_Tab:'Tab',Qt.Key.Key_Return:'Enter',Qt.Key.Key_Escape:'Esc'}
    if key in specials:keys.append(specials[key])
    elif Qt.Key.Key_F1<=key<=Qt.Key.Key_F12:keys.append('F'+str(key-Qt.Key.Key_F1+1))
    elif 32<=key<=126:keys.append(chr(key).upper())
    else:return None
    return '+'.join(keys)

class Keyboard(QWidget):
    submitted=Signal(str)
    def __init__(self):
        super().__init__();self.modifiers=set();self.last=None;self.keys={}
        v=QVBoxLayout(self);v.setContentsMargins(0,0,0,0);v.setSpacing(5)
        rows=[['Esc','F1','F2','F3','F4','F5','F6','F7','F8','F9','F10','F11','F12'],list('1234567890')+['Home','End','Delete'],['Tab']+list('QWERTYUIOP'),list('ASDFGHJKL')+['Enter'],['Shift']+list('ZXCVBNM')+['Up'],['Ctrl','Win','Alt','Space','Left','Down','Right']]
        for row in rows:
            h=QHBoxLayout();h.setSpacing(4)
            for key in row:
                b=QPushButton(key);b.setObjectName('key');b.setCheckable(True);b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                b.clicked.connect(lambda checked=False,k=key:self.click_key(k))
                self.keys[key]=b;h.addWidget(b,4 if key=='Space' else 1)
            v.addLayout(h)
        h=QHBoxLayout();self.display=label('点击修饰键，再点击字母或功能键。','subtitle');h.addWidget(self.display,1)
        self.clear_button=button('清空',self.clear);h.addWidget(self.clear_button)
        self.submit=button('提交虚拟组合',self.emit_combo);h.addWidget(self.submit);v.addLayout(h)
    def click_key(self,key):
        if key in ('Ctrl','Alt','Shift','Win'):
            if key in self.modifiers:self.modifiers.remove(key)
            else:self.modifiers.add(key)
        else:self.last=key
        self.show_keys(self.combo().split('+'));self.display.setText(self.combo() or '点击键帽组合按键。')
    def combo(self):return '+'.join([k for k in ('Ctrl','Alt','Shift','Win') if k in self.modifiers]+([self.last] if self.last else []))
    def emit_combo(self):
        if self.last:self.submitted.emit(self.combo())
    def show_keys(self,keys):
        for key,b in self.keys.items():b.setChecked(key in keys)
    def clear(self):
        self.modifiers.clear();self.last=None;self.show_keys([]);self.display.setText('点击修饰键，再点击字母或功能键。')

class Grid(QTableWidget):
    edited=Signal()
    def __init__(self,rows=9,cols=6):
        super().__init__(rows,cols);self.raw={};self.loading=False
        self.setHorizontalHeaderLabels([address(1,c+1)[:-1] for c in range(cols)])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.verticalHeader().setDefaultSectionSize(34);self.verticalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAlternatingRowColors(True);self.setSelectionMode(QAbstractItemView.SelectionMode.ContiguousSelection)
        self.setMinimumHeight(300);self.itemChanged.connect(self.changed)
    def set_cells(self,cells):
        self.raw=dict(cells);self.recalculate();self.setCurrentCell(1,1)
    def values(self):return dict(self.raw)
    def changed(self,item):
        if self.loading:return
        val=item.text();ref=address(item.row()+1,item.column()+1)
        if val=='':self.raw.pop(ref,None)
        else:
            try:val=float(val) if '.' in val else int(val)
            except ValueError:pass
            self.raw[ref]=val
        self.recalculate();self.edited.emit()
    def set_value(self,ref,value):self.raw[ref]=value;self.recalculate();self.edited.emit()
    def recalculate(self):
        self.loading=True
        try:
            engine=Engine(self.raw)
            for r in range(self.rowCount()):
                for c in range(self.columnCount()):
                    ref=address(r+1,c+1);value=self.raw.get(ref);display='' if value is None else str(value)
                    if isinstance(value,str) and value.startswith('='):
                        try:display=str(engine.cell(ref))
                        except FormulaError:display='#公式错误'
                    if display.endswith('.0'):display=display[:-2]
                    item=self.item(r,c)
                    if item is None:item=QTableWidgetItem();self.setItem(r,c,item)
                    item.setText(display);item.setToolTip(str(value) if value is not None else '')
                    item.setForeground(QColor('#315eaa' if isinstance(value,str) and value.startswith('=') else '#243248'))
                    if r==0:item.setBackground(QColor('#eaf0f8'));item.setFont(QFont('Microsoft YaHei UI',10,QFont.Weight.DemiBold))
        finally:self.loading=False
    def select_data(self):
        self.clearSelection();self.setRangeSelected(QTableWidgetSelectionRange(0,0,4,4),True)
    def data_selected(self):
        return all(self.item(r,c) is not None and self.item(r,c).isSelected() for r in range(5) for c in range(5))
    def sort_scores(self):
        rows=[[self.raw.get(address(r,c)) for c in range(1,6)] for r in range(2,6)]
        try:rows.sort(key=lambda row:float(row[1]),reverse=True)
        except (TypeError,ValueError):raise ValueError('成绩列中有空白或文本，请先填写数值。')
        for r,row in enumerate(rows,2):
            for c,val in enumerate(row,1):self.raw[address(r,c)]=val
        self.recalculate();self.edited.emit()
