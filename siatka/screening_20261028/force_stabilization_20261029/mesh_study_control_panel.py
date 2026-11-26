"""Small live controls for the independent mesh campaign."""
def panel():
 return r'''<section id="mesh-run-controls" style="border:1px solid #cbd7df;border-left:4px solid #318367;padding:16px;margin:16px 0;background:#f3f8f5;break-inside:avoid">
<h3 style="margin:0 0 8px">Mesh calculation queue · pause and resume</h3>
<p data-mesh-control-status role="status" aria-live="polite">Reading the current mesh calculation…</p>
<div style="display:flex;gap:10px;flex-wrap:wrap"><button type="button" data-mesh-action="pause" disabled style="font:inherit;padding:10px 16px;cursor:pointer">Pause &amp; save</button><button type="button" data-mesh-action="resume" disabled style="font:inherit;padding:10px 16px;cursor:pointer">Resume queue (M11 → M10)</button></div>
<p data-mesh-control-message role="status" style="margin:10px 0 0"></p>
<small>Controls the remaining M11 → M10 calm-water queue. Completed M12 will not restart. Pause finishes the current step and saves its calculated fields. Wait for <b>Paused and saved</b> before disconnecting power. Wave controls remain separate.</small>
</section><script>
(()=>{
const root=document.getElementById('mesh-run-controls');if(!root||root.dataset.bound)return;root.dataset.bound='1';
let state=null,busy=false,token=null;const queueBase='http://127.0.0.1:8772';
const note=root.querySelector('[data-mesh-control-status]'),msg=root.querySelector('[data-mesh-control-message]');
function show(){
 if(!state)return;
 note.textContent=(state.job?state.job+' · ':'')+state.message;
 root.querySelector('[data-mesh-action=pause]').disabled=busy||!state.can_pause;
 root.querySelector('[data-mesh-action=resume]').disabled=busy||!state.can_resume;
 if(state.file){note.append(document.createElement('br'));const path=document.createElement('code');path.style.overflowWrap='anywhere';path.textContent=state.file;note.append(path)}
}
async function refresh(){
 if(location.protocol==='file:'){note.textContent='Open the local dashboard at http://127.0.0.1:8771/ to use the queue controls.';return}
 try{const r=await fetch(queueBase+'/api/mesh-queue',{cache:'no-store'});const d=await r.json();if(!r.ok)throw Error(d.error||'Control status unavailable');state=d;token=d.csrf;show()}
 catch(e){note.textContent=e.message;root.querySelectorAll('button').forEach(b=>b.disabled=true)}
}
root.querySelectorAll('[data-mesh-action]').forEach(b=>b.addEventListener('click',async()=>{
 if(busy||!state)return;
 if(!token){msg.textContent='Local queue service unavailable. Existing M12 resume is intentionally disabled.';return}
 busy=true;show();msg.textContent=b.dataset.meshAction==='pause'?'Requesting safe save…':'Verifying saved continuation…';
 try{const r=await fetch(queueBase+'/api/mesh-queue/'+b.dataset.meshAction,{method:'POST',headers:{'Content-Type':'application/json','X-Mesh-Queue-Token':token},body:JSON.stringify({generation:state.generation})});const d=await r.json();if(!r.ok)throw Error(d.error||'Action refused');msg.textContent=d.message}
 catch(e){msg.textContent=e.message}
 finally{busy=false;await refresh()}
}));
refresh();setInterval(refresh,3000);
})();
</script>'''
