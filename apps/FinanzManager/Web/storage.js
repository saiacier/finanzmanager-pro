/* SPDX-License-Identifier: GPL-3.0-or-later · Copyright (C) 2026 Samuele Timoteo Iacierno */
// Native storage protocol v1. The UI contains no filesystem access or SQL.
let nativeStorage=false,storageReady=false,storageRevision=0,storageStatus={},saveChain=Promise.resolve(),pendingSaves=0;
let lastStorageError=null;
const storageRequests=new Map();
window.FinanceStorageReply=result=>{const item=storageRequests.get(result.id);if(!item)return;storageRequests.delete(result.id);clearTimeout(item.timer);result.ok?item.resolve(result.value):item.reject(Error(result.error||'Speicherfehler'))};
function storageRequest(action,values={}){return new Promise((resolve,reject)=>{const id=uid(),timer=['store-backup','store-restore'].includes(action)?null:setTimeout(()=>{storageRequests.delete(id);reject(Error('Die lokale Speicherung antwortet nicht. Bitte nicht schließen; erst ein Backup exportieren.'))},60000);storageRequests.set(id,{resolve,reject,timer});if(!nativeSend({action,id,protocol:1,...values})){clearTimeout(timer);storageRequests.delete(id);reject(Error('Native Speicherung nicht verfügbar.'))}})}
function showStorageFailure(error){lastStorageError=error;saveOk=false;hostDirty();$('storageWarning').textContent=error.message+' Änderungen sind möglicherweise noch nicht gespeichert. Exportiere ein JSON-/FMB-Backup, bevor du schließt.';$('storageWarning').classList.remove('hidden')}
function hostDirty(){if(nativeStorage)hostCall('dirty',pendingSaves>0||lastStorageError!==null||!saveOk).catch(()=>{})}
function updateStorageStatus(){hostDirty();const node=$('nativeStorageStatus');if(node)node.textContent=nativeStorage?(pendingSaves?'Speichern läuft …':saveOk?'SQLite · lokal gespeichert':'Nicht gespeichert'):'WebView-Speicher';if($('nativeDataFolder'))$('nativeDataFolder').textContent=storageStatus.folder||'Wird ermittelt …'}
function persistNative(rerender=true,reason='edit'){
 if(!storageReady){showStorageFailure(Error('Datenbestand ist noch nicht geladen.'));return false}
 const snapshot=JSON.parse(JSON.stringify(state));pendingSaves++;saveOk=false;updateStorageStatus();if(rerender)render();
 saveChain=saveChain.then(async()=>{const result=await storageRequest('store-save',{state:snapshot,revision:storageRevision,reason});storageRevision=result.revision;storageStatus=result.status;lastStorageError=null;pendingSaves--;saveOk=pendingSaves===0;if(saveOk){$('storageWarning').classList.add('hidden');notify('Änderungen in SQLite gespeichert')}updateStorageStatus()}).catch(error=>{pendingSaves=Math.max(0,pendingSaves-1);showStorageFailure(error);updateStorageStatus();throw error});
 saveChain.catch(()=>{});return false;
}
window.financeFlush=async()=>{try{await saveChain;return lastStorageError===null&&pendingSaves===0}catch{return false}};
async function initializeStorage(){
 nativeStorage=!!window.FM_HOST;
 if(!nativeStorage){load();storageReady=true;return}
 const loaded=await storageRequest('store-load');storageStatus=loaded.status;storageRevision=loaded.status.revision;
 if(loaded.state){const next=normalize(loaded.state);if(next.transactions.length!==loaded.state.transactions.length)throw Error('Datenbank enthält nicht unterstützte Buchungen. Es wurde nichts verändert.');state=next}
 else{
  let source=null,data=null;
  const current=localStorage.getItem(STORAGE)||localStorage.getItem('finanzmanager_pro_offline_v2');
  if(current){data=JSON.parse(current);source=current}
  else if(localStorage.getItem('fm_transactions')!==null||localStorage.getItem('fm_categories')!==null){
   const old={transactions:JSON.parse(localStorage.getItem('fm_transactions')||'[]'),categories:JSON.parse(localStorage.getItem('fm_categories')||'[]'),theme:localStorage.getItem('fm_dark')==='true'?'dark':'light'};
   data=old;source=JSON.stringify({format:'legacy-key-snapshot',keys:{fm_transactions:localStorage.getItem('fm_transactions'),fm_categories:localStorage.getItem('fm_categories'),fm_dark:localStorage.getItem('fm_dark')}})
  }
  if(data){
   const next=normalize(data);if(next.transactions.length!==data.transactions.length)throw Error('Alte Daten enthalten ungültige Buchungen. Übernahme abgebrochen.');
   if(!confirm('Vorhandene lokale WebView-Daten mit '+next.transactions.length+' Buchungen in SQLite übernehmen? Zuerst wird der unveränderte Ausgangsstand gesichert. Die alten Daten bleiben erhalten.'))throw Error('Übernahme nicht durchgeführt. Starte erneut, um zu übernehmen, oder exportiere ein Backup in der alten App.');
   const result=await storageRequest('store-migrate',{state:next,revision:storageRevision,source});
   state=next;storageRevision=result.revision;storageStatus=result.status
  }
 }
 storageReady=true;saveOk=true;updateStorageStatus();
}
function setupNativeStorage(){
 document.getElementById('openDataFolder').addEventListener('click',()=>nativeSend({action:'store-open-folder',protocol:1}));
 document.getElementById('sqliteBackup').addEventListener('click',async()=>{if(nativeStorage&&storageRevision===0)persistNative(false);if(!await window.financeFlush())return showStorageFailure(Error('Noch nicht gespeicherte Änderungen.'));try{const result=await storageRequest('store-backup');if(!result.cancelled)notify('SQLite-Sicherung erstellt und geprüft')}catch(e){notify('SQLite-Sicherung fehlgeschlagen: '+e.message,true)}});
 document.getElementById('sqliteRestore').addEventListener('click',async()=>{if(!await window.financeFlush())return showStorageFailure(Error('Noch nicht gespeicherte Änderungen.'));document.body.classList.add('storage-busy');try{const result=await storageRequest('store-restore',{revision:storageRevision});if(!result.cancelled){const next=normalize(result.state);if(next.transactions.length!==result.state.transactions.length)throw Error('Nicht unterstützte Buchungen in Sicherung.');state=next;storageRevision=result.status.revision;storageStatus=result.status;render();notify('SQLite-Sicherung wiederhergestellt')}}catch(e){notify('Wiederherstellung fehlgeschlagen: '+e.message,true)}finally{document.body.classList.remove('storage-busy')}});
 updateStorageStatus();
}
async function startFinance(){
 fillGroups('editGroup');fillGroups('categoryGroup');setupWorkspace();setupNativeStorage();document.body.classList.add('storage-busy');
 try{await initializeStorage();render();showTab('dashboard');document.body.classList.remove('storage-busy')}
 catch(e){showStorageFailure(e);$('storageBootError').textContent=e.message;$('storageBootError').classList.remove('hidden');document.body.classList.add('storage-failed')}
}
