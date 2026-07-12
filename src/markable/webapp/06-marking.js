/* ---------- cloud marking: test + key + scans → judgements ---------- */
const AIM={test:null,key:null,scans:[],structKey:null};
const MARK_SCHEMA={type:'object',properties:{
  student_label:{type:'string'},
  judgements:{type:'array',items:{type:'object',properties:{
    question:{type:'string'},marks_awarded:{type:'number'},marks_available:{type:'number'},
    transcription:{type:'string'},evidence:{type:'string'},feedback:{type:'string'},
    confidence:{type:'number'},needs_review:{type:'boolean'},review_reason:{type:['string','null']}},
    required:['question','marks_awarded','marks_available','transcription','evidence','feedback','confidence','needs_review','review_reason'],
    additionalProperties:false}}},
  required:['student_label','judgements'],additionalProperties:false};
function aimOk(id){$(id.replace('-input','')).classList.add('ok')}
function b64(buf){let s='';const u=new Uint8Array(buf);
  for(let i=0;i<u.length;i+=32768)s+=String.fromCharCode.apply(null,u.subarray(i,i+32768));
  return btoa(s)}
async function fileBlock(f){
  const data=b64(await f.arrayBuffer());
  if(/\.pdf$/i.test(f.name))
    return {type:'document',source:{type:'base64',media_type:'application/pdf',data}};
  const mt=/\.png$/i.test(f.name)?'image/png':/\.webp$/i.test(f.name)?'image/webp':
    /\.gif$/i.test(f.name)?'image/gif':'image/jpeg';
  return {type:'image',source:{type:'base64',media_type:mt,data}};
}
wireDrop('drop-aim-test','aim-test-input',async f=>{
  const s=$('aim-test-status');
  try{AIM.test={name:f.name,text:await docText(f.name,await f.arrayBuffer())};
    if(!AIM.test.text.trim())throw new Error('no readable text');
    s.className='status';s.textContent='✓ '+f.name+docWarnSuffix();aimOk('drop-aim-test');
  }catch(e){AIM.test=null;s.className='status err';s.textContent=e.message}
});
wireDrop('drop-aim-key','aim-key-input',async f=>{
  const s=$('aim-key-status');
  try{AIM.key={name:f.name,text:await docText(f.name,await f.arrayBuffer())};
    if(!AIM.key.text.trim())throw new Error('no readable text');
    AIM.structKey=/\.ya?ml$/i.test(f.name)?parseKeyYaml(AIM.key.text):null;
    s.className='status';s.textContent='✓ '+f.name+docWarnSuffix()+
      (AIM.structKey?' · structured key recognised — question/marks reconciliation is ON':'');
    aimOk('drop-aim-key');
  }catch(e){AIM.key=null;AIM.structKey=null;s.className='status err';s.textContent=e.message}
});
(function(){
  // scans box takes multiple files, so it gets its own wiring
  const input=$('aim-scans-input'),drop=$('drop-aim-scans');
  if(!input)return;
  function paintList(){
    const box=$('aim-scans-list');if(!box)return;
    box.innerHTML=AIM.scans.map((f,i)=>'<div class="scan-item"><span>'+esc(f.name)+
      ' <span class="muted">('+(f.size/1048576).toFixed(1)+' MB)</span></span>'+
      '<button class="mini" aria-label="remove '+esc(f.name)+'" onclick="rmScan('+i+')">✕</button></div>').join('');
    const s=$('aim-scans-status');s.className='status';
    s.textContent=AIM.scans.length?('✓ '+AIM.scans.length+' script(s) ready.'):'';
    $('drop-aim-scans').classList.toggle('ok',AIM.scans.length>0);
  }
  window.rmScan=i=>{AIM.scans.splice(i,1);paintList()};
  function add(files){for(const f of files)AIM.scans.push(f);paintList()}
  input.addEventListener('change',e=>add(e.target.files));
  ['dragover','dragenter'].forEach(ev=>drop.addEventListener(ev,e=>{e.preventDefault();drop.classList.add('drag')}));
  ['dragleave','dragend','drop'].forEach(ev=>drop.addEventListener(ev,e=>{e.preventDefault();drop.classList.remove('drag')}));
  drop.addEventListener('drop',e=>add(e.dataTransfer.files));
})();
const MARK_SYS_PREFIX='You are marking scanned student scripts for a paper-based school assessment.\n'+
  'You will see one student\'s scanned script (images or a PDF). Mark EVERY question strictly\n'+
  'against the answer key below. Transcribe what the student wrote so transcription errors are\n'+
  'visible, cite evidence for the marks you award, and write one sentence of warm, specific\n'+
  'feedback per question. If a response is illegible, blank, or ambiguous, set needs_review=true\n'+
  'and award conservatively — never guess. If the script shows a student name or ID, report it\n'+
  'as student_label; otherwise use the filename.\n\n';
