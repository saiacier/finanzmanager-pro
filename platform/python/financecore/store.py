# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Samuele Timoteo Iacierno
"""Local SQLite database of FinanzManager (storage protocol 1, schema 1, docs/STORAGE-PROTOCOL.md).

Port of the former FinanceStore.swift. Databases written by the Swift app (1.2.x) open
unchanged; checks, limits and messages are the same.
"""
from datetime import datetime
from pathlib import Path
import json,math,os,re,sqlite3,uuid

SCHEMA=1
APPLICATION_ID=1179471954
COLLECTIONS=['transactions','categories','dashboards','goals','balanceSnapshots']
LIMITS={'transactions':150000,'categories':3000,'dashboards':20,'goals':100,'balanceSnapshots':20000}
DATE=re.compile(r'\d{4}-\d{2}-\d{2}')

class FinanceFailure(ValueError):
    """Error whose text is shown to the user."""

def canonical(value):
    """Sorted keys, no whitespace, UTF-8 text."""
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)

def cents(amount):
    """Euro amount to cents, rounding half away from zero like the Swift app."""
    scaled=amount*100
    return int(math.floor(scaled+0.5)) if scaled>=0 else -int(math.floor(-scaled+0.5))

def number(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)

def valid_date(text):
    if not isinstance(text,str) or not DATE.fullmatch(text):return False
    try:return datetime.strptime(text,'%Y-%m-%d').strftime('%Y-%m-%d')==text
    except ValueError:return False

def private(path,mode):
    try:os.chmod(path,mode)
    except OSError:pass

def export_allowed(destination,active_file):
    """Exports may not replace the active database or its journal files."""
    target=os.path.realpath(os.path.abspath(destination))
    protected=os.path.realpath(os.path.abspath(active_file))
    return not target.startswith(protected)

