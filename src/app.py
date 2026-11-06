"""Keylane desktop application shell and learning overview."""
from pathlib import Path
import csv
from PySide6.QtCore import Qt,QEvent
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QMainWindow,QWidget,QFrame,QLabel,QPushButton,QVBoxLayout,QHBoxLayout,QGridLayout,QStackedWidget,QScrollArea,QApplication,QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,QLineEdit,QComboBox,QFileDialog,QMessageBox,QProgressBar)
from widgets import STYLE,label,button,panel,combo_from_event
from training import ShortcutPage,FormulaPage,ChallengePage
from storage import Store
from content import SHORTCUTS,LESSONS,SKILL_NAMES,mastery

class Dashboard(QWidget):
    def __init__(self,host):
        super().__init__();self.host=host
        v=QVBoxLayout(self);v.setSpacing(22);v.addWidget(label('把操作练熟，把时间省下来。','title'));v.addWidget(label('Keylane  /  键径 · 键盘效率训练','subtitle'))
        h=QHBoxLayout();h.setSpacing(16);self.metrics={}
        for name,title in [('today','今日练习'),('accuracy','累计正确率'),('mastered','熟练技能'),('reaction','按键反应')]:
            p,l=panel();n=label('—','number');self.metrics[name]=n;l.addWidget(n);l.addWidget(label(title,'subtitle'));h.addWidget(p)
        v.addLayout(h)
        p,l=panel();l.addWidget(label('今天从这里开始','section'));l.addWidget(label('先用键盘完成一个动作，再用公式解决一个问题。','task'))
        l.addWidget(label('按键训练有 40 项，函数实验有 13 种。你可以按顺序学习，也可以随时切换到需要练习的技能。','subtitle'))
        h=QHBoxLayout();h.addWidget(button('开始快捷键训练',lambda:host.navigate(1),True));h.addWidget(button('进入函数实验',lambda:host.navigate(2)));h.addStretch();l.addLayout(h);v.addWidget(p)
        h=QHBoxLayout();h.setSpacing(18)
        p,l=panel();l.addWidget(label('技能进度','section'));self.progress={}
        for title,total in [('Windows 常用',20),('Excel 常用',20),('Excel 函数',13)]:
            line=QHBoxLayout();line.addWidget(label(title),1);n=label(f'0 / {total}','subtitle');line.addWidget(n);l.addLayout(line)
            bar=QProgressBar();bar.setRange(0,total);bar.setValue(0);bar.setTextVisible(False);l.addWidget(bar);self.progress[title]=(n,bar,total)
        l.addWidget(label('完成至少一次正确练习计入进度；熟练需要至少 3 次独立正确，且独立正确次数占总作答的 80% 以上。','subtitle'));h.addWidget(p,1)
        p,l=panel();l.addWidget(label('把单项技能连起来','section'));l.addWidget(label('班级成绩表整理','task'));l.addWidget(label('选区 → 排序 → 总分 → 平均分 → 及格判断 → 人数统计。可以自由练习，也可以限时完成。','subtitle'))
        l.addStretch();l.addWidget(button('进入实战挑战',lambda:host.navigate(3)));h.addWidget(p,1);v.addLayout(h)
        p,l=panel();l.addWidget(label('记录属于你','section'));self.note=label('','subtitle');l.addWidget(self.note);v.addWidget(p);v.addStretch()
    def refresh(self):
        s=self.host.store.summary();stats=self.host.store.skill_stats()
        self.metrics['today'].setText(str(s['today']));self.metrics['accuracy'].setText(f"{s['correct']/s['attempts']*100:.0f}%" if s['attempts'] else '—')
        mastered=sum(mastery(stats.get(k))[0]=='熟练' for k in SKILL_NAMES if not k.startswith('challenge:'))
        self.metrics['mastered'].setText(f'{mastered} / 53');self.metrics['reaction'].setText(f"{s['reaction']/1000:.2f} s" if s['reaction'] else '—')
        for title,(n,bar,total) in self.progress.items():
            ids=[s.id for s in SHORTCUTS if s.category==title] if title!='Excel 函数' else [l.name for l in LESSONS]
            count=sum(stats.get(k,{}).get('correct',0)>0 for k in ids);n.setText(f'{count} / {total}');bar.setValue(count)
        self.note.setText(f"已学习 {s['days']} 天，累计作答 {s['attempts']} 次。真实按键、虚拟键盘与提示练习均有标记；提示练习不计入独立熟练。\n离线记录：{self.host.store.path}")