/* Deterministic validation — never trust the model's own flags alone.
   Every judgement is checked against hard rules; failures force review. */
const MAX_SCAN_MB=20;
async function markScans(){
  const el=$('aim-result');
  if(!AIM.test||!AIM.key||!AIM.scans.length){
    el.innerHTML='<div class="card"><p class="status err" style="display:block">Add all three: the test (1), the answer key (2) and at least one scanned script (3).</p></div>';
    el.classList.add('active');return}
  if(!needKey())return;
  const tooBig=AIM.scans.filter(f=>f.size>MAX_SCAN_MB*1048576);
  if(tooBig.length){
    el.innerHTML='<div class="card"><p class="status err" style="display:block">These scans exceed the '+MAX_SCAN_MB+' MB limit: '+
      tooBig.map(f=>esc(f.name)+' ('+(f.size/1048576).toFixed(1)+' MB)').join(', ')+
      '. Re-scan at a lower resolution or split the file.</p></div>';el.classList.add('active');return}
  const items=['The test text (“'+AIM.test.name+'”)','The answer key (“'+AIM.key.name+'”)']
    .concat(AIM.scans.map(f=>'Scanned script: '+f.name+' ('+(f.size/1048576).toFixed(1)+' MB)'));
  if(!await cloudConsent('Marking '+AIM.scans.length+' script(s)',items))return;
  const sys=MARK_SYS_PREFIX+'=== THE TEST ===\n'+AIM.test.text+'\n\n=== THE ANSWER KEY ===\n'+AIM.key.text;
  const results=[];
  CLOUD_CANCEL=false;
  for(let i=0;i<AIM.scans.length;i++){
    if(CLOUD_CANCEL){results.push({student_label:'(cancelled)',_file:AIM.scans[i].name,
      _error:'cancelled before sending',judgements:[]});continue}
    const f=AIM.scans[i];
    busy(el,'Marking script '+(i+1)+' of '+AIM.scans.length+' with '+provName()+' — '+f.name+' …',true);
    try{
      const out=await callAI({system:sys,schema:MARK_SCHEMA,
        content:[await fileBlock(f),{type:'text',text:'Mark this script. Filename: '+f.name}]});
      out._file=f.name;results.push(validateResult(out,AIM.structKey));
    }catch(err){results.push({student_label:f.name,_file:f.name,_error:err.message,judgements:[]})}
  }
  renderMarks(el,results);
}
/* Review + finalise workflow. Marks are PROPOSALS until the teacher acts:
   every validation-flagged item must be accepted or overridden (with the mark
   they choose) before the export unlocks. Decisions live in MREV. */
