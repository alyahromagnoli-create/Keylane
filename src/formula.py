"""Small, bounded Excel-like expression evaluator. No Python eval or I/O."""
import re
import math
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from dataclasses import dataclass

class FormulaError(ValueError):
    pass

@dataclass
class Area:
    rows: list
    def flat(self):
        return [v for row in self.rows for v in row]

TOKEN = re.compile(r'\s*(?:(\d+(?:\.\d*)?|\.\d+)|("(?:[^"]|"")*")|(\$?[A-Za-z]{1,3}\$?[0-9]+)|([A-Za-z_][A-Za-z_0-9]*)|(>=|<=|<>|[+*/^&=<>():,;\-]))')

def coord(ref):
    m=re.fullmatch(r'([A-Z]{1,3})([1-9][0-9]*)',ref.replace('$','').upper())
    if not m: raise FormulaError('单元格地址无效，例如 B2。')
    col=0
    for ch in m[1]:col=col*26+ord(ch)-64
    row=int(m[2])
    if row>1000 or col>100:raise FormulaError('练习范围限于 A1:CV1000。')
    return row,col

def address(row,col):
    name=''
    while col:col,d=divmod(col-1,26);name=chr(65+d)+name
    return f'{name}{row}'

class Parser:
    def __init__(self,text):
        if not isinstance(text,str) or not text.strip().startswith('='):raise FormulaError('公式须以 = 开头。')
        text=text.strip()[1:].strip()
        if len(text)>1000:raise FormulaError('公式过长，最多 1000 个字符。')
        self.tokens=[];i=0
        while i<len(text):
            m=TOKEN.match(text,i)
            if not m:raise FormulaError(f'无法识别第 {i+2} 个字符，请检查引号和运算符。')
            self.tokens.append(next(v for v in m.groups() if v is not None));i=m.end()
        self.tokens.append('<END>');self.i=0;self.depth=0
    def peek(self):return self.tokens[self.i]
    def pop(self):t=self.peek();self.i+=1;return t
    def expect(self,t):
        if self.pop()!=t:raise FormulaError(f'此处需要 {t}。')
    def parse(self):
        node=self.expr(0)
        if self.peek()!='<END>':raise FormulaError('公式末尾有多余内容。')
        return node
    def expr(self,min_prec):
        self.depth+=1
        if self.depth>40:raise FormulaError('嵌套层数过多。')
        t=self.pop()
        if t in ('+','-'):left=('unary',t,self.expr(5))
        elif t=='(':
            left=self.expr(0);self.expect(')')
        elif t.startswith('"'):left=('value',t[1:-1].replace('""','"'))
        elif re.fullmatch(r'\d+(\.\d*)?|\.\d+',t):left=('value',float(t) if '.' in t else int(t))
        elif re.fullmatch(r'\$?[A-Za-z]{1,3}\$?[0-9]+',t):
            coord(t);left=('ref',t.replace('$','').upper())
            if self.peek()==':':
                self.pop();end=self.pop();coord(end);left=('range',left[1],end.replace('$','').upper())
        elif t.upper() in ('TRUE','FALSE'):left=('value',t.upper()=='TRUE')
        elif re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*',t):
            self.expect('(');args=[]
            if self.peek()!=')':
                while True:
                    args.append(self.expr(0))
                    if self.peek() not in (',',';'):break
                    self.pop()
            self.expect(')');left=('fn',t.upper(),args)
        else:raise FormulaError('缺少参数、单元格或括号。')
        prec={'=':1,'<>':1,'>':1,'<':1,'>=':1,'<=':1,'&':2,'+':3,'-':3,'*':4,'/':4,'^':5}
        while self.peek() in prec and prec[self.peek()]>=min_prec:
            op=self.pop();right=self.expr(prec[op]+1);left=('op',op,left,right)
        self.depth-=1
        return left

def functions(node):
    if node[0]=='fn':return {node[1]}.union(*(functions(n) for n in node[2]))
    if node[0]=='op':return functions(node[2])|functions(node[3])
    if node[0]=='unary':return functions(node[2])
    return set()

