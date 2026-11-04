# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Samuele Timoteo Iacierno
"""Storage checks of FinanceCore (same cases as the former StoreTests.swift). Synthetic data only.

  python3 -m unittest discover -s tests
"""
from pathlib import Path
import copy,os,sqlite3,sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'platform/python'))
from financecore.store import FinanceFailure,FinanceStore,export_allowed

STATE={'transactions':[{'id':'t1','date':'2026-10-01','description':'Test','amount':-12.34,'account':'Hauptkonto','categoryId':'cat'}],
       'categories':[{'id':'cat','name':'Test','group':'variable','budget':100}],'dashboards':[{'id':'d1','name':'Übersicht','widgets':[]}],
       'goals':[{'id':'g1','name':'Test','target':100,'saved':10}],'balanceSnapshots':[{'account':'Hauptkonto','date':'2026-10-01','amount':100.0,'dayTotal':-12.34}],
       'theme':'dark','showBalance':False}

class StoreTests(unittest.TestCase):
    """Runs in order on one database, like the Swift checks."""
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.base=Path(cls.temp.name)
        cls.file=cls.base/'finanzmanager.sqlite3';cls.store=FinanceStore(cls.file);cls.state=copy.deepcopy(STATE)
        cls.backup=cls.base/'backup.sqlite3'
    @classmethod
    def tearDownClass(cls):cls.store.close();cls.temp.cleanup()
    def test_01_empty_database(self):
        self.assertIsNone(self.store.load());self.assertEqual(self.store.revision,0)
        if os.name!='nt':self.assertEqual(self.file.stat().st_mode&0o777,0o600)
    def test_02_migration_keeps_original(self):
        raw='{"original":"unmodified"}'
        self.assertEqual(self.store.save(self.state,0,legacy_source=raw),1)
        status=self.store.status()
        self.assertEqual((self.base/'Sicherungen'/status['legacyBackup']).read_text(encoding='utf-8'),raw)
    def test_03_reopen_keeps_everything(self):
        with FinanceStore(self.file) as reopened:loaded=reopened.load()
        self.assertEqual(loaded['transactions'][0]['amount'],-12.34);self.assertEqual(loaded['theme'],'dark')
        self.assertEqual(len(loaded['goals']),1);self.assertEqual(len(loaded['balanceSnapshots']),1)
    def test_04_stale_revision_and_second_migration(self):
        with self.assertRaises(FinanceFailure):self.store.save(self.state,0)
        with self.assertRaises(FinanceFailure):self.store.save(self.state,1,legacy_source='different')
        self.assertEqual(self.store.revision,1)
    def test_05_duplicate_ids(self):
        invalid=dict(self.state,transactions=[{'id':'a','date':'2026-10-01','description':'A','amount':1},{'id':'a','date':'2026-10-02','description':'B','amount':2}])
        with self.assertRaises(FinanceFailure):self.store.save(invalid,1)
        self.assertEqual(self.store.revision,1)
    def test_06_invalid_date_and_amount(self):
        for day,amount in [('2026-02-31',1.0),('2026-10-01',1e20),('2026-10-01',True)]:
            with self.assertRaises(FinanceFailure):self.store.save(dict(self.state,transactions=[{'id':'a','date':day,'description':'A','amount':amount}]),1)
    def test_07_backup(self):
        self.store.backup(self.backup)
        with FinanceStore(self.backup,read_only=True) as snapshot:
            self.assertEqual(snapshot.revision,1);self.assertIsNotNone(snapshot.load())
            with self.assertRaises(FinanceFailure):snapshot.save(self.state,1)
        with self.assertRaises(FinanceFailure):self.store.backup(self.backup)
    def test_08_restore_creates_recovery_snapshot(self):
        type(self).state['transactions']=[]
        self.assertEqual(self.store.save(self.state,1,reason='restore'),2)
        self.assertEqual(len([f for f in os.listdir(self.base/'Sicherungen') if f.startswith('vor-wiederherstellung')]),1)
        with FinanceStore(self.backup,read_only=True) as snapshot:self.assertEqual(len(snapshot.load()['transactions']),1)
    def test_09_restore_from_backup(self):
        with FinanceStore(self.backup,read_only=True) as snapshot:type(self).state=snapshot.load()
        self.assertEqual(self.store.save(self.state,2,reason='restore'),3)
        self.assertEqual(len(self.store.load()['transactions']),1)
    def test_10_future_schema(self):
        future=self.base/'future.sqlite3';self.store.backup(future)
        db=sqlite3.connect(future);db.execute('PRAGMA user_version=999');db.commit();db.close()
        before=future.read_bytes()
        with self.assertRaises(FinanceFailure):FinanceStore(future)
        self.assertEqual(future.read_bytes(),before)
    def test_11_foreign_database(self):
        foreign=self.base/'foreign.sqlite3';db=sqlite3.connect(foreign);db.execute('CREATE TABLE unrelated(id)');db.commit();db.close()
        with self.assertRaises(FinanceFailure):FinanceStore(foreign)
    def test_12_failed_insert_rolls_back(self):
        db=sqlite3.connect(self.file);db.execute("CREATE TRIGGER synthetic_failure BEFORE INSERT ON records WHEN NEW.key='bad' BEGIN SELECT RAISE(ABORT,'synthetic'); END");db.commit();db.close()
        with self.assertRaises(FinanceFailure):self.store.save(dict(self.state,transactions=[{'id':'bad','date':'2026-10-01','description':'Test','amount':1}]),3)
        self.assertEqual(self.store.revision,3);self.assertEqual(self.store.load()['transactions'][0]['id'],'t1')
    def test_13_exports_cannot_replace_database(self):
        self.assertFalse(export_allowed(self.file,self.file))
        self.assertFalse(export_allowed(str(self.file)+'-journal',self.file))
        self.assertTrue(export_allowed(self.base/'export.json',self.file))
    def test_14_cents_round_half_away_from_zero(self):
        from financecore.store import cents
        self.assertEqual([cents(x) for x in (0.005,-0.005,1.005,12.345,-12.345,-12.34)],[1,-1,100,1235,-1235,-1234])

if __name__=='__main__':unittest.main()
