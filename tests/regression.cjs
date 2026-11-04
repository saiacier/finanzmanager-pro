// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Samuele Timoteo Iacierno
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict'),{webcrypto}=require('crypto');
const source=fs.readFileSync('apps/FinanzManager/Web/app.js','utf8');
const nodes=new Map();const node=id=>{if(!nodes.has(id))nodes.set(id,{value:'',innerHTML:'',textContent:'',style:{},dataset:{},options:[],classList:{add(){},remove(){},toggle(){}},addEventListener(){},removeEventListener(){},setAttribute(){},focus(){},querySelector(){return null},querySelectorAll(){return[]},insertAdjacentHTML(){}});return nodes.get(id)};
const context={console,assert,crypto:webcrypto,TextEncoder,TextDecoder,structuredClone,Intl,Date,Math,Set,Map,Blob,URL,Number,String,Array,Object,JSON,Promise,Error,RegExp,Uint8Array,btoa,atob,setTimeout:()=>0,clearTimeout(){},document:{getElementById:node,querySelectorAll:()=>[],addEventListener(){},documentElement:{dataset:{}},body:node('body')},window:{scrollTo(){}},localStorage:{getItem(){return null},setItem(){}},confirm:()=>true};
const checks=[
"assert.equal(parseNumber('1.234,56'),1234.56);assert.equal(parseNumber('-99,20'),-99.2);assert.equal(parseDate('31.02.2026'),'');assert.equal(parseDate('30.10.2026'),'2026-10-30');console.log('PASS Money and date parsing');",
"const rows=parseDelimited('Datum;Text;Betrag\\n30.10.2026;\"A; B\";-2,50',';');assert.equal(rows[1][1],'A; B');console.log('PASS CSV quoting');",
"const next=normalize({transactions:[{date:'2026-10-30',description:'Test',amount:-10}],categories:[{id:'c1',name:'Test',group:'variable',budget:100,keywords:[]}]});assert.equal(next.transactions.length,1);assert.equal(next.categories[0].budget,100);assert.ok(next.dashboards.length);console.log('PASS Legacy data normalization');",
"state.balanceSnapshots=[{account:'Test',date:'2026-09-30',amount:100,dayTotal:0}];state.transactions=[{account:'Test',date:'2026-10-01',amount:-25,description:'Test'}];assert.equal(knownBalance('Test','2026-10-31').amount,75);assert.equal(knownBalance('Other','2026-10-31'),null);console.log('PASS Account carry-forward');",
"csvErrors=[];$('csvOrder').value='oldest';importRows=[{date:'2026-10-01',amount:50,bankBalance:100,csvIndex:0},{date:'2026-10-02',amount:-10,bankBalance:90,csvIndex:1}];assert.equal(csvBalanceCheck().mismatches,0);importRows[1].bankBalance=90.01;assert.ok(csvBalanceCheck().mismatches);console.log('PASS Exact bank balance validation');",
"assert.equal(bookingDateColumn(['Buchung','Wertstellungsdatum']),0);console.log('PASS Booking date priority');"
].join('\n');
let js=source.replace("void startFinance();",'');
assert.notEqual(js,source);js=js.replace(/\}\)\(\);\s*$/,checks+'\nglobalThis.bridge={hostCall,nativeSend};\n})();');vm.runInNewContext(js,context);
const template=fs.readFileSync('apps/FinanzManager/Web/index.template.html','utf8');
assert.ok(template.includes('finance-app-icon'));assert.equal((template.match(/data-legal="/g)||[]).length,5);assert.ok(template.includes('professionalSoftwareBtn'));
const csp=template.match(/<meta\s+http-equiv="Content-Security-Policy"\s+content="([^"]+)"/);
assert.ok(csp,'Interface must declare a content security policy');
assert.deepEqual(csp[1].split(';').map(rule=>rule.trim().split(/\s+/)).find(rule=>rule[0]==='connect-src'),['connect-src',"'self'"]);
// All interface requests go through hostCall; its actual request is checked below.
assert.equal((source.match(/\bfetch\s*\(/g)||[]).length,1);
assert.ok(!/\b(WebSocket|XMLHttpRequest|sendBeacon)\s*\(/.test(source));
console.log('PASS Brand, legal entry points, software CTA and same-origin connection policy');

async function checkHostBridge(){
 const requests=[];
 let response={value:{revision:2}},networkError=null;
 context.fetch=async(url,options)=>{
  requests.push({url,options:JSON.parse(JSON.stringify(options))});
  assert.match(url,/^\/api\/host\/[a-z]+$/,'Host calls must use a relative local API URL');
  if(networkError)throw networkError;
  return {json:async()=>response};
 };
 const {hostCall,nativeSend}=context.bridge;
 const message={action:'store-load',id:'request-1',protocol:1};
 assert.deepEqual(await hostCall('message',message),{revision:2});
 assert.deepEqual(requests.pop(),{
  url:'/api/host/message',
  options:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({args:[message]})}
 });
 response={value:true};
 assert.equal(await hostCall('dirty',true),true);
 assert.deepEqual(JSON.parse(requests.pop().options.body),{args:[true]});
 response={error:'Zugriff verweigert.'};
 await assert.rejects(()=>hostCall('message',message),/Zugriff verweigert/);
 networkError=Error('Local server unavailable');
 await assert.rejects(()=>hostCall('message',message),/Local server unavailable/);
 networkError=null;
 console.log('PASS Local host requests, JSON arguments and server/network errors');

 requests.length=0;
 context.window.FM_HOST=false;
 assert.equal(nativeSend(message),false);
 assert.equal(context.window.financeHostQuit(),false);
 context.window.FM_HOST=true;
 assert.equal(nativeSend({action:'print'}),false);
 assert.equal(requests.length,0,'Fallback actions must not send host requests');

 // Wait for the real bridge callback, with a timeout so a lost reply fails the test.
 async function receive(callback,message){
  let timer;
  try{
   return await new Promise((resolve,reject)=>{
    timer=setTimeout(()=>reject(Error('Missing bridge callback: '+callback)),3000);
    context.window[callback]=(...values)=>resolve(values);
    assert.equal(nativeSend(message),true);
   });
  }finally{clearTimeout(timer)}
 }
 response={value:{id:message.id,ok:true,value:{revision:2}}};
 assert.deepEqual(JSON.parse(JSON.stringify(await receive('FinanceStorageReply',message))),[response.value]);
 assert.deepEqual(JSON.parse(requests.at(-1).options.body),{args:[message]});
 response={value:{notice:'Test notice',error:false}};
 assert.deepEqual(await receive('fmNativeResult',{action:'software'}),['Test notice',false]);
 response={error:'Zugriff verweigert.'};
 assert.deepEqual(JSON.parse(JSON.stringify(await receive('FinanceStorageReply',message))),[
  {id:message.id,ok:false,error:'Zugriff verweigert.'}
 ]);
 networkError=Error('Local server unavailable');
 assert.deepEqual(await receive('fmNativeResult',{action:'software'}),['Local server unavailable',true]);
 networkError=null;response={value:true};
 assert.equal(await context.window.financeHostQuit(),true);
 assert.equal(requests.at(-1).url,'/api/host/quit');
 console.log('PASS Host fallback, reply dispatch, error reporting and quit');
}

function checkLocalServer(){
 // Exercise the actual Python server, including rejection paths and absence of side effects.
 // Only this test file is needed; Python is already required by the application.
 const python=String.raw`
from pathlib import Path
from http.client import HTTPConnection
from http.cookies import SimpleCookie
from urllib.parse import urlsplit
import json,sys
sys.path.insert(0,str(Path.cwd()/'platform/python'))
from financecore.pageserver import PageServer

class Host:
    def __init__(self):self.calls=[]
    def echo(self,*args):self.calls.append(list(args));return list(args)
    def private(self):raise AssertionError('Non-allowlisted function was dispatched')

host=Host()
server=PageServer(lambda:'<html>test interface</html>',host,['echo'])
def request(method,path,body=None,headers=None):
    connection=HTTPConnection('127.0.0.1',server.server_port,timeout=3)
    try:
        connection.request(method,path,body=body,headers=headers or {})
        response=connection.getresponse()
        return response.status,response.read(),dict(response.getheaders())
    finally:connection.close()

try:
    assert server.socket.getsockname()[0]=='127.0.0.1'
    assert request('GET','/')[0]==401
    assert request('GET','/start?token=wrong')[0]==401
    status,body,headers=request('GET',urlsplit(server.start_url).path+'?'+urlsplit(server.start_url).query)
    assert status==200
    cookies=SimpleCookie();cookies.load(headers['Set-Cookie'])
    session=cookies[server.cookie]
    assert session['httponly'] and session['samesite']=='Strict'
    cookie=server.cookie+'='+session.value
    assert request('GET','/',headers={'Cookie':cookie})[:2]==(200,b'<html>test interface</html>')
    assert request('GET','/missing',headers={'Cookie':cookie})[0]==404
    assert headers['Cache-Control']=='no-store'
    assert headers['Referrer-Policy']=='no-referrer'
    assert headers['X-Frame-Options']=='DENY'
    print('PASS Loopback server, token bootstrap, session cookie and protected page')

    valid={'Cookie':cookie,'Origin':server.origin,'Content-Type':'application/json'}
    payload=json.dumps({'args':['synthetic test',True]})
    status,body,_=request('POST','/api/host/echo',payload,valid)
    assert status==200 and json.loads(body)=={'value':['synthetic test',True]}
    assert host.calls==[['synthetic test',True]]

    rejected=[
        {key:value for key,value in valid.items() if key!='Cookie'},
        dict(valid,Cookie=server.cookie+'=wrong'),
        {key:value for key,value in valid.items() if key!='Origin'},
        dict(valid,Origin='https://foreign.invalid'),
        dict(valid,Host='foreign.invalid'),
        dict(valid,**{'Content-Type':'text/plain'}),
    ]
    for headers in rejected:
        assert request('POST','/api/host/echo',payload,headers)[0]==403
        assert len(host.calls)==1,'Rejected request caused a host call'
    assert request('GET','/',headers={'Cookie':cookie,'Host':'foreign.invalid'})[0]==403
    for path,body in [('/api/host/private',payload),('/api/host/__class__',payload),
                      ('/other',payload),('/api/host/echo','{"args":"wrong"}'),
                      ('/api/host/echo','invalid JSON'),('/api/host/echo','')]:
        assert request('POST',path,body,valid)[0]==400
        assert len(host.calls)==1,'Invalid request caused a host call'
    print('PASS Allowed API call; missing/invalid session, foreign origin/host and forbidden calls rejected')
finally:
    server.close()
`;
 const output=require('child_process').execFileSync(process.env.PYTHON||'python3',['-B','-c',python],{encoding:'utf8',timeout:15000});
 console.log(output.trim());
}

(async()=>{await checkHostBridge();checkLocalServer()})().catch(error=>{console.error(error);process.exitCode=1});