let MRES=null,MREV={};
function mkey(ri,j){return ri+'|'+j.question}
function renderMarks(el,results){
  MRES=results;MREV={};
  let cards='';
  results.forEach((r,ri)=>{
    if(r._error){cards+='<div class="card"><h3>'+esc(r.student_label||r._file)+'</h3>'+
      '<p class="status err" style="display:block">Failed: '+esc(r._error)+'</p>'+
      '<p class="hint">This script was NOT marked — nothing for it will appear in the export.</p></div>';return}
    let rows='';
    r.judgements.forEach((j,ji)=>{
      const k=mkey(ri,j);
      const flags=(j._flags||[]).join('; ');
      const ctl=j._review
        ?'<div class="rev-ctl" id="ctl-'+ri+'-'+ji+'">'+
          '<button class="btn" onclick="mAccept('+ri+','+ji+')">✓ Accept '+j.marks_awarded+'</button>'+
          '<input type="number" id="ov-'+ri+'-'+ji+'" min="0" max="'+j.marks_available+'" step="0.5" placeholder="mark" aria-label="override mark for '+esc(j.question)+'">'+
          '<input type="text" id="ovr-'+ri+'-'+ji+'" placeholder="reason (required to override)" aria-label="override reason">'+
          '<button class="btn ghost" onclick="mOverride('+ri+','+ji+')">Override</button></div>'
        :'';
      rows+='<tr id="row-'+ri+'-'+ji+'"'+(j._review?' class="flag"':'')+'><td><b>'+esc(j.question)+'</b>'+
        (j._review?' <span class="chip review" title="'+esc(flags)+'">review</span>':'')+'</td>'+
        '<td class="num" id="mark-'+ri+'-'+ji+'">'+j.marks_awarded+' / '+j.marks_available+'</td>'+
        '<td class="num">'+Math.round(j.confidence*100)+'%</td>'+
        '<td>'+esc(j.transcription||'')+'</td>'+
        '<td>'+esc(j.evidence||'')+'</td>'+
        '<td>'+esc(j.feedback||'')+(flags?'<div class="hint">⚠ '+esc(flags)+'</div>':'')+ctl+'</td></tr>';
    });
    cards+='<div class="card" id="mcard-'+ri+'"><h3>'+esc(r.student_label)+' <span class="muted">('+esc(r._file)+')</span>'+
      ' <span class="sum-chip" id="mstate-'+ri+'"></span></h3>'+
      '<p><span class="mark-total" id="mtotal-'+ri+'"></span></p>'+
      '<div class="mx"><table class="marks"><tr><th>Q</th><th>Marks</th><th>Conf.</th><th>Transcription</th><th>Evidence</th><th>Feedback / review</th></tr>'+
      rows+'</table></div></div>';
  });
  el.innerHTML='<h2 class="section">Proposed marks — review before export</h2>'+
    '<div class="card" id="mgate"><p id="mgate-msg"></p>'+
    '<div class="aim-actions">'+
    '<span class="filters"><button class="on" onclick="setMFilter(\'all\',this)">All</button>'+
    '<button onclick="setMFilter(\'todo\',this)">Needs review</button>'+
    '<button onclick="setMFilter(\'done\',this)">Resolved</button></span>'+
    '<button class="btn ghost" onclick="mAcceptAll()">✓ Accept all remaining flagged</button>'+
    '<button class="btn" id="mexport" onclick="exportMarks()">⬇ Export finalised marks (.csv)</button></div>'+
    '<p class="hint">The export includes proposed vs final marks, transcription, evidence, review flags and your override reasons — a complete audit trail.</p></div>'+
    cards+
    '<p class="foot">AI marks are proposals — you are the marker of record. Every flagged item must be accepted or overridden before the export unlocks.</p>';
  el.classList.add('active');el.scrollIntoView({behavior:'smooth'});
  paintMarks();
}
let MFILTER='all';
function setMFilter(f,btn){MFILTER=f;
  document.querySelectorAll('#mgate .filters button').forEach(b=>b.classList.toggle('on',b===btn));paintMarks()}
