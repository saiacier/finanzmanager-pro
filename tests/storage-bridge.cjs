// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Samuele Timoteo Iacierno
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const storage=fs.readFileSync('apps/FinanzManager/Web/storage.js','utf8');
function fixture(options={}){
 const elements=new Map(),messages=[],notifications=[];let revision=options.revision||0;
 const element=id=>{if(!elements.has(id))elements.set(id,{textContent:'',classList:{add(){},remove(){}}});return elements.get(id)};
 const context={console,JSON,Promise,Map,Error,document:{getElementById:element},window:{FM_HOST:true},hostCall:()=>Promise.resolve(),setTimeout,clearTimeout,uid:(()=>{let id=0;return()=>String(++id)})(),$ :element,saveOk:true,state:{transactions:[],categories:[]},STORAGE:'current',normalize:x=>structuredClone(x),confirm:()=>options.accept!==false,localStorage:{getItem:key=>options.legacy&&key==='current'?options.legacy:null},notify:(...a)=>notifications.push(a),render(){},load(){},structuredClone};
 context.nativeSend=message=>{messages.push(structuredClone(message));queueMicrotask(()=>{
   let value,ok=true,error='';
   if(message.action==='store-load'){value={state:options.existing||null,status:{revision,folder:'/test'}}}
   else if(options.failSave){ok=false;error='Synthetic disk full'}
   else {revision++;value={revision,status:{revision,folder:'/test'}}}
   context.window.FinanceStorageReply({id:message.id,ok,value,error})
 });return true};
 vm.createContext(context);
 vm.runInContext(storage+'\nglobalThis.api={initializeStorage,persistNative,getState:()=>state,setState:x=>state=x,flush:window.financeFlush,isReady:()=>storageReady,revision:()=>storageRevision};',context);
 return {api:context.api,messages,notifications,context};
}
(async()=>{
 let f=fixture();await f.api.initializeStorage();assert.equal(f.api.isReady(),true);assert.deepEqual(f.messages.map(m=>m.action),['store-load']);console.log('PASS Empty native DB does not silently import or save defaults');
 f.api.setState({transactions:[{id:'one'}],categories:[]});assert.equal(f.api.persistNative(false),false);
 f.api.setState({transactions:[{id:'two'}],categories:[]});f.api.persistNative(false);
 assert.equal(await f.api.flush(),true);
 const saves=f.messages.filter(m=>m.action==='store-save');
 assert.deepEqual(saves.map(m=>m.revision),[0,1]);assert.equal(saves[0].state.transactions[0].id,'one');assert.equal(saves[1].state.transactions[0].id,'two');
 console.log('PASS Pending writes serialized with immutable snapshots and committed revisions');
 f=fixture({legacy:JSON.stringify({transactions:[{id:'legacy'}],categories:[]})});await f.api.initializeStorage();
 const migration=f.messages.find(m=>m.action==='store-migrate');assert.ok(migration);assert.equal(migration.source,JSON.stringify({transactions:[{id:'legacy'}],categories:[]}));assert.equal(f.api.revision(),1);
 console.log('PASS Original legacy bytes sent for backup only after confirmation');
 f=fixture({legacy:JSON.stringify({transactions:[],categories:[]}),accept:false});await assert.rejects(()=>f.api.initializeStorage());assert.equal(f.messages.length,1);assert.equal(f.api.isReady(),false);f.api.persistNative(false);assert.equal(f.messages.length,1);
 console.log('PASS Declined migration remains read-only');
 f=fixture({existing:{transactions:[{id:'native'}],categories:[]},legacy:JSON.stringify({transactions:[{id:'old'}],categories:[]}),revision:7});await f.api.initializeStorage();assert.equal(f.api.getState().transactions[0].id,'native');assert.equal(f.messages.length,1);
 console.log('PASS Existing SQLite state takes priority over legacy data');
 f=fixture({failSave:true});await f.api.initializeStorage();f.api.persistNative(false);f.api.persistNative(false);assert.equal(await f.api.flush(),false);assert.equal(f.messages.filter(m=>m.action==='store-save').length,1);assert.ok(!f.notifications.some(x=>x[0].includes('gespeichert')));
 console.log('PASS Failed write prevents later queued writes and blocks successful-close status');
})().catch(e=>{console.error(e);process.exitCode=1});