class GrowthPage(QWidget):
    def __init__(self,host):
        super().__init__();self.host=host
        v=QVBoxLayout(self);v.setSpacing(18);v.addWidget(label('我的成长','title'));v.addWidget(label('从实际练习记录看见进步。双击技能或错题，可以直接回到训练。','subtitle'))
        h=QHBoxLayout();self.search=QLineEdit();self.search.setPlaceholderText('搜索技能、函数或组合键');self.search.textChanged.connect(self.refresh);h.addWidget(self.search,1)
        self.filter=QComboBox();self.filter.addItems(['全部技能','尚未练习','正在学习','熟练']);self.filter.currentTextChanged.connect(self.refresh);h.addWidget(self.filter);v.addLayout(h)
        p,l=panel();l.addWidget(label('技能熟练度地图','section'));self.map=QTableWidget(0,6);self.map.setHorizontalHeaderLabels(['技能','分类 / 组合键','状态','正确 / 作答','独立正确率','平均用时'])
        self.map.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);self.map.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows);self.map.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers);self.map.setMinimumHeight(310);self.map.cellDoubleClicked.connect(self.map_review);l.addWidget(self.map)
        l.addWidget(label('“熟练”标准：至少 3 次独立正确，且独立正确次数 / 总作答次数 ≥80%。平均用时仅统计独立正确作答；虚拟和提示练习不计入。','subtitle'));v.addWidget(p)
        p,l=panel();l.addWidget(label('历史错题 · 双击复习','section'));self.errors=QTableWidget(0,3);self.errors.setHorizontalHeaderLabels(['技能','错误次数','最近错误时间']);self.errors.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);self.errors.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers);self.errors.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows);self.errors.setMinimumHeight(170);self.errors.cellDoubleClicked.connect(self.error_review);l.addWidget(self.errors);self.empty=label('还没有错题记录。','subtitle');l.addWidget(self.empty);v.addWidget(p)
        p,l=panel();l.addWidget(label('最近 14 个学习日','section'));self.history=label('暂无学习记录。','subtitle');l.addWidget(self.history)
        h=QHBoxLayout();h.addWidget(button('备份学习记录',self.backup));h.addWidget(button('恢复备份',self.restore));h.addWidget(button('导出练习记录 CSV',self.export));h.addStretch();l.addLayout(h);v.addWidget(p);v.addStretch()
    def refresh(self,*args):
        stats=self.host.store.skill_stats();query=self.search.text().strip().casefold();selected=self.filter.currentText();rows=[]
        entries=[(s.id,s.title,s.category+' · '+s.combo,'shortcut') for s in SHORTCUTS]+[(l.name,l.name,l.group,'formula') for l in LESSONS]
        for key,name,category,mode in entries:
            stat=stats.get(key);status,score=mastery(stat)
            if query and query not in (name+' '+category).casefold():continue
            if selected!='全部技能' and selected!=status:continue
            rows.append((key,mode,[name,category,status,f"{stat['correct']} / {stat['attempts']}" if stat else '0 / 0',f'{score}%' if stat else '—',f"{stat['elapsed']/1000:.2f} s" if stat and stat['elapsed'] is not None else '—']))
        self.map.setRowCount(len(rows));self.map_rows=rows
        for r,(_,_,values) in enumerate(rows):
            for c,value in enumerate(values):self.map.setItem(r,c,QTableWidgetItem(value))
        self.error_rows=self.host.store.mistakes();self.errors.setRowCount(len(self.error_rows));self.empty.setVisible(not self.error_rows)
        for r,item in enumerate(self.error_rows):
            for c,value in enumerate([SKILL_NAMES.get(item['skill'],item['skill']),str(item['errors']),item['latest'].replace('T',' ')]):self.errors.setItem(r,c,QTableWidgetItem(value))
        days=self.host.store.daily();self.history.setText('\n'.join(f"{d['day']}   {d['attempts']} 次作答 · {d['correct']} 次正确" for d in days) if days else '暂无学习记录。')
    def review_skill(self,mode,key):
        if mode=='shortcut':self.host.navigate(1);self.host.shortcut.load_skill(key)
        elif mode=='formula':
            self.host.navigate(2);self.host.formula.choose(next(i for i,l in enumerate(LESSONS) if l.name==key))
        else:self.host.navigate(3)
    def map_review(self,row,column):
        key,mode,_=self.map_rows[row];self.review_skill(mode,key)
    def error_review(self,row,column):
        item=self.error_rows[row];self.review_skill(item['mode'],item['skill'])
    def file_path(self,save,title,filename,filter):
        options=QFileDialog.Option.DontUseNativeDialog
        if save:return QFileDialog.getSaveFileName(self,title,str(self.host.store.path.parent/filename),filter,options=options)[0]
        return QFileDialog.getOpenFileName(self,title,str(self.host.store.path.parent),filter,options=options)[0]
    def backup(self):
        path=self.file_path(True,'备份学习记录','Keylane-backup.db','数据库 (*.db)')
        if path:
            try:self.host.store.backup(path);QMessageBox.information(self,'备份完成',f'已保存到：\n{path}')
            except Exception as exc:QMessageBox.warning(self,'备份失败',str(exc))
    def restore(self):
        path=self.file_path(False,'选择 Keylane 备份','','数据库 (*.db)')
        if not path:return
        if QMessageBox.question(self,'恢复学习记录','将用所选备份替换当前学习记录。当前数据会先自动备份为 before-restore.db。继续？')!=QMessageBox.StandardButton.Yes:return
        try:
            self.host.store.restore(path);self.host.refresh_stats();QMessageBox.information(self,'恢复完成','学习记录已恢复。')
        except Exception as exc:QMessageBox.warning(self,'无法恢复',str(exc))
    def export(self):
        path=self.file_path(True,'导出练习记录','Keylane-records.csv','CSV (*.csv)')
        if not path:return
        try:
            with open(path,'w',newline='',encoding='utf-8-sig') as f:
                writer=csv.writer(f);writer.writerow(['时间','模块','技能','正确','用时毫秒','作答','提示或虚拟练习'])
                for r in self.host.store.db.execute('SELECT * FROM attempts ORDER BY id'):
                    # Protect Excel against formula injection in exported user input.
                    answer=r['answer'];answer="'"+answer if answer.startswith(('=','+','-','@','\t','\r')) else answer
                    writer.writerow([r['created'],r['mode'],SKILL_NAMES.get(r['skill'],r['skill']),r['correct'],r['elapsed'],answer,r['assisted']])
            QMessageBox.information(self,'导出完成',f'已保存到：\n{path}')
        except OSError as exc:QMessageBox.warning(self,'导出失败',str(exc))

