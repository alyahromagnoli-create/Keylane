"""Local learning history and validated SQLite backups."""
import sqlite3
from pathlib import Path
from datetime import datetime

SCHEMA='CREATE TABLE IF NOT EXISTS attempts (id INTEGER PRIMARY KEY, created TEXT NOT NULL, day TEXT NOT NULL, mode TEXT NOT NULL, skill TEXT NOT NULL, correct INTEGER NOT NULL, elapsed INTEGER NOT NULL, answer TEXT NOT NULL, assisted INTEGER NOT NULL DEFAULT 0)'

class Store:
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(self.path);self.db.row_factory=sqlite3.Row
        self.db.execute(SCHEMA);self.db.execute('PRAGMA user_version=1');self.db.commit()
    def record(self,mode,skill,correct,elapsed,answer,assisted=False):
        now=datetime.now()
        self.db.execute('INSERT INTO attempts(created,day,mode,skill,correct,elapsed,answer,assisted) VALUES(?,?,?,?,?,?,?,?)',(now.isoformat(timespec='seconds'),now.date().isoformat(),mode,skill,int(correct),max(0,int(elapsed)),str(answer)[:1000],int(assisted)))
        self.db.commit()
    def summary(self):
        row=dict(self.db.execute('SELECT COUNT(*) attempts, COALESCE(SUM(correct),0) correct, COUNT(DISTINCT day) days, COALESCE(AVG(CASE WHEN correct=1 AND mode="shortcut" AND assisted=0 THEN elapsed END),0) reaction FROM attempts').fetchone())
        row['today']=self.db.execute('SELECT COUNT(*) FROM attempts WHERE day=?',(datetime.now().date().isoformat(),)).fetchone()[0]
        return row
    def skill_stats(self):
        return {r['skill']:dict(r) for r in self.db.execute('SELECT skill, COUNT(*) attempts, SUM(correct) correct, SUM(CASE WHEN correct=1 AND assisted=0 THEN 1 ELSE 0 END) independent, AVG(CASE WHEN correct=1 AND assisted=0 THEN elapsed END) elapsed FROM attempts GROUP BY skill')}
    def mistakes(self):
        return [dict(r) for r in self.db.execute('SELECT skill,mode,COUNT(*) errors,MAX(created) latest FROM attempts WHERE correct=0 GROUP BY mode,skill ORDER BY latest DESC')]
    def recent(self):
        return [dict(r) for r in self.db.execute('SELECT * FROM attempts ORDER BY id DESC LIMIT 100')]
    def daily(self):
        return [dict(r) for r in self.db.execute('SELECT day,COUNT(*) attempts,SUM(correct) correct FROM attempts GROUP BY day ORDER BY day DESC LIMIT 14')]
    def backup(self,target):
        target=Path(target)
        if target.resolve()==self.path.resolve():raise ValueError('备份文件不能覆盖当前数据库。')
        target.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(target) as out:self.db.backup(out)
    def restore(self,source):
        source=Path(source)
        if source.resolve()==self.path.resolve():raise ValueError('请选择另一个备份文件。')
        if not source.is_file():raise ValueError('备份文件不存在。')
        try:
            check=sqlite3.connect(source.resolve().as_uri()+'?mode=ro',uri=True)
            try:
                if check.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('数据库不完整。')
                cols=[r[1] for r in check.execute('PRAGMA table_info(attempts)')]
                expected=['id','created','day','mode','skill','correct','elapsed','answer','assisted']
                if cols!=expected or check.execute('PRAGMA user_version').fetchone()[0]!=1:raise ValueError('不是兼容的 Keylane 备份。')
                for r in check.execute('SELECT * FROM attempts'):
                    if r[3] not in ('shortcut','formula','challenge') or r[5] not in (0,1) or not isinstance(r[6],int) or r[6]<0 or r[8] not in (0,1):raise ValueError('备份记录内容无效。')
                # Keep a recoverable snapshot before a valid replacement.
                self.backup(self.path.with_name('before-restore.db'))
                self.db.commit();check.backup(self.db);self.db.commit()
            finally:check.close()
        except (sqlite3.Error,OSError) as exc:raise ValueError('无法读取备份，当前记录已保留。') from exc
    def close(self):self.db.close()
