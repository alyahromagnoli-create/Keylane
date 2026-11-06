"""Shortcut, formula, and integrated challenge controllers."""
from PySide6.QtCore import Qt,QEvent,QTimer
from PySide6.QtWidgets import (QWidget,QLabel,QVBoxLayout,QHBoxLayout,QComboBox,QLineEdit,QListWidget,QAbstractItemView,QApplication)
from widgets import label,button,panel,Keyboard,Grid,Clock,combo_from_event
from content import SHORTCUTS,LESSONS,sample_cells,validate_lesson,Lesson

class ShortcutPage(QWidget):
    def __init__(self,host):
        super().__init__();self.host=host;self.armed=False;self.solved=False;self.clock=Clock();self.hinted=False;self.queue=list(SHORTCUTS);self.index=0
        v=QVBoxLayout(self);v.setSpacing(18)
        v.addWidget(label('快捷键训练','title'));v.addWidget(label('空格：开始／暂停接收按键；Enter：答对后进入下一题。组合键中的空格照常作答。','subtitle'))
        h=QHBoxLayout();self.category=QComboBox();self.category.addItems(['全部分类','Windows 常用','Excel 常用']);self.category.currentTextChanged.connect(self.filter_category)
        self.pick=QComboBox();self.pick.setMinimumContentsLength(12);self.pick.currentIndexChanged.connect(self.pick_changed)
        h.addWidget(self.category);h.addWidget(self.pick,1);v.addLayout(h)
        p,l=panel();self.position=label('','subtitle');l.addWidget(self.position);self.task=label('','task');l.addWidget(self.task)
        self.mode=label('','subtitle');l.addWidget(self.mode)
        h=QHBoxLayout();self.start_button=button('开始接收按键 [空格]',self.start,True);h.addWidget(self.start_button);self.hint=button('查看提示',self.show_hint);h.addWidget(self.hint)
        self.next_button=button('下一题 [Enter]',self.next_skill);self.next_button.setEnabled(False);h.addWidget(self.next_button);h.addStretch()
        self.time=label('0.0 秒','subtitle');h.addWidget(self.time);l.addLayout(h)
        self.feedback=label('按空格或点击“开始接收按键”后，在本窗口按组合键。','feedback');l.addWidget(self.feedback);v.addWidget(p)
        p,l=panel();l.addWidget(label('键盘反馈','section'));self.keyboard=Keyboard();self.keyboard.submitted.connect(lambda combo:self.submit(combo,True));l.addWidget(self.keyboard);v.addWidget(p)
        p,l=panel();l.addWidget(label('操作预览 · 模拟数据','section'));self.sandbox=label('','subtitle');l.addWidget(self.sandbox)
        self.grid=Grid(5,5);self.grid.setMinimumHeight(190);self.grid.setMaximumHeight(210);self.grid.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers);l.addWidget(self.grid);v.addWidget(p);v.addStretch()
        self.timer=QTimer(self);self.timer.timeout.connect(lambda:self.time.setText(f'{self.clock.ms()/1000:.1f} 秒'));self.timer.start(100)
        self.refill_pick();self.load(self.queue[0])
    def refill_pick(self):
        self.pick.blockSignals(True);self.pick.clear()
        for s in self.queue:self.pick.addItem(s.title,s.id)
        self.pick.blockSignals(False)
    def filter_category(self,category):
        self.queue=[s for s in SHORTCUTS if category=='全部分类' or s.category==category];self.refill_pick();self.index=0;self.load(self.queue[0])
    def pick_changed(self,i):
        if 0<=i<len(self.queue):self.index=i;self.load(self.queue[i])
    def load_skill(self,skill):
        s=next((s for s in SHORTCUTS if s.id==skill),SHORTCUTS[0])
        self.category.blockSignals(True);self.category.setCurrentIndex(0);self.category.blockSignals(False);self.queue=list(SHORTCUTS);self.refill_pick();self.index=self.queue.index(s)
        self.pick.blockSignals(True);self.pick.setCurrentIndex(self.index);self.pick.blockSignals(False);self.load(s)
    def load(self,skill):
        self.current=skill;self.armed=False;self.solved=False;self.hinted=False;self.clock.reset();self.keyboard.clear()
        self.position.setText(f'{skill.category}   /   {self.index+1:02d} / {len(self.queue):02d}')
        self.task.setText(skill.task);self.grid.set_cells(sample_cells());self.grid.setCurrentCell(1,1)
        self.mode.setText('系统组合：请使用下方虚拟键盘提交；不会触发系统操作。' if skill.virtual else '支持真实按键；也可点击虚拟键盘，虚拟练习单独标记。')
        self.feedback.setText('按空格或点击“开始接收按键”后作答。');self.sandbox.setText('选中 B2 = 85；本页操作不会修改电脑上的文件。')
        self.start_button.setText('开始接收按键 [空格]');self.start_button.setEnabled(True);self.next_button.setEnabled(False);self.time.setText('0.0 秒')
        if skill.id.endswith('paste'):self.grid.setCurrentCell(2,1);self.sandbox.setText('训练剪贴板已有 85；请粘贴到 B3。')
    def start(self):
        if self.solved:return
        self.armed=not self.armed
        if self.armed:self.clock.resume();self.setFocus()
        else:self.clock.pause()
        self.start_button.setText('暂停接收按键 [空格]' if self.armed else '继续接收按键 [空格]')
        self.feedback.setText('正在接收按键。虚拟组合请点击键帽后提交。' if self.armed else '已暂停。点击“继续接收按键”后作答。')
    def show_hint(self):
        self.hinted=True;self.feedback.setText(f'提示：{self.current.combo}\n{self.current.explanation}');self.keyboard.show_keys(self.current.combo.split('+'))
    def submit(self,combo,virtual=False):
        if not self.armed or self.solved:return
        if self.current.virtual and not virtual:
            self.feedback.setText('这道系统组合题请用虚拟键盘提交。');return
        parts=combo.split('+');expected=self.current.combo.split('+')
        self.keyboard.show_keys(parts);correct=parts[-1]==expected[-1] and set(parts[:-1])==set(expected[:-1])
        assisted=virtual or self.hinted
        self.host.store.record('shortcut',self.current.id,correct,self.clock.ms(),combo,assisted)
        if correct:
            self.clock.pause();self.armed=False;self.solved=True;self.start_button.setText('本题已完成');self.start_button.setEnabled(False);self.next_button.setEnabled(True)
            tag='虚拟键盘' if virtual else ('提示练习' if self.hinted else '真实按键')
            self.feedback.setText(f'正确 · {combo} · {self.clock.ms()/1000:.2f} 秒 · {tag}\n{self.current.explanation}')
            self.apply_preview()
        else:
            self.hinted=True;self.feedback.setText(f'收到：{combo}。正确组合：{self.current.combo}\n{self.current.explanation}\n请再试一次；本题后续将标为提示练习。')
        self.host.refresh_stats()
    def apply_preview(self):
        key=self.current.id
        if key.endswith('paste'):self.grid.set_value('B3',85);msg='已粘贴：B3 = 85。'
        elif key.endswith('copy'):msg='已复制：训练剪贴板 = 85。'
        elif key.endswith('cut'):self.grid.set_value('B2',None);msg='已剪切：B2 清空，训练剪贴板 = 85。'
        elif key.endswith('all'):self.grid.select_data();msg='已选中 A1:E5 数据区域。'
        elif key.endswith('home'):self.grid.setCurrentCell(0,0);msg='当前位置：A1。'
        elif key.endswith('end'):self.grid.setCurrentCell(4,4);msg='当前位置：E5。'
        elif key.endswith('select_down'):
            from PySide6.QtWidgets import QTableWidgetSelectionRange
            self.grid.clearSelection();self.grid.setRangeSelected(QTableWidgetSelectionRange(1,1,4,1),True);msg='已扩展选区至 B2:B5。'
        elif key.endswith('select_right'):
            from PySide6.QtWidgets import QTableWidgetSelectionRange
            self.grid.clearSelection();self.grid.setRangeSelected(QTableWidgetSelectionRange(1,1,1,4),True);msg='已扩展选区至 B2:E2。'
        elif key.endswith('column'):self.grid.selectColumn(1);msg='已选中 B 列。'
        elif key.endswith('row'):self.grid.selectRow(1);msg='已选中第 2 行。'
        elif key.endswith('fill_down'):
            for r in range(3,6):self.grid.set_value(f'B{r}',85)
            msg='向下填充结果：B2:B5 均为 85（模拟预选区域）。'
        elif key.endswith('fill_right'):
            for c in 'CDE':self.grid.set_value(f'{c}2',85)
            msg='向右填充结果：B2:E2 均为 85（模拟预选区域）。'
        elif key=='e_down':self.grid.setCurrentCell(4,1);msg='已跳至 B5。'
        elif key=='e_right':self.grid.setCurrentCell(1,4);msg='已跳至 E2。'
        else:msg=f'已识别“{self.current.title}”。这是 {self.current.category} 的场景模拟反馈。'
        self.sandbox.setText(msg)
    def next_skill(self):
        self.index=(self.index+1)%len(self.queue);self.pick.setCurrentIndex(self.index)
        if len(self.queue)==1:self.load(self.queue[0])
    def on_active(self,active):
        if active and self.armed:self.clock.resume()
        else:self.clock.pause()

