/* ---------- rubric builder: test → editable marking key → key.yaml / print ---------- */
let RUB_DOC=null,RUB=null;
wireDrop('drop-rub','drop-rub-input',async file=>{
  const st=$('rub-status');st.className='status';st.textContent='Reading '+file.name+' …';
  try{
    const text=await docText(file.name,await file.arrayBuffer());
    if(!text.trim())throw new Error('No readable text found in that document.');
    RUB_DOC={name:file.name,text};
    st.textContent='✓ '+file.name+docWarnSuffix();
    $('rub-result').innerHTML='<div class="card"><div class="optways">'+
      '<div class="optway"><h4>Option A — draft it right here</h4>'+
      '<p class="hint">Uses your saved API key (<span class="prov-name">'+esc(provName())+'</span>).</p>'+
      '<div class="aim-actions" style="margin:8px 0 0"><button class="btn" onclick="genRubric()">📐 Draft the marking key</button></div></div>'+
      '<div class="optway"><h4>Option B — use your own AI, no key</h4>'+
      '<p class="hint">Get a packaged prompt; paste the YAML the AI returns straight back as key.yaml.</p>'+
      '<div class="aim-actions" style="margin:8px 0 0"><select id="rub-chat-ai" class="picker" style="margin:0">'+
      '<option value="claude">Claude (claude.ai)</option><option value="chatgpt">ChatGPT (chatgpt.com)</option>'+
      '<option value="copilot">Copilot (copilot.microsoft.com)</option></select>'+
      '<button class="btn" onclick="genRubricPrompt()">📋 Generate the prompt</button></div></div>'+
      '</div></div>';
    $('rub-result').classList.add('active');
  }catch(err){st.className='status err';st.textContent='Could not read that file: '+err.message}
});
async function genRubric(){
  if(!RUB_DOC){scrollToEl('drop-rub');return}
  if(!needKey()){show('rubric');return}
  if(!await cloudConsent('Drafting the marking key',['The full text extracted from “'+RUB_DOC.name+'”']))return;
  const el=$('rub-result');busy(el,'Drafting the marking key for “'+RUB_DOC.name+'” with '+provName()+'…');
  try{
    RUB=await callAI({system:RUBRIC_PACK,schema:RUBRIC_SCHEMA,
      content:[{type:'text',text:'Draft the marking key for this test:\n\n'+RUB_DOC.text}]});
    renderRubricEditor();
  }catch(err){el.innerHTML='<div class="card"><p class="status err" style="display:block">Rubric drafting failed: '+esc(err.message)+'</p></div>'}
}
function critRow(qi,ci,c){
  return '<div class="crit-row" data-q="'+qi+'">'+
    '<input class="crit-point" value="'+esc(c.point)+'" placeholder="what earns the mark">'+
    '<input class="crit-marks" type="number" min="0" step="1" value="'+c.marks+'">'+
    '<button class="mini" onclick="this.parentNode.remove();sumCheck('+qi+')" title="remove">✕</button></div>';
}
function bandRow(b){
  return '<div class="band-row"><input class="band-name" value="'+esc(b.band)+'" placeholder="band">'+
    '<input class="band-desc" value="'+esc(b.descriptor)+'" placeholder="descriptor">'+
    '<button class="mini" onclick="this.parentNode.remove()" title="remove">✕</button></div>';
}
function renderRubricEditor(){
  const el=$('rub-result');
  const verify=(RUB.verify||[]).map(v=>'<li><b>'+esc(v.question_id)+'</b> — '+esc(v.note)+'</li>').join('');
  let cards='';
  RUB.questions.forEach((q,qi)=>{
    let extra='';
    if(q.type==='mcq'){
      const notes=(q.distractor_notes||[]).map(d=>'<div class="band-row"><input class="dn-opt" value="'+esc(d.option)+'" style="width:52px">'+
        '<input class="dn-note" value="'+esc(d.note)+'" placeholder="what this distractor represents"></div>').join('');
      extra='<div class="kv-edit"><label>Correct option</label><input id="rq'+qi+'-correct" value="'+esc(q.correct||'')+'" style="width:64px"></div>'+
        '<label class="sublbl">Distractor notes</label><div id="rq'+qi+'-notes">'+notes+'</div>';
    }
    if(q.type==='numerical'){
      extra='<div class="kv-edit"><label>Final answer</label><input id="rq'+qi+'-final" value="'+esc(q.final_answer||'')+'">'+
        '<label>± tolerance</label><input id="rq'+qi+'-tol" type="number" step="any" value="'+(q.tolerance==null?'':q.tolerance)+'" style="width:90px"></div>';
    }
    let bands='';
    if(q.type==='extended'){
      bands='<label class="sublbl">Rubric bands</label><div id="rq'+qi+'-bands">'+
        (q.rubric||[]).map(bandRow).join('')+'</div>'+
        '<button class="mini add" onclick="$(\'rq'+qi+'-bands\').insertAdjacentHTML(\'beforeend\',bandRow({band:\'\',descriptor:\'\'}))">+ band</button>';
    }
    const crits=(q.criteria||[]).map((c,ci)=>critRow(qi,ci,c)).join('');
    cards+='<div class="card rq" id="rq'+qi+'">'+
      '<h3>'+esc(q.id)+' <span class="muted">['+esc(q.type)+', '+q.marks+' mark'+(q.marks==1?'':'s')+']</span>'+
      ' <span class="sum-chip" id="rq'+qi+'-sum"></span></h3>'+extra+
      (q.type!=='mcq'?'<label class="sublbl">Criteria <span class="muted">(marks must sum to '+q.marks+')</span></label>'+
        '<div id="rq'+qi+'-crit" oninput="sumCheck('+qi+')">'+crits+'</div>'+
        '<button class="mini add" onclick="$(\'rq'+qi+'-crit\').insertAdjacentHTML(\'beforeend\',critRow('+qi+',99,{point:\'\',marks:1}));sumCheck('+qi+')">+ criterion</button>':'')+
      (q.type!=='mcq'?'<div class="kv-edit"><label>Accept</label><input id="rq'+qi+'-accept" value="'+esc((q.accept||[]).join('; '))+'" placeholder="alternative correct answers; separated by ;">'+
        '<label>Reject</label><input id="rq'+qi+'-reject" value="'+esc((q.reject||[]).join('; '))+'" placeholder="common wrong answers; separated by ;"></div>':'')+
      bands+'</div>';
  });
  el.innerHTML='<h2 class="section">Draft marking key — edit anything, then export</h2>'+
    (verify?'<div class="card highlights"><h3>⚠ Verify before marking</h3><ul class="hi-list">'+verify+'</ul></div>':'')+
    '<div class="aim-actions">'+
    '<button class="btn" onclick="downloadKeyYaml()">⬇ key.yaml (for markable mark)</button>'+
    '<select id="rub-fmt" class="picker" style="margin:0"><option value="docx">Printable rubric (.docx)</option><option value="pdf">Printable rubric (.pdf)</option><option value="md">Markdown (.md)</option></select>'+
    '<button class="btn ghost" onclick="downloadRubricDoc()">⬇ Download printable</button>'+
    '<button class="btn ghost" onclick="useKeyInMarking()">Use this key in the marking studio →</button></div>'+
    cards;
  el.classList.add('active');el.scrollIntoView({behavior:'smooth'});
  RUB.questions.forEach((_,qi)=>sumCheck(qi));
}
function sumCheck(qi){
  const box=$('rq'+qi+'-crit'),chip=$('rq'+qi+'-sum');if(!chip)return;
  if(!box){chip.textContent='';return}
  let sum=0;box.querySelectorAll('.crit-marks').forEach(i=>sum+=parseFloat(i.value)||0);
  const want=RUB.questions[qi].marks;
  chip.textContent=sum===want?'✓ marks sum':'⚠ criteria sum '+sum+' of '+want;
  chip.className='sum-chip '+(sum===want?'ok':'bad');
}
function collectRubric(){
  const out={test_id:RUB.test_id,total_marks:0,questions:[]};
  RUB.questions.forEach((q,qi)=>{
    const e={id:q.id,type:q.type,marks:q.marks};
    if(q.type==='mcq'){
      e.correct=($('rq'+qi+'-correct')||{}).value||null;
      const notes={};document.querySelectorAll('#rq'+qi+'-notes .band-row').forEach(r=>{
        const o=r.querySelector('.dn-opt').value.trim(),n=r.querySelector('.dn-note').value.trim();
        if(o&&n)notes[o]=n});
      if(Object.keys(notes).length)e.distractor_notes=notes;
    }else{
      e.criteria=[];document.querySelectorAll('#rq'+qi+'-crit .crit-row').forEach(r=>{
        const p=r.querySelector('.crit-point').value.trim(),m=parseInt(r.querySelector('.crit-marks').value)||0;
        if(p)e.criteria.push({point:p,marks:m})});
      const acc=($('rq'+qi+'-accept')||{}).value||'',rej=($('rq'+qi+'-reject')||{}).value||'';
      e.accept=acc.split(';').map(s=>s.trim()).filter(Boolean);
      e.reject=rej.split(';').map(s=>s.trim()).filter(Boolean);
    }
    if(q.type==='numerical'){
      e.final_answer=($('rq'+qi+'-final')||{}).value||null;
      const t=($('rq'+qi+'-tol')||{}).value;e.tolerance=t===''?null:parseFloat(t);
    }
    if(q.type==='extended'){
      e.rubric=[];document.querySelectorAll('#rq'+qi+'-bands .band-row').forEach(r=>{
        const b=r.querySelector('.band-name').value.trim(),d=r.querySelector('.band-desc').value.trim();
        if(b&&d)e.rubric.push({band:b,descriptor:d})});
    }
    e.review_threshold=(q.type==='extended'||q.type==='diagram')?0.9:0.85;
    out.total_marks+=q.marks;out.questions.push(e);
  });
  return out;
}
function dlBlob(data,fname,mime){
  const a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([data],{type:mime}));
  a.download=fname;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),2000);
}
function downloadKeyYaml(){dlBlob(keyYaml(collectRubric()),'key.yaml','text/yaml')}
function downloadRubricDoc(){
  const k=collectRubric(),md=rubricMd(k),fmt=($('rub-fmt')||{}).value||'docx';
  if(fmt==='docx')dlBlob(mdToDocx(md),k.test_id+'-rubric.docx','application/vnd.openxmlformats-officedocument.wordprocessingml.document');
  else if(fmt==='pdf')dlBlob(mdToPdf(md),k.test_id+'-rubric.pdf','application/pdf');
  else dlBlob(md,k.test_id+'-rubric.md','text/markdown');
}
function useKeyInMarking(){
  const k=collectRubric();
  AIM.key={name:'rubric-builder (edited)',text:keyYaml(k)};
  AIM.structKey=k;
  const st=$('aim-key-status');
  if(st){st.className='status';st.textContent='✓ key from the Rubric builder — reconciliation ON';}
  const dz=$('drop-aim-key');if(dz)dz.classList.add('ok');
  show('aimark');scrollToEl('drop-aim-scans');
}
function rubricChatPack(){
  return RUBRIC_PACK.replace(/Return JSON:[\s\S]*$/,
    'Return the complete marking key as YAML in ONE code block, shaped exactly like:\n'+
    'test_id: ...\ntotal_marks: ...\nquestions:\n- id: Q1\n  type: mcq\n  marks: 1\n  correct: C\n'+
    '  distractor_notes: {A: "...", B: "...", D: "..."}\n- id: Q2\n  type: short_answer\n  marks: 2\n'+
    '  criteria:\n  - point: "..."\n    marks: 1\n  accept: ["..."]\n  reject: ["..."]\n'+
    '(final_answer/tolerance for numerical; rubric bands for extended; omit fields that do not apply.)\n'+
    'After the code block, list anything the teacher must verify.');
}
function genRubricPrompt(){
  if(!RUB_DOC){scrollToEl('drop-rub');return}
  const which=($('rub-chat-ai')&&$('rub-chat-ai').value)||'claude';
  const [name,url]=CHAT_AIS[which];
  const prompt=rubricChatPack()+'\n\n=== THE TEST (extracted by Markable from “'+RUB_DOC.name+'”) ===\n\n'+RUB_DOC.text;
  const el=$('rub-result');
  el.innerHTML='<h2 class="section">Your rubric prompt for '+esc(name)+'</h2>'+
    '<div class="card"><div class="aim-actions">'+
    '<button class="btn" onclick="fallbackCopy($(\'rub-prompt\').textContent,()=>{})">📋 Copy prompt</button>'+
    dlButton('⬇ Download prompt (.txt)',prompt,RUB_DOC.name.replace(/\.[^.]+$/,'')+'.rubric-prompt.txt','text/plain')+
    '<a class="btn ghost" href="'+url+'" target="_blank" rel="noopener">Open '+esc(name)+' ↗</a></div>'+
    '<pre id="rub-prompt" style="white-space:pre-wrap;background:var(--page);border:1px solid var(--border);border-radius:8px;padding:12px;max-height:300px;overflow:auto">'+esc(prompt)+'</pre>'+
    '<h3>Then bring the YAML back</h3>'+
    '<p class="hint" style="margin-top:0">Paste the YAML '+esc(name)+' returned — Markable saves it as key.yaml.</p>'+
    '<textarea id="rub-paste" placeholder="Paste the key.yaml content here…" style="width:100%;min-height:120px;padding:10px;border-radius:8px;border:1px solid var(--border);background:var(--page);color:var(--ink);font:13px/1.5 ui-monospace,monospace"></textarea>'+
    '<div class="aim-actions" style="margin-top:10px"><button class="btn" onclick="rubricPasteBack()">⬇ Save as key.yaml</button></div></div>';
  el.classList.add('active');el.scrollIntoView({behavior:'smooth'});
}
function rubricPasteBack(){
  let t=($('rub-paste')||{}).value||'';t=t.trim().replace(/^```[a-z]*\n?/,'').replace(/\n?```\s*$/,'');
  if(!t)return;dlBlob(t,'key.yaml','text/yaml');
}