class MainWindow(QMainWindow):
    def __init__(self,data_path):
        super().__init__();self.store=Store(data_path);self.app_active=True;self.setWindowTitle('Keylane · 键径 · 键盘效率训练');self.resize(1400,980);self.setMinimumSize(1000,700)
        self.setStyleSheet(STYLE)
        icon=Path(__file__).resolve().parent/'resources'/'Keylane.ico'
        if icon.exists():self.setWindowIcon(QIcon(str(icon)))
        root=QWidget();root.setObjectName('root');self.setCentralWidget(root);h=QHBoxLayout(root);h.setContentsMargins(0,0,0,0);h.setSpacing(0)
        side=QFrame();side.setObjectName('sidebar');side.setFixedWidth(212);v=QVBoxLayout(side);v.setContentsMargins(18,28,18,24);v.setSpacing(9)
        mark=QLabel();mark.setFixedSize(48,48)
        if icon.exists():mark.setPixmap(QIcon(str(icon)).pixmap(48,48))
        v.addWidget(mark);v.addWidget(label('Keylane','brand'));v.addWidget(label('键径 · 键盘效率训练','sideNote'));v.addSpacing(30)
        self.nav=[]
        for i,title in enumerate(['首页','快捷键训练','Excel 函数','实战挑战','我的成长']):
            b=QPushButton(title);b.setObjectName('nav');b.setCheckable(True);b.clicked.connect(lambda checked=False,n=i:self.navigate(n));v.addWidget(b);self.nav.append(b)
        v.addStretch();v.addWidget(label('本地学习记录\nWindows 便携版 1.0.2','sideNote'));h.addWidget(side)
        self.stack=QStackedWidget();h.addWidget(self.stack,1)
        self.dashboard=Dashboard(self);self.shortcut=ShortcutPage(self);self.formula=FormulaPage(self);self.challenge=ChallengePage(self);self.growth=GrowthPage(self)
        self.pages=[self.dashboard,self.shortcut,self.formula,self.challenge,self.growth]
        for page in self.pages:
            scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(page);page.layout().setContentsMargins(32,28,32,28);self.stack.addWidget(scroll)
        self.navigate(0);QApplication.instance().installEventFilter(self)
    def navigate(self,i):
        if not hasattr(self,'pages'):return
        for n,page in enumerate(self.pages):
            if hasattr(page,'on_active'):page.on_active(n==i and self.app_active)
        self.stack.setCurrentIndex(i)
        for n,b in enumerate(self.nav):b.setChecked(n==i)
        self.refresh_stats()
    def refresh_stats(self):
        if hasattr(self,'growth'):self.dashboard.refresh();self.growth.refresh()
    def eventFilter(self,obj,event):
        typ=event.type()
        if typ in (QEvent.Type.ApplicationDeactivate,QEvent.Type.ApplicationActivate):
            self.app_active=typ==QEvent.Type.ApplicationActivate
            for n,p in enumerate(self.pages):
                if hasattr(p,'on_active'):p.on_active(n==self.stack.currentIndex() and self.app_active)
        if typ not in (QEvent.Type.KeyPress,QEvent.Type.KeyRelease,QEvent.Type.ShortcutOverride):return False
        if not isinstance(obj,QWidget) or obj.window() is not self:return False
        index=self.stack.currentIndex()
        modifiers=event.modifiers() & ~Qt.KeyboardModifier.KeypadModifier
        if index==1 and modifiers==Qt.KeyboardModifier.NoModifier and event.key() in (Qt.Key.Key_Space,Qt.Key.Key_Return,Qt.Key.Key_Enter):
            # Consume both press and release, so a focused button cannot fire twice.
            if typ==QEvent.Type.ShortcutOverride:event.accept();return True
            if typ==QEvent.Type.KeyPress and not event.isAutoRepeat():
                if event.key()==Qt.Key.Key_Space and self.shortcut.start_button.isEnabled():self.shortcut.start()
                elif event.key()!=Qt.Key.Key_Space and self.shortcut.next_button.isEnabled():self.shortcut.next_skill()
            return True
        if typ==QEvent.Type.KeyRelease:return False
        if event.isAutoRepeat():return self.stack.currentIndex()==1 and self.shortcut.armed
        combo=combo_from_event(event)
        if not combo:return False
        if index==1 and self.shortcut.armed:
            # No global hotkeys. Only process combinations delivered to our window.
            modified='+' in combo;standalone=combo in ('F2','Delete')
            if not modified and not standalone:return False
            if typ==QEvent.Type.ShortcutOverride:event.accept();return True
            self.shortcut.submit(combo);return True
        if index==3 and self.challenge.running and combo=='Ctrl+A' and self.challenge.step<=1 and not self.challenge.input.hasFocus():
            if typ==QEvent.Type.ShortcutOverride:event.accept();return True
            return self.challenge.handle_combo(combo)
        return False
    def closeEvent(self,event):
        QApplication.instance().removeEventFilter(self)
        for p in self.pages:
            if hasattr(p,'timer'):p.timer.stop()
        self.store.close();event.accept()
