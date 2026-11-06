"""Authored lessons; all tables contain synthetic practice data."""
from dataclasses import dataclass
import math
from formula import Engine, Parser, functions, FormulaError

@dataclass(frozen=True)
class Shortcut:
    id:str
    category:str
    title:str
    combo:str
    task:str
    explanation:str
    virtual:bool=False

def shortcut(id,cat,title,combo,task,explanation='',virtual=False):
    return Shortcut(id,cat,title,combo,task,explanation or f'在对应应用中，{combo} 用于{title}。',virtual)

W='Windows 常用';E='Excel 常用'
SHORTCUTS=[
 shortcut('w_copy',W,'复制','Ctrl+C','复制当前选中的文字或数据。'),
 shortcut('w_paste',W,'粘贴','Ctrl+V','将剪贴板内容粘贴到当前位置。'),
 shortcut('w_cut',W,'剪切','Ctrl+X','剪切当前选中的内容。'),
 shortcut('w_undo',W,'撤销','Ctrl+Z','撤销刚才的一步修改。'),
 shortcut('w_redo',W,'重做','Ctrl+Y','恢复刚刚撤销的操作。'),
 shortcut('w_all',W,'全选','Ctrl+A','选中当前文档的全部内容。'),
 shortcut('w_find',W,'查找','Ctrl+F','打开查找，定位需要的文字。'),
 shortcut('w_save',W,'保存','Ctrl+S','保存当前文档。'),
 shortcut('w_new',W,'新建','Ctrl+N','在支持的应用中新建文档或窗口。'),
 shortcut('w_open',W,'打开','Ctrl+O','打开现有文档。'),
 shortcut('w_print',W,'打印','Ctrl+P','打开打印设置。'),
 shortcut('w_rename',W,'重命名','F2','在资源管理器中重命名选中的文件。'),
 shortcut('w_delete',W,'删除','Delete','把选中的文件移到回收站。'),
 shortcut('w_permanent',W,'永久删除','Shift+Delete','跳过回收站，永久删除选中的文件。','Shift+Delete 跳过回收站；训练只在模拟区进行。'),
 shortcut('w_switch',W,'切换窗口','Alt+Tab','切换到另一个已打开的窗口。',virtual=True),
 shortcut('w_desktop',W,'显示桌面','Win+D','快速显示桌面，再按一次恢复窗口。',virtual=True),
 shortcut('w_explorer',W,'资源管理器','Win+E','打开文件资源管理器。',virtual=True),
 shortcut('w_lock',W,'锁定电脑','Win+L','离开座位前锁定电脑。',virtual=True),
 shortcut('w_capture',W,'区域截图','Win+Shift+S','打开系统区域截图。',virtual=True),
 shortcut('w_settings',W,'系统设置','Win+I','打开 Windows 设置。',virtual=True),
 shortcut('e_copy',E,'复制单元格','Ctrl+C','复制 B2 单元格的内容。'),
 shortcut('e_paste',E,'粘贴单元格','Ctrl+V','将已复制的内容粘贴到当前单元格。'),
 shortcut('e_cut',E,'移动内容','Ctrl+X','剪切当前单元格，准备移动内容。'),
 shortcut('e_undo',E,'撤销修改','Ctrl+Z','撤销最近一次表格修改。'),
 shortcut('e_redo',E,'重做修改','Ctrl+Y','重做上一步被撤销的表格修改。'),
 shortcut('e_all',E,'选择数据区域','Ctrl+A','选中当前连续数据区域。'),
 shortcut('e_find',E,'查找数据','Ctrl+F','在表格中查找指定内容。'),
 shortcut('e_replace',E,'替换数据','Ctrl+H','打开查找和替换。'),
 shortcut('e_home',E,'转到首格','Ctrl+Home','快速跳到工作表起始单元格 A1。'),
 shortcut('e_end',E,'转到末格','Ctrl+End','跳到工作表已使用区域的最后一个单元格。'),
 shortcut('e_down',E,'跳到数据底端','Ctrl+Down','跳到当前连续数据区域的底端。'),
 shortcut('e_right',E,'跳到数据右端','Ctrl+Right','跳到当前连续数据区域的右端。'),
 shortcut('e_select_down',E,'选中向下数据','Ctrl+Shift+Down','从当前单元格扩展选区到下方数据边界。'),
 shortcut('e_select_right',E,'选中向右数据','Ctrl+Shift+Right','从当前单元格扩展选区到右侧数据边界。'),
 shortcut('e_column',E,'选择整列','Ctrl+Space','选中当前单元格所在的整列。','某些中文输入法会拦截 Ctrl+Space，可用虚拟键盘练习。'),
 shortcut('e_row',E,'选择整行','Shift+Space','选中当前单元格所在的整行。'),
 shortcut('e_fill_down',E,'向下填充','Ctrl+D','将选区最上方单元格内容向下填充。'),
 shortcut('e_fill_right',E,'向右填充','Ctrl+R','将选区最左侧内容向右填充。'),
 shortcut('e_format',E,'单元格格式','Ctrl+1','打开单元格格式设置。'),
 shortcut('e_filter',E,'开启筛选','Ctrl+Shift+L','为当前数据区域开启或关闭筛选。'),
]