class FormulaPage(QWidget):
    def __init__(self,host):
        super().__init__();self.host=host;self.clock=Clock();self.solved=False;self.hinted=False;self.active=False
        v=QVBoxLayout(self);v.setSpacing(18);v.addWidget(label('Excel 函数实验','title'));v.addWidget(label('理解参数，输入公式，再用变化的数据验证思路。表内均为模拟练习数据。','subtitle'))
        h=QHBoxLayout();h.setSpacing(18);self.list=QListWidget();self.list.setFixedWidth(180)
        for l in LESSONS:self.list.addItem(f'{l.name}\n{l.group} · {l.title}')
        self.list.currentRowChanged.connect(self.choose);h.addWidget(self.list)
        right=QWidget();r=QVBoxLayout(right);r.setContentsMargins(0,0,0,0);r.setSpacing(16)
        p,l=panel();self.title=label('','section');l.addWidget(self.title);self.task=label('','task');l.addWidget(self.task);self.syntax=label('','subtitle');l.addWidget(self.syntax);self.explanation=label('');l.addWidget(self.explanation);r.addWidget(p)
        p,l=panel();top=QHBoxLayout();top.addWidget(label('练习工作表','section'),1);top.addWidget(button('重置数据',self.reset_data));l.addLayout(top)
        self.grid=Grid();self.grid.edited.connect(self.invalidate);l.addWidget(self.grid)
        l.addWidget(label('结果写入 F8。可双击编辑输入数据；公式区域支持本页 13 种函数。','subtitle'))
        f=QHBoxLayout();f.addWidget(label('fx'));self.input=QLineEdit();self.input.setPlaceholderText('输入以 = 开头的公式，按 Enter 检查');self.input.setObjectName('formulaInput');self.input.returnPressed.connect(self.check);self.input.textChanged.connect(self.formula_changed);f.addWidget(self.input,1)
        self.check_button=button('检查公式',self.check,True);f.addWidget(self.check_button);l.addLayout(f)
        self.feedback=label('','feedback');l.addWidget(self.feedback)
        f=QHBoxLayout();self.hint_button=button('查看答案与解析',self.show_answer);f.addWidget(self.hint_button);f.addStretch();self.next_button=button('下一函数',self.next_lesson);f.addWidget(self.next_button);l.addLayout(f);r.addWidget(p);r.addStretch()
        h.addWidget(right,1);v.addLayout(h);self.list.setCurrentRow(0)
    def choose(self,i):
        if not 0<=i<len(LESSONS):return
        if self.list.currentRow()!=i:
            self.list.setCurrentRow(i);return
        self.current=LESSONS[i];self.title.setText(f'{i+1:02d}  /  {self.current.name}  ·  {self.current.title}');self.task.setText(self.current.task)
        self.syntax.setText(self.current.syntax);self.explanation.setText(self.current.explanation)
        self.hinted=False;self.solved=False;self.input.clear();self.grid.set_cells(self.current.cells);self.feedback.setText('先读任务，再输入公式。也可以修改表内数据，观察计算是否随之变化。')
        self.clock.reset()
        if self.active:self.clock.resume()
        self.check_button.setEnabled(True)
    def formula_changed(self):
        if self.solved:
            self.clock.reset()
            if self.active:self.clock.resume()
        self.solved=False;self.check_button.setEnabled(True)
    def invalidate(self):
        if self.solved:
            self.clock.reset()
            if self.active:self.clock.resume()
        self.solved=False;self.check_button.setEnabled(True)
    def reset_data(self):self.grid.set_cells(self.current.cells);self.invalidate();self.feedback.setText('已恢复原始练习数据。')
    def check(self):
        if self.solved:return
        formula=self.input.text().strip();cells=self.grid.values();cells.pop('F8',None)
        if not formula:self.feedback.setText('请输入公式。');return
        correct,msg=validate_lesson(self.current,formula,cells)
        self.host.store.record('formula',self.current.name,correct,self.clock.ms(),formula,self.hinted)
        if correct:
            self.grid.set_value('F8',formula);self.solved=True;self.check_button.setEnabled(False);self.clock.pause()
            if self.hinted:msg+=' 本次为答案提示后的练习。'
        self.feedback.setText(('正确 · ' if correct else '再检查一下 · ')+msg);self.host.refresh_stats()
    def show_answer(self):
        self.hinted=True;self.feedback.setText(f'参考公式：{self.current.answer}\n{self.current.explanation}\n看过答案后仍需自己输入；本次记录会标记为提示练习。')
    def next_lesson(self):self.list.setCurrentRow((self.list.currentRow()+1)%len(LESSONS))
    def on_active(self,active):
        self.active=active
        if active and not self.solved:self.clock.resume()
        else:self.clock.pause()