function mAcceptAll(){
  let n=0;MRES.forEach((r,ri)=>{if(r._error)return;r.judgements.forEach(j=>{
    if(j._review&&!MREV[mkey(ri,j)])n++})});
  if(!n)return;
  if(!confirm('Accept the AI\'s proposed mark for all '+n+' remaining flagged item(s)?\n\nOnly do this after you have actually looked at them — this records each as teacher-accepted.'))return;
  MRES.forEach((r,ri)=>{if(r._error)return;r.judgements.forEach(j=>{
    if(j._review&&!MREV[mkey(ri,j)])MREV[mkey(ri,j)]={final:j.marks_awarded,reason:'',action:'accepted (bulk)'}})});
  paintMarks();
}
function mAccept(ri,ji){
  const j=MRES[ri].judgements[ji];
  MREV[mkey(ri,j)]={final:j.marks_awarded,reason:'',action:'accepted'};
  paintMarks();
}
function mOverride(ri,ji){
  const j=MRES[ri].judgements[ji];
  const v=parseFloat($('ov-'+ri+'-'+ji).value);
  const reason=$('ovr-'+ri+'-'+ji).value.trim();
  if(isNaN(v)||v<0||v>j.marks_available){alert('Enter a mark between 0 and '+j.marks_available);return}
  if(!reason){alert('An override needs a reason — it goes into the audit trail.');return}
  MREV[mkey(ri,j)]={final:v,reason,action:'overridden'};
  paintMarks();
}
function mUndo(ri,ji){delete MREV[mkey(ri,MRES[ri].judgements[ji])];paintMarks()}
function paintMarks(){
  let open=0,total=0;
  MRES.forEach((r,ri)=>{
    if(r._error)return;
    let aw=0,av=0,pend=0;
    r.judgements.forEach((j,ji)=>{
      const d=MREV[mkey(ri,j)];
      const final=d?d.final:j.marks_awarded;
      av+=j.marks_available;aw+=final;
      const row=$('row-'+ri+'-'+ji),ctl=$('ctl-'+ri+'-'+ji),mk=$('mark-'+ri+'-'+ji);
      if(row){const resolved=!j._review||!!d;
        row.style.display=(MFILTER==='all'||(MFILTER==='todo'&&j._review&&!d)||(MFILTER==='done'&&j._review&&!!d))?'':'none';
        if(MFILTER==='all')row.style.display='';}
      if(j._review){total++;
        if(d){row.classList.remove('flag');
          if(ctl)ctl.innerHTML='<span class="chip" style="border-color:var(--accent);color:var(--accent)">'+
            (d.action==='accepted'?'✓ accepted':'✎ overridden → '+d.final+(d.reason?' — '+esc(d.reason):''))+
            '</span> <button class="mini" onclick="mUndo('+ri+','+ji+')">↺</button>';
          if(mk)mk.textContent=final+' / '+j.marks_available;
        }else{pend++;open++}
      }
    });
    const st=$('mstate-'+ri),tt=$('mtotal-'+ri);
    if(tt)tt.textContent=aw+' / '+av+(av?' ('+Math.round(100*aw/av)+'%)':'');
    if(st){st.textContent=pend?pend+' to review':'✓ finalised';st.className='sum-chip '+(pend?'bad':'ok')}
  });
  const gate=$('mgate-msg'),btn=$('mexport');
  if(gate){gate.innerHTML=open
    ?'⚠ <b>'+open+'</b> flagged item(s) still need your decision — the export unlocks when every one is accepted or overridden.'
    :'✓ All flagged items reviewed ('+total+' decision(s) recorded). The finalised export is ready.'}
  if(btn)btn.disabled=open>0;
}
function exportMarks(){
  let csv='student,file,question,proposed_marks,final_marks,marks_available,confidence,'+
    'review_required,review_flags,teacher_action,override_reason,transcription,evidence,feedback\n';
  MRES.forEach((r,ri)=>{
    if(r._error)return;
    r.judgements.forEach(j=>{
      const d=MREV[mkey(ri,j)];
      csv+=[JSON.stringify(r.student_label),JSON.stringify(r._file),JSON.stringify(j.question),
        j.marks_awarded,(d?d.final:j.marks_awarded),j.marks_available,j.confidence,
        j._review,JSON.stringify((j._flags||[]).join('; ')),
        JSON.stringify(d?d.action:(j._review?'':'auto-accepted')),
        JSON.stringify(d?d.reason:''),
        JSON.stringify(j.transcription||''),JSON.stringify(j.evidence||''),
        JSON.stringify(j.feedback||'')].join(',')+'\n';
    });
  });
  dlBlob(csv,'marks_finalised.csv','text/csv');
}
