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
assert.notEqual(js,source);js=js.replace(/\}\)\(\);\s*$/,checks+'\n})();');vm.runInNewContext(js,context);
const template=fs.readFileSync('apps/FinanzManager/Web/index.template.html','utf8');
assert.ok(template.includes('finance-app-icon'));assert.equal((template.match(/data-legal="/g)||[]).length,5);assert.ok(template.includes('professionalSoftwareBtn'));
assert.ok(source.includes("message.nonce=window.FM_NATIVE_NONCE"));assert.ok(!/\b(fetch|WebSocket|XMLHttpRequest|sendBeacon)\s*\(/.test(source));
console.log('PASS Brand, legal entry points, software CTA, native nonce and no networking APIs');
