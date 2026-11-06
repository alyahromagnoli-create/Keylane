import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from formula import Engine, FormulaError
from content import LESSONS, SHORTCUTS, validate_lesson
from storage import Store

@pytest.mark.parametrize('formula, expected', [
 ('=SUM(B2:B5)',345),('=AVERAGE(B2:B5)',86.25),('=MAX(B2:B5)',92),
 ('=MIN(B2:B5)',78),('=COUNT(B2:B5)',4),('=COUNTA(A2:A6)',4),
 ('=IF(B2>=60,"及格","未及格")','及格'),('=COUNTIF(B2:B5,">=90")',2),
 ('=SUMIF(B2:B5,">=90",B2:B5)',182),('=VLOOKUP("李四",A2:B5,2,FALSE)',92),
 ('=ROUND(2.675,2)',2.68),('=ROUND(-2.5,0)',-3),('=LEFT("AB123",2)','AB'),
 ('=RIGHT("AB123",3)','123'),('=SUM($B$2:$B$5)/COUNT(B2:B5)',86.25),
 ('=IF(TRUE,1,1/0)',1),('=SUM(B2;B3)',177),('=(2+3)*4',20),
 ('=COUNTIF(A2:A5,"张*")',1),('=SUMIF(B2:B5,">=90")',182),
 ('=VLOOKUP(85,B2:C5,2,FALSE)',2),('=1+2*3',7)
])
def test_excel_values(formula,expected):
    cells={'A2':'张三','A3':'李四','A4':'王五','A5':'赵六','B2':85,'B3':92,'B4':78,'B5':90,'C2':2,'C3':3,'C4':1,'C5':4}
    assert Engine(cells).evaluate(formula)==expected

@pytest.mark.parametrize('bad', ['=__import__("os")','=A1.__class__','=SUM(A1:XFD999999)','=1/0','=VLOOKUP("不存在",A2:B5,2,FALSE)','=SUM(', '=UNKNOWN(1)', '=A0', '=IF(1,2)', '=ROUND(1,99999)'])
def test_rejects_invalid_formulas(bad):
    with pytest.raises(FormulaError): Engine({'A2':'张三','B2':85}).evaluate(bad)

def test_cell_formula_and_cycle():
    assert Engine({'A1':2,'B1':'=A1*3'}).evaluate('=B1+1')==7
    with pytest.raises(FormulaError): Engine({'A1':'=B1','B1':'=A1'}).evaluate('=A1')

def test_lessons_are_solvable_and_not_constant_answers():
    assert len(LESSONS)==13
    assert len(SHORTCUTS)==40
    assert sum(s.category=='Windows 常用' for s in SHORTCUTS)==20
    for lesson in LESSONS:
        assert validate_lesson(lesson,lesson.answer,lesson.cells)[0],lesson.name
        assert not validate_lesson(lesson,'=345',lesson.cells)[0]
    lesson=LESSONS[0]
    assert not validate_lesson(lesson,'=SUM(345)',lesson.cells)[0]
    assert validate_lesson(lesson,'=SUM(B2,B3,B4,B5)',lesson.cells)[0]
    cells=dict(lesson.cells); cells['B2']=100
    assert validate_lesson(lesson,lesson.answer,cells)[0]
    assert not validate_lesson(lesson,'=SUM(B2:B4)+90',cells)[0]

def test_store_restart_mistakes_and_backup(tmp_path):
    path=tmp_path/'record.db'; s=Store(path)
    assert s.summary()['attempts']==0
    s.record('shortcut','w_copy',False,1300,'Ctrl+X')
    s.record('shortcut','w_copy',True,900,'Ctrl+C')
    s.record('formula','SUM',True,3000,'=SUM(B2:B5)')
    assert s.summary()['attempts']==3
    assert s.summary()['correct']==2
    assert len(s.mistakes())==1
    backup=tmp_path/'backup.db'; s.backup(backup)
    s.record('formula','SUM',False,50,'=1')
    s.restore(backup)
    assert s.summary()['attempts']==3
    s.close(); s=Store(path)
    assert s.skill_stats()['SUM']['correct']==1
    assert s.skill_stats()['w_copy']['attempts']==2
    s.close()

def test_bad_backup_does_not_destroy_current_data(tmp_path):
    s=Store(tmp_path/'live.db');s.record('formula','SUM',True,100,'ok')
    bad=tmp_path/'bad.db';bad.write_bytes(b'no database')
    with pytest.raises(ValueError): s.restore(bad)
    assert s.summary()['attempts']==1
    s.close()
