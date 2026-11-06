import os,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt
from app import MainWindow
from content import LESSONS
from content import SHORTCUTS

@pytest.fixture(scope='module')
def qt():
    return QApplication.instance() or QApplication([])

@pytest.fixture
def win(qt,tmp_path):
    w=MainWindow(tmp_path/'learning.db');w.show();qt.processEvents()
    yield w
    w.close();qt.processEvents()

def test_real_shortcut_error_then_success(win,qt):
    win.navigate(1);p=win.shortcut;p.load_skill('w_copy');p.start()
    QTest.keyClick(p,Qt.Key.Key_X,Qt.KeyboardModifier.ControlModifier)
    assert win.store.summary()['correct']==0
    assert win.store.summary()['attempts']==1
    assert 'Ctrl+C' in p.feedback.text()
    QTest.keyClick(p,Qt.Key.Key_C,Qt.KeyboardModifier.ControlModifier)
    assert win.store.summary()['correct']==1
    assert not p.armed
    assert '复制' in p.sandbox.text()

def test_virtual_system_shortcut(win):
    win.navigate(1);p=win.shortcut;p.load_skill('w_lock');p.start()
    p.keyboard.click_key('Win');p.keyboard.click_key('L');p.keyboard.submit.click()
    assert win.store.summary()['correct']==1
    assert win.store.recent()[0]['assisted']==1

def test_all_formulas_in_ui(win,qt):
    win.navigate(2);p=win.formula
    for i,l in enumerate(LESSONS):
        p.choose(i);p.input.setText(l.answer);p.check_button.click();qt.processEvents()
        assert p.solved,l.name
    assert win.store.summary()['correct']==13

def test_challenge_needs_actions_and_finishes(win,qt):
    win.navigate(3);p=win.challenge;p.begin()
    p.verify.click();assert p.step==0
    p.select_all();p.verify.click();assert p.step==1
    p.sort_scores();p.verify.click();assert p.step==2
    for formula in ('=SUM(B2:B5)','=AVERAGE(B2:B5)','=IF(B2>=60,"及格","未及格")','=COUNTIF(B2:B5,">=60")'):
        p.input.setText(formula);p.verify.click();qt.processEvents()
    assert p.finished
    assert '完成' in p.status.text()
    assert win.store.skill_stats()['challenge:grades']['correct']==1

def test_review_routes_to_mistake(win):
    win.store.record('formula','IF',False,1000,'=3')
    win.navigate(4);win.growth.review_skill('formula','IF')
    assert win.stack.currentIndex()==2
    assert win.formula.current.name=='IF'

def test_small_window_pages_do_not_crash(win,qt):
    win.resize(1000,700)
    for i in range(5):win.navigate(i);qt.processEvents()
    assert win.isVisible()

def test_formula_timer_restarts_when_editing_solved_answer(win):
    win.navigate(2);p=win.formula;p.choose(0);p.input.setText('=SUM(B2:B5)');p.check()
    assert p.clock.started is None
    p.input.setText('=SUM(B2,B3,B4,B5)')
    assert p.clock.started is not None

def test_challenge_updates_function_skills(win):
    win.navigate(3);p=win.challenge;p.begin();p.select_all();p.check();p.sort_scores();p.check()
    p.input.setText('=SUM(B2:B5)');p.check()
    assert win.store.skill_stats()['SUM']['correct']==1

def test_all_40_shortcut_event_or_virtual_routes(win,qt):
    win.navigate(1);p=win.shortcut
    special={'Space':Qt.Key.Key_Space,'Home':Qt.Key.Key_Home,'End':Qt.Key.Key_End,'Delete':Qt.Key.Key_Delete,'Down':Qt.Key.Key_Down,'Right':Qt.Key.Key_Right,'F2':Qt.Key.Key_F2}
    for skill in SHORTCUTS:
        p.load_skill(skill.id);p.start()
        if skill.virtual:
            for key in skill.combo.split('+'):p.keyboard.click_key(key)
            p.keyboard.submit.click()
        else:
            bits=skill.combo.split('+');mods=Qt.KeyboardModifier.NoModifier
            for m in bits[:-1]:mods|={'Ctrl':Qt.KeyboardModifier.ControlModifier,'Shift':Qt.KeyboardModifier.ShiftModifier,'Alt':Qt.KeyboardModifier.AltModifier}[m]
            last=bits[-1];key=special[last] if last in special else getattr(Qt.Key,'Key_'+last)
            QTest.keyClick(p,key,mods)
        assert p.solved,skill.id
    assert win.store.summary()['correct']==40

def test_challenge_timeout_and_navigation_pause(win):
    win.navigate(3);p=win.challenge;p.limit.setCurrentIndex(1);p.begin()
    win.navigate(0);assert p.clock.started is None
    win.navigate(3);p.clock.total=181;p.tick()
    assert not p.running
    assert win.store.skill_stats()['challenge:grades']['correct']==0

def test_space_starts_pauses_and_enter_advances_only_after_correct(win):
    win.navigate(1);p=win.shortcut;p.load_skill('w_copy')
    p.hint.setFocus()
    QTest.keyClick(p.hint,Qt.Key.Key_Space)
    assert p.armed
    assert win.store.summary()['attempts']==0
    QTest.keyClick(p,Qt.Key.Key_Return)
    assert p.current.id=='w_copy' and p.armed
    QTest.keyClick(p,Qt.Key.Key_Space)
    assert not p.armed
    QTest.keyClick(p,Qt.Key.Key_Space)
    QTest.keyClick(p,Qt.Key.Key_C,Qt.KeyboardModifier.ControlModifier)
    assert p.solved
    QTest.keyClick(p,Qt.Key.Key_Space)
    assert p.solved and not p.armed
    QTest.keyClick(p,Qt.Key.Key_Return)
    assert p.current.id=='w_paste' and not p.armed
    QTest.keyClick(p,Qt.Key.Key_Space)
    assert p.armed

def test_modified_space_still_answers_and_keypad_enter_advances(win):
    win.navigate(1);p=win.shortcut;p.load_skill('e_row');p.start()
    QTest.keyClick(p,Qt.Key.Key_Space,Qt.KeyboardModifier.ShiftModifier)
    assert p.solved
    QTest.keyClick(p,Qt.Key.Key_Enter,Qt.KeyboardModifier.KeypadModifier)
    assert p.current.id=='e_fill_down'

def test_space_auto_repeat_does_not_toggle(win):
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtCore import QEvent
    win.navigate(1);p=win.shortcut;p.load_skill('w_copy')
    event=QKeyEvent(QEvent.Type.KeyPress,Qt.Key.Key_Space,Qt.KeyboardModifier.NoModifier,' ',True,1)
    QApplication.sendEvent(p,event)
    assert not p.armed