def sample_cells():
    cells={'A1':'姓名','B1':'成绩','C1':'学分','D1':'学号','E1':'班级'}
    rows=[('张三',85,2,'CS202601','一班'),('李四',92,3,'CS202602','二班'),('王五',78,2,'CS202603','一班'),('赵六',90,4,'CS202604','二班')]
    for r,row in enumerate(rows,2):
        for c,v in enumerate(row):cells[f'{chr(65+c)}{r}']=v
    return cells

@dataclass
class Lesson:
    name:str
    group:str
    title:str
    task:str
    syntax:str
    explanation:str
    answer:str
    cells:dict

def lesson(name,group,title,task,syntax,explanation,answer):
    return Lesson(name,group,title,task,syntax,explanation,answer,sample_cells())

LESSONS=[
 lesson('SUM','基础计算','区域求和','计算 B2:B5 四名同学的成绩总和。','SUM(数值1, [数值2], …)','用冒号表示连续区域。SUM 会忽略区域中的文本；若成绩被保存成文本，需先改为数值。','=SUM(B2:B5)'),
 lesson('AVERAGE','基础计算','计算平均分','计算 B2:B5 的平均成绩。','AVERAGE(数值1, [数值2], …)','平均值 = 数值总和 ÷ 数值个数。空白和区域内文本不计入分母，0 会计入。','=AVERAGE(B2:B5)'),
 lesson('MAX','统计','寻找最高分','找出 B2:B5 的最高成绩。','MAX(数值1, [数值2], …)','MAX 返回数值区域的最大值。注意最高分与取得最高分的姓名是两个不同任务。','=MAX(B2:B5)'),
 lesson('MIN','统计','寻找最低分','找出 B2:B5 的最低成绩。','MIN(数值1, [数值2], …)','MIN 返回数值区域的最小值。0 是有效数值，空白会被忽略。','=MIN(B2:B5)'),
 lesson('COUNT','统计','数值计数','统计 B2:B5 中有多少个数值成绩。','COUNT(值1, [值2], …)','COUNT 只统计数值，不统计文本姓名或空白。用它核对有成绩的学生人数。','=COUNT(B2:B5)'),
 lesson('COUNTA','统计','非空计数','统计 A2:A5 中有多少个已填写的姓名。','COUNTA(值1, [值2], …)','COUNTA 统计非空单元格，文字也会计数。公式返回的空字符串也算非空。','=COUNTA(A2:A5)'),
 lesson('IF','条件判断','判断是否及格','判断 B2 是否至少为 60 分，输出“及格”或“未及格”。','IF(条件, 条件成立时的值, 条件不成立时的值)','比较运算可以使用 >=、<=、=、<>。输出文字要使用英文双引号。','=IF(B2>=60,"及格","未及格")'),
 lesson('COUNTIF','条件统计','统计高分人数','统计 B2:B5 中成绩 >=90 的人数。','COUNTIF(条件区域, 条件)','比较符号与数字放在同一个英文双引号字符串里，例如 ">=90"。','=COUNTIF(B2:B5,">=90")'),
 lesson('SUMIF','条件统计','按班级汇总','计算一班同学的成绩总和，班级在 E2:E5，成绩在 B2:B5。','SUMIF(条件区域, 条件, [求和区域])','先在条件区域找到符合条件的行，再汇总求和区域的对应数值。两个区域大小要一致。','=SUMIF(E2:E5,"一班",B2:B5)'),
 lesson('VLOOKUP','查找','按姓名查成绩','在 A2:B5 查找李四，返回第二列的成绩，使用精确匹配。','VLOOKUP(查找值, 表格区域, 返回列序号, FALSE)','查找值必须位于表格区域的第一列。列序号从该区域第一列开始数，FALSE 表示精确匹配。','=VLOOKUP("李四",A2:B5,2,FALSE)'),
 lesson('ROUND','数值处理','保留一位小数','将 B2:B5 的平均成绩四舍五入到一位小数。','ROUND(数值, 保留位数)','第二个参数是小数位数。ROUND 会改变计算结果；单元格显示格式只改变外观。','=ROUND(AVERAGE(B2:B5),1)'),
 lesson('LEFT','文本处理','提取学号前缀','从 D2 学号左边提取 2 个字符。','LEFT(文本, [字符数])','用于截取编码前缀。字符数省略时默认取 1 个。','=LEFT(D2,2)'),
 lesson('RIGHT','文本处理','提取学号尾号','从 D2 学号右边提取 3 个字符。','RIGHT(文本, [字符数])','结果仍然是文本，因此尾号 001 的前导 0 会保留。','=RIGHT(D2,3)'),
]

