# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Samuele Timoteo Iacierno
"""Program window of FinanzManager for macOS and Windows.

Shows the terms first (accepted only by the user's own click), then the interface from the local
PageServer in a pywebview window. The interface reaches the functions in HOST_CALLS through
/api/host/<function>: storage protocol 1, file dialogs, legal documents, allowed links and the
closing protection. The terms and document pages use the pywebview bridge (`pywebview.api`).
"""
from datetime import date
from html import escape
from pathlib import Path
import threading
from . import PRODUCT,VERSION,desktop
from .documents import DOCUMENTS,TERMS_VERSION,TITLES
from .pageserver import PageServer
from .store import FinanceFailure,FinanceStore,export_allowed

MAX_EXPORT=50_000_000
HOST_CALLS={'message','dirty','quit'}

class DocumentWindow:
    """Bridge of a separate window showing one legal document."""
    def __init__(self,host,key):self._host,self._key=host,key
    def save(self):self._host.save_document(self._key)

class FinanceHost:
    def __init__(self,platform,webview,web_page):
        """web_page(): interface HTML; served only to the program window."""
        self._platform,self._webview,self._web_page=platform,webview,web_page
        self._lock=threading.Lock();self._window=None;self._server=None;self._dirty=False;self._closing=False
    # ---------- window ----------
    def attach(self,window):
        self._window=window;window.events.closing+=self._on_closing
    def show(self):
        if self._server is None:self._server=PageServer(self._interface,self,HOST_CALLS)
        if not self._platform.terms_accepted():return self._terms_page()
        self._window.load_url(self._server.start_url)
    def _interface(self):
        return self._web_page().replace('<head>','<head><script>window.FM_HOST=true</script>',1)
    def _terms_page(self):
        buttons=''.join('<button onclick="pywebview.api.show_document(\'%s\')">%s</button>'%(key,escape(TITLES[key])) for key in ['privacy','imprint','licenses'])
        self._window.load_html(desktop.page('Nutzungsbedingungen','<h1>FinanzManager Pro · Nutzungsbedingungen</h1><p>Fassung '+escape(TERMS_VERSION)+' · Kostenlose freie Software unter GPL-3.0, ohne Pflicht zur Unterstützung. Du kannst die Bedingungen und weiteren Informationen vor der Zustimmung lesen und speichern. Datenschutzinformationen sind keine Einwilligungserklärung.</p><div class="box"><pre>'+escape(DOCUMENTS['terms'])+'</pre></div>'+buttons+'<button onclick="pywebview.api.save_document(\'terms\')">Bedingungen speichern</button><label><input type="checkbox" id="read" onchange="document.getElementById(\'accept\').disabled=!this.checked"> Ich habe die Nutzungsbedingungen gelesen und stimme zu.</label><button class="primary" id="accept" disabled onclick="document.getElementById(\'read\').checked&&pywebview.api.accept_terms()">Zustimmen und starten</button><button onclick="pywebview.api.quit()">Beenden</button>'))
    def run_js(self,code):
        try:
            if self._window and not self._closing:self._window.run_js(code)
        except Exception:pass
    # ---------- called by the terms page ----------
    def accept_terms(self):
        """The user ticked the box and clicked „Zustimmen“; never called on the user's behalf."""
        self._platform.accept_terms();self.show()
    def show_document(self,key):
        if key not in DOCUMENTS:return
        body='<h1>'+escape(TITLES[key])+'</h1><div class="box"><pre>'+escape(DOCUMENTS[key])+'</pre></div><button onclick="pywebview.api.save()">Text speichern …</button>'
        self._webview.create_window(TITLES[key],html=desktop.page(TITLES[key],body),js_api=DocumentWindow(self,key),width=760,height=760)
    def save_document(self,key):
        if key not in DOCUMENTS:return
        target=self._save_path('FinanzManager-'+key+'.txt')
        if target and export_allowed(target,self._platform.database_file):desktop.write_atomic(target,DOCUMENTS[key].encode())
    def about(self):
        body='<h1>FinanzManager Pro '+escape(VERSION)+'</h1><p>Entwickelt von Samuele Timoteo Iacierno · IT-Smarthome<br>Kostenlose lokale Haushalts- und Budgetsoftware · freie Software unter GPL-3.0.</p>'
        self._webview.create_window('Über FinanzManager Pro',html=desktop.page('Über FinanzManager Pro',body),width=520,height=300)
    def open_settings(self):self.run_js("document.querySelector('[data-tab=settings]')?.click()")
    # ---------- called by the interface ----------
    def dirty(self,value):
        """True while changes are not yet confirmed as saved in the database."""
        self._dirty=bool(value)
    def message(self,payload):
        if not isinstance(payload,dict):return None
        action=str(payload.get('action',''))
        if action.startswith('store-'):return self._storage(payload)
        if action=='legal':return self.show_document(payload.get('document'))
        if action in ('support','software'):
            desktop.open_external(desktop.SUPPORT_URL if action=='support' else desktop.DOWNLOADS_URL);return None
        if action=='save':return self._export(payload)
        return None
    def _export(self,payload):
        text,name=payload.get('content'),payload.get('filename')
        if not isinstance(text,str) or not isinstance(name,str) or len(text.encode())>MAX_EXPORT:return None
        target=self._save_path(Path(name).name or 'Export')
        if not target:return {'notice':'Speichern abgebrochen'}
        if not export_allowed(target,self._platform.database_file):return {'notice':'Die aktive Datenbank darf nicht durch einen Export ersetzt werden.','error':True}
        try:desktop.write_atomic(target,text.encode())
        except OSError:return {'notice':'Speichern fehlgeschlagen','error':True}
        return {'notice':'Datei gespeichert'}
    def _storage(self,payload):
        request=payload.get('id','');request=request if isinstance(request,str) else ''
        try:
            if payload.get('protocol')!=1:raise FinanceFailure('Nicht unterstützte Speicher-Schnittstelle.')
            with self._lock:value=self._storage_action(payload)
            return {'id':request,'ok':True,'value':value,'error':''}
        except (FinanceFailure,OSError) as e:
            if not request:return {'notice':str(e),'error':True}
            return {'id':request,'ok':False,'value':None,'error':str(e)}
    def _storage_action(self,payload):
        store=self._platform.store();action=payload['action']
        if action=='store-load':return {'state':store.load(),'status':store.status()}
        if action in ('store-save','store-migrate'):
            state,revision=payload.get('state'),payload.get('revision')
            if not isinstance(state,dict) or not isinstance(revision,int) or isinstance(revision,bool):raise FinanceFailure('Ungültiger Speicherauftrag.')
            source=None
            if action=='store-migrate':
                source=payload.get('source')
                if not isinstance(source,str):raise FinanceFailure('Originalsicherung fehlt.')
            reason=payload.get('reason') if payload.get('reason') in ('edit','restore') else 'edit'
            following=store.save(state,revision,reason=reason,legacy_source=source)
            return {'revision':following,'status':store.status()}
        if action=='store-open-folder':
            desktop.reveal(store.file.parent);return None
        if action=='store-backup':
            target=self._save_path('FinanzManager-'+date.today().isoformat()+'.sqlite3',('SQLite-Datenbank (*.sqlite3)',))
            if not target:return {'cancelled':True}
            store.backup(target);return {'cancelled':False}
        if action=='store-restore':
            source=desktop.first_path(self._window.create_file_dialog(self._webview.FileDialog.OPEN,allow_multiple=False,file_types=('SQLite-Datenbank (*.sqlite3)','Alle Dateien (*.*)')))
            if not source:return {'cancelled':True}
            with FinanceStore(source,read_only=True) as backup:state=backup.load()
            revision=payload.get('revision')
            if state is None or not isinstance(revision,int):raise FinanceFailure('Sicherung enthält keinen Datenbestand.')
            if not self._window.create_confirmation_dialog('SQLite-Sicherung wiederherstellen?','Der bisherige Stand wird zuerst im lokalen Sicherungsordner gesichert und dann ersetzt. Die Sicherungsdatei bleibt unverändert.'):return {'cancelled':True}
            store.save(state,revision,reason='restore')
            return {'cancelled':False,'state':store.load(),'status':store.status()}
        raise FinanceFailure('Unbekannte Speicheraktion.')
    def _save_path(self,name,file_types=()):
        return desktop.first_path(self._window.create_file_dialog(self._webview.FileDialog.SAVE,save_filename=name,file_types=file_types))
    # ---------- closing ----------
    def quit(self):
        self._closing=True
        threading.Thread(target=self._shutdown,daemon=True).start()
    def _shutdown(self):
        self._stop();self._window.destroy()
    def _stop(self):
        if self._server:self._server.close();self._server=None
        with self._lock:self._platform.close()
    def _on_closing(self):
        if self._closing:return True
        if self._dirty:
            threading.Timer(0.1,lambda:self.run_js("if(confirm('Änderungen möglicherweise nicht gespeichert. Bitte zuerst ein JSON-/FMB-Backup exportieren. Trotzdem beenden?'))window.financeHostQuit?.()")).start()
            return False
        self._closing=True;self._stop();return True