def scalar(value):
    if isinstance(value,Area):
        vals=value.flat()
        if len(vals)!=1:raise FormulaError('此处需要单个值，不能使用整片区域。')
        return vals[0]
    return value

def number(value):
    value=scalar(value)
    if value is None or value=='':return 0
    if isinstance(value,(int,float)):return value
    try:return float(value)
    except (ValueError,TypeError):raise FormulaError('需要数值，但遇到了文本。')

def text(value):
    value=scalar(value)
    if value is None:return ''
    if isinstance(value,bool):return 'TRUE' if value else 'FALSE'
    if isinstance(value,float) and value.is_integer():return str(int(value))
    return str(value)

def compare(a,b,op):
    a,b=scalar(a),scalar(b)
    if isinstance(a,str) and isinstance(b,str):a,b=a.casefold(),b.casefold()
    if a is None:a=0 if isinstance(b,(float,int)) else ''
    if b is None:b=0 if isinstance(a,(float,int)) else ''
    try:
        if op=='=':return a==b
        if op=='<>':return a!=b
        if op=='>':return a>b
        if op=='<':return a<b
        if op=='>=':return a>=b
        return a<=b
    except TypeError:raise FormulaError('比较条件的类型不一致。')

def matches(value,criterion):
    if not isinstance(criterion,str):return compare(value,criterion,'=')
    m=re.match(r'^(>=|<=|<>|>|<|=)?(.*)$',criterion);op=m[1] or '=';target=m[2]
    try:target=float(target)
    except ValueError:pass
    if isinstance(target,float):
        if not isinstance(value,(float,int)):return False
        return compare(value,target,op)
    if op in ('=','<>'):
        pattern='';i=0
        while i<len(target):
            ch=target[i]
            if ch=='~' and i+1<len(target):i+=1;pattern+=re.escape(target[i])
            elif ch=='*':pattern+='.*'
            elif ch=='?':pattern+='.'
            else:pattern+=re.escape(ch)
            i+=1
        yes=re.fullmatch(pattern,text(value),flags=re.I) is not None
        return yes if op=='=' else not yes
    return compare(value,target,op)