class ChallengePage(QWidget):
    TASKS=[
      '选中 A1:E5 整个数据区域。可以按 Ctrl+A，或拖动选择。',
      '使用“成绩降序”按钮，将整张数据表按成绩从高到低排列。',
      '使用 SUM，计算 B2:B5 的成绩总和，结果写入 F2。',
      '使用 AVERAGE，计算 B2:B5 的平均成绩，结果写入 F3。',
      '使用 IF 判断排序后 B2 是否 >=60，输出“及格”或“未及格”，写入 F4。',
      '使用 COUNTIF，统计 B2:B5 中成绩 >=60 的人数，写入 F5。',
    ]
    def __init__(self,host):
        super().__init__();self.host=host;self.step=0;self.finished=False;self.running=False;self.active=False;self.clock=Clock();self.step_clock=Clock();self.tries=0;self.correct_steps=0;self.key_count=0
        v=QVBoxLayout(self);v.setSpacing(18);v.addWidget(label('综合实战挑战','title'));v.addWidget(label('整理班级成绩表 · 6 个连续任务，把快捷键与函数用在同一张表上。','subtitle'))
        p,l=panel();self.status=label('准备开始','section');l.addWidget(self.status);self.task=label('点击“开始挑战”，按步骤完成选区、排序和公式计算。','task');l.addWidget(self.task)
        h=QHBoxLayout();self.begin_button=button('开始挑战',self.begin,True);h.addWidget(self.begin_button);self.limit=QComboBox();self.limit.addItems(['不限时','限时 3 分钟','限时 5 分钟']);h.addWidget(self.limit);h.addStretch();self.time=label('00:00','section');h.addWidget(self.time);l.addLayout(h);v.addWidget(p)
        p,l=panel();h=QHBoxLayout();h.addWidget(label('工作表 · 合成成绩数据','section'),1);self.select_button=button('选择数据区域',self.select_all);h.addWidget(self.select_button);self.sort_button=button('成绩降序',self.sort_scores);h.addWidget(self.sort_button);l.addLayout(h)
        self.grid=Grid(8,6);self.grid.set_cells(sample_cells());self.grid.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers);l.addWidget(self.grid)
        h=QHBoxLayout();h.addWidget(label('fx'));self.input=QLineEdit();self.input.setPlaceholderText('轮到公式任务时，在这里输入公式');self.input.returnPressed.connect(self.check);h.addWidget(self.input,1);self.verify=button('验证当前步骤',self.check,True);h.addWidget(self.verify);l.addLayout(h)
        self.feedback=label('按顺序验证每一步。切换页面或离开应用时暂停计时。','feedback');l.addWidget(self.feedback);v.addWidget(p)
        self.report=label('尚无本轮成绩。完成挑战后显示用时、正确率与快捷键使用次数。','subtitle');v.addWidget(self.report);v.addStretch()
        self.timer=QTimer(self);self.timer.timeout.connect(self.tick);self.timer.start(200);self.set_controls(False)
    def set_controls(self,enabled):
        for widget in (self.input,self.verify,self.select_button,self.sort_button):widget.setEnabled(enabled)
    def begin(self):
        self.step=0;self.finished=False;self.running=True;self.tries=0;self.correct_steps=0;self.key_count=0;self.grid.set_cells(sample_cells());self.input.clear();self.clock.reset()
        if self.active:self.clock.resume()
        self.limit.setEnabled(False);self.limit_ms=[0,180000,300000][self.limit.currentIndex()];self.begin_button.setText('重新开始');self.set_controls(True)
        self.feedback.setText('挑战已开始。每一步都要点击“验证当前步骤”。');self.report.setText('本轮快捷键使用 0 次。');self.show_step()
    def show_step(self):
        self.status.setText(f'第 {self.step+1} / 6 步');self.task.setText(self.TASKS[self.step]);self.input.setEnabled(self.step>=2);self.input.clear()
        self.step_clock.reset()
        if self.active:self.step_clock.resume()
        if self.step>=2:self.input.setFocus()
    def select_all(self):
        if self.running:self.grid.select_data()
    def sort_scores(self):
        if not self.running:return
        if self.step!=1:self.feedback.setText('先完成当前步骤，再进行排序。');return
        if not self.grid.data_selected():self.feedback.setText('先选中 A1:E5，再按成绩降序排列。');return
        try:self.grid.sort_scores();self.feedback.setText('已按成绩降序排列，并保持每行姓名与数据的对应关系。')
        except ValueError as e:self.feedback.setText(str(e))
    def check(self):
        if not self.running or self.finished:return
        self.tick()
        if not self.running:return
        self.tries+=1;correct=False;msg=''
        if self.step==0:
            correct=self.grid.data_selected();msg='需要选中完整的 A1:E5，包含表头。'
        elif self.step==1:
            correct=[self.grid.raw.get(f'B{r}') for r in range(2,6)]==[92,90,85,78];msg='尚未完成降序排序，请点击“成绩降序”。'
        else:
            answers=[('SUM','=SUM(B2:B5)'),('AVERAGE','=AVERAGE(B2:B5)'),('IF','=IF(B2>=60,"及格","未及格")'),('COUNTIF','=COUNTIF(B2:B5,">=60")')]
            name,answer=answers[self.step-2];l=Lesson(name,'','','','','',answer,self.grid.values())
            correct,msg=validate_lesson(l,self.input.text().strip(),self.grid.values())
            self.host.store.record('formula',name,correct,self.step_clock.ms(),self.input.text().strip())
            self.host.refresh_stats()
            if correct:self.grid.set_value(f'F{self.step}',self.input.text().strip())
        if not correct:
            self.feedback.setText('未通过 · '+msg);return
        self.correct_steps+=1;self.step+=1
        if self.step==6:
            self.clock.pause();self.step_clock.pause();self.finished=True;self.running=False;self.set_controls(False);self.limit.setEnabled(True)
            rate=round(100*self.correct_steps/self.tries);self.status.setText('挑战完成');self.task.setText('已完成班级成绩表整理。');self.feedback.setText('选择、排序、SUM、AVERAGE、IF、COUNTIF 六步均已通过。')
            self.report.setText(f'完成用时 {self.clock.ms()/1000:.1f} 秒  ·  步骤正确率 {rate}%（6 / {self.tries}）  ·  快捷键使用 {self.key_count} 次\n函数：SUM、AVERAGE、IF、COUNTIF 均通过；成长页可查看本轮记录。')
            self.host.store.record('challenge','challenge:grades',True,self.clock.ms(),f'6/{self.tries}; shortcuts={self.key_count}');self.host.refresh_stats()
        else:self.feedback.setText('上一步已通过。继续完成下一项任务。');self.show_step()
    def handle_combo(self,combo):
        if not self.running:return False
        # Only intercept on the worksheet; formula text keeps normal edit shortcuts.
        if combo=='Ctrl+A' and self.step<=1 and not self.input.hasFocus():
            self.select_all();self.key_count+=1;self.report.setText(f'本轮快捷键使用 {self.key_count} 次。');return True
        return False
    def tick(self):
        ms=self.clock.ms();seconds=ms//1000
        self.time.setText(f'{seconds//60:02d}:{seconds%60:02d}')
        if self.running and self.limit_ms:
            self.time.setText(f'剩余 {max(0,(self.limit_ms-ms)//1000)} 秒')
            if ms>=self.limit_ms:
                self.clock.pause();self.step_clock.pause();self.running=False;self.set_controls(False);self.limit.setEnabled(True);self.status.setText('本轮时间结束');self.task.setText(f'已完成 {self.step} / 6 步，重新开始再试一次。')
                self.host.store.record('challenge','challenge:grades',False,ms,f'timeout step={self.step}');self.host.refresh_stats()
    def on_active(self,active):
        self.active=active
        if active and self.running:self.clock.resume();self.step_clock.resume()
        else:self.clock.pause();self.step_clock.pause()
