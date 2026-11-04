# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Samuele Timoteo Iacierno
"""Data folder, program settings and acceptance of the terms of use.

macOS: ~/Library/Application Support/IT-Smarthome/FinanzManager (unchanged since 1.2.0)
Windows: %LOCALAPPDATA%\\IT-Smarthome\\FinanzManager (per device, not in the roaming profile)
"""
from datetime import datetime,timezone
from pathlib import Path
import json,os,sys,tempfile
from .documents import TERMS_SHA256,TERMS_VERSION
from .store import FinanceStore,private

DATABASE='finanzmanager.sqlite3'

def default_root():
    if sys.platform=='darwin':return Path.home()/'Library/Application Support/IT-Smarthome/FinanzManager'
    if os.name=='nt':return Path(os.environ.get('LOCALAPPDATA') or Path.home()/'AppData/Local')/'IT-Smarthome/FinanzManager'
    return Path(os.environ.get('XDG_DATA_HOME') or Path.home()/'.local/share')/'IT-Smarthome/FinanzManager'

class Platform:
    def __init__(self,root=None):
        self.root=Path(root or default_root()).absolute()
        self.root.mkdir(parents=True,exist_ok=True);private(self.root,0o700)
        self.settings_file=self.root/'programm.json'
        self._store=None
    # ---------- settings ----------
    def settings(self):
        try:
            value=json.loads(self.settings_file.read_text(encoding='utf-8'))
            return value if isinstance(value,dict) else {}
        except (OSError,ValueError):return {}
    def set(self,**values):
        data=json.dumps({**self.settings(),**values},ensure_ascii=False,indent=2,sort_keys=True).encode()
        handle,temp=tempfile.mkstemp(dir=self.root,prefix='.programm.')
        try:
            with os.fdopen(handle,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
            os.replace(temp,self.settings_file);private(self.settings_file,0o600)
        except BaseException:
            Path(temp).unlink(missing_ok=True);raise
    # ---------- terms of use ----------
    def terms_accepted(self):
        """Only the exact text the user confirmed counts; a new version asks again."""
        return self.settings().get('terms_sha256')==TERMS_SHA256
    def accept_terms(self):
        """Called only after the user's own click."""
        self.set(terms_sha256=TERMS_SHA256,terms_version=TERMS_VERSION,terms_accepted_at=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
    # ---------- database ----------
    @property
    def database_file(self):return self.root/DATABASE
    def store(self):
        if self._store is None:self._store=FinanceStore(self.database_file)
        return self._store
    def close(self):
        if self._store:self._store.close();self._store=None