class FinanceStore:
    def __init__(self,file,read_only=False):
        self.file=Path(os.path.abspath(file));self.read_only=read_only
        if self.file.is_symlink():raise FinanceFailure('Verknüpfte Datenbankdateien werden nicht geöffnet.')
        exists=self.file.exists()
        if not read_only:
            self.file.parent.mkdir(parents=True,exist_ok=True);private(self.file.parent,0o700)
        elif not exists:raise FinanceFailure('Sicherung fehlt.')
        mode='ro' if read_only else 'rwc'
        try:self.db=sqlite3.connect(self.file.as_uri()+'?mode='+mode,uri=True,timeout=4,isolation_level=None,check_same_thread=False)
        except sqlite3.Error as e:raise FinanceFailure(str(e)) from None
        try:
            version=self.integer('PRAGMA user_version')
            if version>SCHEMA:raise FinanceFailure('Diese Datenbank stammt aus einer neueren App-Version. Sie wird nicht verändert.')
            identity=self.integer('PRAGMA application_id')
            if exists:
                if identity!=APPLICATION_ID or version!=SCHEMA:raise FinanceFailure('Keine unterstützte FinanzManager-Datenbank.')
            else:
                self.execute('BEGIN EXCLUSIVE')
                try:
                    self.execute('CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)')
                    self.execute('CREATE TABLE records(collection TEXT NOT NULL,key TEXT NOT NULL,position INTEGER NOT NULL,payload TEXT NOT NULL,amount_cents INTEGER,PRIMARY KEY(collection,key))')
                    self.execute('PRAGMA application_id=%d'%APPLICATION_ID)
                    self.execute('PRAGMA user_version=1')
                    self.execute("INSERT INTO metadata VALUES('revision','0')")
                    self.execute('COMMIT')
                except BaseException:
                    self.rollback();raise
            if self.strings('PRAGMA quick_check')!=['ok']:raise FinanceFailure('Die Datenbankprüfung ist fehlgeschlagen. Bitte eine Sicherung wiederherstellen.')
            if not read_only:
                self.execute('PRAGMA synchronous=FULL')
                self.execute('PRAGMA journal_mode=DELETE')
                private(self.file,0o600)
        except BaseException:
            self.db.close();raise
    # ---------- SQLite ----------
    def execute(self,query,args=()):
        try:self.db.execute(query,tuple(args)).fetchall()
        except sqlite3.Error as e:raise FinanceFailure(str(e)) from None
    def strings(self,query,args=()):
        try:return ['' if row[0] is None else str(row[0]) for row in self.db.execute(query,tuple(args)).fetchall()]
        except sqlite3.Error as e:raise FinanceFailure(str(e)) from None
    def integer(self,query):
        found=self.strings(query)
        try:return int(found[0]) if found else 0
        except ValueError:return 0
    def rollback(self):
        try:self.db.execute('ROLLBACK')
        except sqlite3.Error:pass
    def metadata(self,key):
        found=self.strings('SELECT value FROM metadata WHERE key=?',[key]);return found[0] if found else None
    @property
    def revision(self):
        text=self.metadata('revision')
        if text is None or not text.isdigit():raise FinanceFailure('Ungültige Datenbankrevision.')
        return int(text)
    def close(self):self.db.close()
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
    # ---------- data ----------
    def load(self):
        prefs=self.metadata('preferences')
        if prefs is None:
            if self.revision!=0 or self.integer('SELECT COUNT(*) FROM records')!=0:raise FinanceFailure('Unvollständiger Datenbestand: Einstellungen fehlen.')
            return None
        try:state=json.loads(prefs)
        except ValueError:raise FinanceFailure('Einstellungen unlesbar.') from None
        if not isinstance(state,dict):raise FinanceFailure('Einstellungen unlesbar.')
        for kind in COLLECTIONS:
            state[kind]=[json.loads(payload) for payload in self.strings('SELECT payload FROM records WHERE collection=? ORDER BY position',[kind])]
        self.validated(state)
        stored=self.strings("SELECT amount_cents FROM records WHERE collection='transactions' ORDER BY position")
        for row,exact in zip(state['transactions'],stored):
            if not number(row.get('amount')) or not exact.lstrip('-').isdigit() or cents(row['amount'])!=int(exact):raise FinanceFailure('Inkonsistenter Centbetrag in der Datenbank.')
        return state
    def validated(self,state):
        """Rows (collection, key, position, payload, cents) of a complete, checked state."""
        def rows_of(kind):
            value=state.get(kind)
            return isinstance(value,list) and all(isinstance(row,dict) for row in value)
        if not rows_of('transactions') or not rows_of('categories'):raise FinanceFailure('Buchungen oder Kategorien fehlen.')
        records=[]
        for kind in sorted(LIMITS):
            if kind in state and not rows_of(kind):raise FinanceFailure('Ungültige Sammlung: '+kind)
            values=state.get(kind) or []
            if len(values)>LIMITS[kind]:raise FinanceFailure('Zu viele Datensätze: '+kind)
            seen=set()
            for index,original in enumerate(values):
                row=dict(original);amount=None
                if kind=='balanceSnapshots':
                    account,date=row.get('account'),row.get('date')
                    if not isinstance(account,str) or not account or not valid_date(date) or not number(row.get('amount')) or not number(row.get('dayTotal')):raise FinanceFailure('Ungültige Bankreferenz.')
                    key=canonical([account,date])
                else:
                    key=row.get('id')
                    if not isinstance(key,str) or not key:raise FinanceFailure('Datensatz ohne Kennung: '+kind)
                if key in seen:raise FinanceFailure('Doppelte Datensatzkennung in '+kind)
                seen.add(key)
                if kind=='transactions':
                    description=row.get('description')
                    if not valid_date(row.get('date')) or not isinstance(description,str) or not description or not number(row.get('amount')) or abs(row['amount'])>9_000_000_000_000:raise FinanceFailure('Ungültige Buchung.')
                    amount=cents(row['amount']);row['amount']=amount/100
                records.append((kind,key,index,canonical(row),amount))
        return records
    def save(self,state,expected_revision,reason='edit',legacy_source=None):
        if self.read_only:raise FinanceFailure('Sicherung ist schreibgeschützt.')
        if not isinstance(state,dict):raise FinanceFailure('Ungültiger Speicherauftrag.')
        rows=self.validated(state)
        if self.revision!=expected_revision:raise FinanceFailure('Der Bestand wurde in einem anderen Fenster geändert. Bitte vor weiteren Änderungen neu laden.')
        if reason=='restore' and self.load() is not None:self.recovery_backup('vor-wiederherstellung')
        legacy_file=None
        if legacy_source is not None:
            if self.load() is not None:raise FinanceFailure('Eine vorhandene Datenbank wird nicht durch WebView-Daten überschrieben.')
            folder=self.backup_folder()
            legacy_file=folder/('webview-original-'+str(uuid.uuid4()).upper()+'.json')
            legacy_file.write_text(legacy_source,encoding='utf-8');private(legacy_file,0o600)
        prefs={key:value for key,value in state.items() if key not in COLLECTIONS}
        self.execute('BEGIN IMMEDIATE')
        try:
            if self.revision!=expected_revision:raise FinanceFailure('Gleichzeitige Änderung erkannt.')
            if legacy_source is not None and self.load() is not None:raise FinanceFailure('Datenbank inzwischen befüllt.')
            self.execute('DELETE FROM records')
            for kind,key,index,payload,amount in rows:self.execute('INSERT INTO records VALUES(?,?,?,?,?)',[kind,key,index,payload,amount])
            self.execute("INSERT OR REPLACE INTO metadata VALUES('preferences',?)",[canonical(prefs)])
            self.execute("UPDATE metadata SET value=? WHERE key='revision'",[str(expected_revision+1)])
            if legacy_file:self.execute("INSERT OR REPLACE INTO metadata VALUES('legacy_backup',?)",[legacy_file.name])
            self.execute('COMMIT')
            return expected_revision+1
        except BaseException:
            self.rollback();raise
    # ---------- backups ----------
    def backup_folder(self):
        folder=self.file.parent/'Sicherungen';folder.mkdir(parents=True,exist_ok=True);private(folder,0o700);return folder
    def backup(self,target):
        """Consistent copy to a new file, checked by reopening it read-only."""
        target=Path(os.path.abspath(target))
        if target==self.file or target.exists():raise FinanceFailure('Sicherung benötigt einen neuen Dateinamen.')
        try:
            copy=sqlite3.connect(target)
            try:self.db.backup(copy)
            finally:copy.close()
            private(target,0o600)
            with FinanceStore(target,read_only=True) as check:check.load()
        except BaseException as e:
            target.unlink(missing_ok=True)
            if isinstance(e,sqlite3.Error):raise FinanceFailure('Datenbanksicherung fehlgeschlagen.') from None
            raise
    def recovery_backup(self,label):
        target=self.backup_folder()/(label+'-'+str(uuid.uuid4()).upper()+'.sqlite3')
        self.backup(target);return target
    def status(self):
        return {'folder':str(self.file.parent),'file':str(self.file),'schema':SCHEMA,'revision':self.revision,'legacyBackup':self.metadata('legacy_backup') or ''}
