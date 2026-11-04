# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Samuele Timoteo Iacierno
"""Helpers of the program window: the interface page, external links, folders, files and the
packaged start check.

Nothing here connects to the internet by itself; external pages open in the system browser only
after an explicit click and only for the allowed addresses.
"""
from html import escape
from pathlib import Path
from urllib.parse import urlparse
import json,os,subprocess,sys,tempfile,threading,time,webbrowser

DOWNLOADS_URL='https://it-smarthome.net/downloads'
SUPPORT_URL='https://www.paypal.com/ncp/payment/Q8F4MVPJS87CU'

def external_allowed(url):
    """PayPal support link and the download page of it-smarthome.net, nothing else."""
    u=urlparse(url)
    return u.scheme=='https' and not u.username and not u.password and u.port is None and (u.hostname=='www.paypal.com' or (u.hostname=='it-smarthome.net' and u.path=='/downloads'))

def open_external(url):
    if not external_allowed(url):return False
    webbrowser.open(url);return True

def reveal(folder):
    """Shows a folder in Finder or Explorer."""
    folder=str(folder)
    if sys.platform=='darwin':subprocess.run(['open',folder],check=False)
    elif os.name=='nt':os.startfile(folder)  # noqa: only the program's own data folder
    else:subprocess.run(['xdg-open',folder],check=False)

def first_path(result):
    """pywebview returns a string or a sequence depending on dialog and system."""
    if not result:return None
    return str(result[0] if isinstance(result,(list,tuple)) else result)

def write_atomic(target,data):
    target=Path(target);handle,temp=tempfile.mkstemp(dir=target.parent,prefix='.'+target.name+'.')
    try:
        with os.fdopen(handle,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(temp,target)
    except BaseException:
        Path(temp).unlink(missing_ok=True);raise
    try:os.chmod(target,0o600)
    except OSError:pass

def resources():
    """Folder with Web and Legal: inside the package, or the project folder when run from source."""
    if getattr(sys,'frozen',False):return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[3]

def interface(web_folder):
    """Self-contained interface page: template with inlined style and scripts."""
    web=Path(web_folder)
    script=(web/'app.js').read_text(encoding='utf-8').replace('/* FINANCE_STORAGE */',(web/'storage.js').read_text(encoding='utf-8'))
    return (web/'index.template.html').read_text(encoding='utf-8').replace('<!-- APP_STYLE -->','<style>'+(web/'style.css').read_text(encoding='utf-8')+'</style>').replace('<!-- APP_SCRIPT -->','<script>'+script+'</script>')

def self_test(window,result,timeout=90):
    """Packaged start check: waits until the hidden window shows the interface with the local
    database loaded, writes {ok, title, storage} to `result` and closes the window."""
    def run():
        state={};ok=False;end=time.time()+timeout
        while time.time()<end and not ok:
            try:
                raw=window.run_js("JSON.stringify({origin:location.origin,ready:document.readyState,title:document.title,storage:(document.getElementById('nativeStorageStatus')||{}).textContent||'',busy:document.body.classList.contains('storage-busy'),failed:document.body.classList.contains('storage-failed')})")
                state=json.loads(raw) if isinstance(raw,str) else {}
            except Exception:state={}
            ok=str(state.get('origin','')).startswith('http://127.0.0.1:') and state.get('ready')=='complete' and str(state.get('title','')).startswith('FinanzManager') and not state.get('busy') and not state.get('failed') and 'SQLite' in str(state.get('storage',''))
            if not ok:time.sleep(0.3)
        Path(result).write_text(json.dumps(dict(ok=ok,title=state.get('title',''),storage=state.get('storage',''),frozen=bool(getattr(sys,'frozen',False))),ensure_ascii=False))
        window.destroy()
    threading.Thread(target=run,daemon=True).start()

PAGE_STYLE='''<style>
:root{color-scheme:light dark;--bg:#f5f5f7;--text:#1d1d1f;--muted:#6e6e73;--accent:#6246ea;--on-accent:#fff;--panel:#fff;--line:#e2e2e7}
@media (prefers-color-scheme:dark){:root{--bg:#000;--text:#f5f5f7;--muted:#a1a1a6;--accent:#a99bff;--on-accent:#16113a;--panel:#1d1d1f;--line:#38383c}}
body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
main{max-width:820px;margin:0 auto;padding:40px 28px}h1{font-size:26px;letter-spacing:-.02em;margin:0 0 6px}p{color:var(--muted)}
.box{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:18px 20px;margin:18px 0}
pre{white-space:pre-wrap;font-family:inherit;font-size:13px;line-height:1.6;max-height:48vh;overflow:auto;margin:0}
button{font:inherit;font-weight:600;border:1px solid var(--line);background:var(--panel);color:var(--text);border-radius:980px;padding:9px 18px;cursor:pointer;margin:6px 8px 0 0}
button.primary{background:var(--accent);border-color:var(--accent);color:var(--on-accent)}button:disabled{opacity:.45;cursor:not-allowed}
label{display:flex;gap:10px;align-items:center;margin:14px 0}
</style>'''

def page(title,body):
    return '<!doctype html><html lang="de"><head><meta charset="utf-8"><title>'+escape(title)+'</title>'+PAGE_STYLE+'</head><body><main>'+body+'</main></body></html>'