def same(a,b):
    if isinstance(a,(int,float)) and not isinstance(a,bool) and isinstance(b,(int,float)) and not isinstance(b,bool):return math.isclose(a,b,rel_tol=1e-8,abs_tol=1e-8)
    return type(a)==type(b) and a==b

def variants(cells):
    yield dict(cells)
    for n in (1,2):
        probe=dict(cells)
        changes={1:{'B2':51,'B3':99,'B4':67,'B5':72,'D2':'AB812345','E2':'二班','E3':'一班','E4':'一班','E5':'二班'},2:{'B2':93,'B3':64,'B4':88,'B5':97,'D2':'XY450076','A4':None,'E2':'一班','E3':'二班','E4':'二班','E5':'一班'}}[n]
        probe.update(changes)
        if n==2:probe['B4']=None
        yield probe

def validate_lesson(lesson,formula,cells):
    try:
        used=functions(Parser(formula).parse())
        if lesson.name not in used:return False,f'这题请使用 {lesson.name} 函数完成。'
        actual=Engine(cells).evaluate(formula)
        for probe in variants(cells):
            if not same(Engine(probe).evaluate(formula),Engine(probe).evaluate(lesson.answer)):
                return False,f'当前计算结果：{actual}。请检查引用范围和条件；公式也需要在数据变化后成立。'
        return True,f'计算正确：{actual}。公式已通过原表与变化数据的校验。'
    except FormulaError as exc:return False,str(exc)

SKILL_NAMES={s.id:s.title for s in SHORTCUTS}|{l.name:l.name for l in LESSONS}|{'challenge:grades':'班级成绩挑战'}

def mastery(stat):
    if not stat or not stat['attempts']:return '尚未练习',0
    n=stat['attempts'];success=stat['independent'];score=round(success/n*100)
    if success>=3 and score>=80:return '熟练',score
    return '正在学习',score
