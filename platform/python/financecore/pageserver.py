# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Samuele Timoteo Iacierno
"""Local page server for the interface.

Listens only on 127.0.0.1 with a random port and token. The program window opens /start?token
once; afterwards a Strict, HttpOnly session cookie authorizes the page and its calls to
/api/host/<function>, which reach the program logic in the same process. Requests from other
origins, without the cookie or for functions outside `calls` are refused. A local origin keeps
Web Crypto (encrypted backups) available on macOS and Windows.
"""
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from urllib.parse import urlparse,parse_qs
import json,secrets,threading

class PageServer(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,page,host_api,calls):
        """page(): current HTML; host_api: object whose methods in calls the page may use."""
        super().__init__(('127.0.0.1',0),_Handler)
        self.page,self.host_api,self.calls=page,host_api,set(calls);self.token=secrets.token_urlsafe(32)
        self.origin='http://127.0.0.1:%d'%self.server_port;self.cookie='finance_session_%d'%self.server_port
        self.thread=threading.Thread(target=self.serve_forever,daemon=True);self.thread.start()
    @property
    def start_url(self):return self.origin+'/start?token='+self.token
    def close(self):self.shutdown();self.server_close()

class _Handler(BaseHTTPRequestHandler):
    server_version='FinanzManager'
    def log_message(self,*args):pass  # Never log bearer URLs.
    def send(self,status,body,ctype='text/plain; charset=utf-8',extra=None):
        self.send_response(status);self.send_header('Content-Type',ctype);self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer');self.send_header('X-Frame-Options','DENY')
        for k,v in (extra or {}).items():self.send_header(k,v)
        self.end_headers();self.wfile.write(body)
    def authenticated(self):
        from http.cookies import SimpleCookie
        cookies=SimpleCookie()
        try:cookies.load(self.headers.get('Cookie',''))
        except Exception:return False
        token=cookies.get(self.server.cookie)
        return bool(token and secrets.compare_digest(token.value,self.server.token))
    def do_GET(self):
        if self.headers.get('Host')!='127.0.0.1:%d'%self.server.server_port:return self.send(403,b'Host nicht zugelassen.')
        u=urlparse(self.path)
        if u.path=='/start' and secrets.compare_digest(parse_qs(u.query).get('token',[''])[0],self.server.token):
            # A same-origin refresh keeps the cookie Strict even for program-initiated loads.
            return self.send(200,b'<!doctype html><meta http-equiv="refresh" content="0;url=/">','text/html; charset=utf-8',{'Set-Cookie':'%s=%s; Path=/; HttpOnly; SameSite=Strict'%(self.server.cookie,self.server.token)})
        if not self.authenticated():return self.send(401,'Bitte FinanzManager starten und das dort geöffnete Fenster verwenden.'.encode())
        if u.path!='/':return self.send(404,b'Nicht gefunden')
        self.send(200,self.server.page().encode(),'text/html; charset=utf-8')
    def json(self,value,status=200):self.send(status,json.dumps(value,ensure_ascii=False).encode(),'application/json; charset=utf-8')
    def do_POST(self):
        if self.headers.get('Host')!='127.0.0.1:%d'%self.server.server_port or not self.authenticated():return self.json({'error':'Zugriff verweigert.'},403)
        if self.headers.get('Origin')!=self.server.origin or self.headers.get('Content-Type','').split(';')[0]!='application/json':return self.json({'error':'Fremde Anfrage blockiert.'},403)
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=150*1024*1024:raise ValueError('Anfrage ist leer oder zu groß.')
            data=json.loads(self.rfile.read(length));path=urlparse(self.path).path
            name=path[len('/api/host/'):] if path.startswith('/api/host/') else ''
            args=data.get('args',[]) if isinstance(data,dict) else None
            if name not in self.server.calls or not isinstance(args,list):raise ValueError('Unbekannte Programmfunktion.')
            self.json(dict(value=getattr(self.server.host_api,name)(*args)))
        except (ValueError,KeyError,TypeError) as e:self.json({'error':str(e)},400)
        except BrokenPipeError:pass