class Engine:
    def __init__(self,cells):
        self.cells={str(k).upper():v for k,v in cells.items()};self.visiting=set();self.cache={};self.steps=0
    def evaluate(self,formula):
        try:
            result=scalar(self.run(Parser(formula).parse()))
            if isinstance(result,(float,int)) and not math.isfinite(result):raise FormulaError('数值超出范围。')
            return result
        except FormulaError:raise
        except (ValueError,TypeError,OverflowError,ZeroDivisionError,RecursionError,InvalidOperation):
            raise FormulaError('无法计算：检查数值、除数和参数范围。')
    def cell(self,ref):
        if ref in self.cache:return self.cache[ref]
        if ref in self.visiting:raise FormulaError('检测到循环引用。')
        if len(self.visiting)>30:raise FormulaError('引用层数过多。')
        value=self.cells.get(ref)
        if isinstance(value,str) and value.startswith('='):
            self.visiting.add(ref)
            try:value=self.evaluate(value)
            finally:self.visiting.remove(ref)
        self.cache[ref]=value
        return value
    def run(self,node):
        self.steps+=1
        if self.steps>10000:raise FormulaError('计算步骤过多。')
        kind=node[0]
        if kind=='value':return node[1]
        if kind=='ref':return self.cell(node[1])
        if kind=='range':
            r1,c1=coord(node[1]);r2,c2=coord(node[2])
            r1,r2=sorted((r1,r2));c1,c2=sorted((c1,c2))
            if (r2-r1+1)*(c2-c1+1)>2000:raise FormulaError('一次最多计算 2000 个单元格。')
            return Area([[self.cell(address(r,c)) for c in range(c1,c2+1)] for r in range(r1,r2+1)])
        if kind=='unary':return number(self.run(node[2]))*(1 if node[1]=='+' else -1)
        if kind=='op':
            a,b=self.run(node[2]),self.run(node[3]);op=node[1]
            if op in ('=','<>','>','<','>=','<='):return compare(a,b,op)
            if op=='&':return text(a)+text(b)
            a,b=number(a),number(b)
            if op=='+':return a+b
            if op=='-':return a-b
            if op=='*':return a*b
            if op=='/':
                if b==0:raise FormulaError('除数不能为 0。')
                return a/b
            if abs(b)>100 or abs(a)>1e100:raise FormulaError('幂运算超出练习范围。')
            return a**b
        name,args=node[1],node[2]
        arities={'SUM':(1,50),'AVERAGE':(1,50),'MAX':(1,50),'MIN':(1,50),'COUNT':(1,50),'COUNTA':(1,50),'IF':(3,3),'COUNTIF':(2,2),'SUMIF':(2,3),'VLOOKUP':(3,4),'ROUND':(2,2),'LEFT':(1,2),'RIGHT':(1,2)}
        if name not in arities:raise FormulaError(f'暂不支持函数 {name}。')
        low,high=arities[name]
        if not low<=len(args)<=high:raise FormulaError(f'{name} 参数数量不正确。')
        if name=='IF':return self.run(args[1] if bool(scalar(self.run(args[0]))) else args[2])
        vals=[self.run(a) for a in args]
        if name in ('SUM','AVERAGE','MAX','MIN','COUNT','COUNTA'):
            flat=[]
            for v in vals:flat.extend(v.flat() if isinstance(v,Area) else [v])
            nums=[v for v in flat if isinstance(v,(int,float)) and not isinstance(v,bool)]
            if name=='COUNTA':return sum(v is not None for v in flat)
            if name=='COUNT':return len(nums)
            if name=='SUM':return sum(nums)
            if name=='AVERAGE':
                if not nums:raise FormulaError('AVERAGE 的区域内没有数值。')
                return sum(nums)/len(nums)
            if name=='MAX':return max(nums,default=0)
            return min(nums,default=0)
        if name in ('COUNTIF','SUMIF'):
            if not isinstance(vals[0],Area):raise FormulaError('条件统计的第一个参数需要区域。')
            source=vals[0].flat();crit=scalar(vals[1])
            if name=='COUNTIF':return sum(matches(v,crit) for v in source)
            sums=vals[2] if len(vals)==3 else vals[0]
            if not isinstance(sums,Area) or len(sums.rows)!=len(vals[0].rows) or len(sums.rows[0])!=len(vals[0].rows[0]):raise FormulaError('条件区域和求和区域大小须一致。')
            return sum(v for k,v in zip(source,sums.flat()) if isinstance(v,(float,int)) and not isinstance(v,bool) and matches(k,crit))
        if name=='ROUND':
            n=number(vals[0]);digits=int(number(vals[1]))
            if not -10<=digits<=10:raise FormulaError('ROUND 保留位数限 -10 到 10。')
            return float(Decimal(str(n)).quantize(Decimal('1').scaleb(-digits),rounding=ROUND_HALF_UP))
        if name in ('LEFT','RIGHT'):
            s=text(vals[0]);n=int(number(vals[1])) if len(vals)==2 else 1
            if n<0:raise FormulaError('截取字符数不能为负。')
            return s[:n] if name=='LEFT' else (s[-n:] if n else '')
        lookup,area,index=scalar(vals[0]),vals[1],number(vals[2])
        if not isinstance(area,Area):raise FormulaError('VLOOKUP 第二个参数需要表格区域。')
        if index!=int(index) or not 1<=index<=len(area.rows[0]):raise FormulaError('查找列序号超出表格范围。')
        approx=scalar(vals[3]) if len(vals)==4 else True
        if not isinstance(approx,(bool,int,float)):raise FormulaError('最后一个参数使用 FALSE 或 TRUE。')
        if not approx:
            for row in area.rows:
                if matches(row[0],lookup):return row[int(index)-1]
        else:
            keys=[row[0] for row in area.rows]
            try:
                if keys!=sorted(keys):raise FormulaError('近似查找要求首列升序，请排序或使用 FALSE。')
                candidates=[row for row in area.rows if row[0]<=lookup]
            except TypeError:raise FormulaError('近似查找的类型不一致。')
            if candidates:return candidates[-1][int(index)-1]
        raise FormulaError('未找到匹配值，请检查首列和查找内容。')
