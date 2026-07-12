/* ---------- assessment optimiser: readiness → optimise → before/after ----------
   STUDENT/TEACHER SEPARATION (P0): the optimised markdown is the TEACHER MASTER
   (correct MCQ options carry a trailing *, which `markable ingest` needs to
   build the key). Student exports strip every answer marker and are then run
   through a leak detector; any remaining indicator BLOCKS the download. */
let OPT_DOC=null,OPT_OUT=null;
const OPT_FMTS={md:['Markdown (.md) — ready for markable ingest','text/markdown','.md'],
  docx:['Word (.docx)','application/vnd.openxmlformats-officedocument.wordprocessingml.document','.docx'],
  pdf:['PDF (.pdf)','application/pdf','.pdf']};
function fmtSelector(){return '<select id="opt-aud" class="picker" style="margin:0" aria-label="who is this copy for">'+
  '<option value="student">Student copy (answers stripped)</option>'+
  '<option value="teacher">Teacher master (contains answers)</option></select>'+
  '<select id="opt-fmt" class="picker" style="margin:0">'+
  Object.keys(OPT_FMTS).map(k=>'<option value="'+k+'">'+esc(OPT_FMTS[k][0])+'</option>').join('')+'</select>'}
function downloadOpt(){
  if(!OPT_OUT)return;
  const aud=($('opt-aud')&&$('opt-aud').value)||'student';
  const fmt=($('opt-fmt')&&$('opt-fmt').value)||'md';
  const [_,mime,ext]=OPT_FMTS[fmt];
  let md,label,suffix;
  if(aud==='student'){
    md=stripAnswerMarkers(OPT_OUT.md);
    const leaks=detectAnswerLeaks(md);
    const box=$('leak-box');
    if(leaks.length){
      if(box){box.style.display='block';
        box.innerHTML='<b>⛔ Student download blocked — possible answers detected:</b><ul>'+
          leaks.map(l=>'<li>'+esc(l)+'</li>').join('')+
          '</ul>Edit the test (download the teacher master, fix it, re-optimise) or export the teacher master instead.';}
      return;
    }
    if(box)box.style.display='none';
    label='STUDENT COPY';suffix='.STUDENT';
  }else{
    md=OPT_OUT.md;label='TEACHER MASTER — CONTAINS ANSWERS · not for students';suffix='.TEACHER-MASTER';
  }
  const body=(fmt==='md'&&aud==='teacher')?md:('# '+label+'\n'+md);  // ingest master stays clean
  const data=fmt==='docx'?mdToDocx(body):fmt==='pdf'?mdToPdf(body):body;
  const a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([data],{type:mime}));
  a.download=OPT_OUT.base+suffix+ext;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),2000);
}
function gauge(score){return '<div class="gauge" style="--v:'+score+'"><span>'+score+'%</span></div>'}
wireDrop('drop-opt','drop-opt-input',async file=>{
  const st=$('opt-status');st.className='status';st.textContent='Checking '+file.name+' …';
  try{
    const text=await docText(file.name,await file.arrayBuffer());
    if(!text.trim())throw new Error('No readable text found in that document.');
    OPT_DOC={name:file.name,text};
    const rep=analyseReadiness(text);
    OPT_DOC.before=rep.score;
    const items=rep.checks.map(c=>'<li class="'+(c[1]?'li-good':'li-warn')+'">'+
      '<b>'+esc(c[0])+'</b> — '+esc(c[1]?c[2]:c[3])+'</li>').join('');
    $('opt-result').innerHTML='<h2 class="section">Step 2 — readiness check</h2>'+
      '<div class="card"><div class="readiness">'+gauge(rep.score)+
      '<div><p style="margin:0 0 6px"><b>'+esc(file.name)+'</b> — '+rep.questions+' questions found, '+
      rep.withMarks+' with marks allocated.</p>'+
      '<p style="margin:0;color:var(--ink-2);font-size:13px">The optimiser fixes the items below while preserving your questions, difficulty and topics.</p></div></div>'+
      '<ul style="margin:0 0 14px;padding-left:2px;list-style:none;line-height:1.9">'+items+'</ul>'+
      '<div class="optways">'+
      '<div class="optway"><h4>Option A — optimise right here</h4>'+
      '<p class="hint">Uses the API key you saved (Markable\'s associated AI).</p>'+
      '<div class="aim-actions" style="margin:8px 0 0"><button class="btn" onclick="optimiseNow()">✨ Optimise with <span class="prov-name">'+esc(provName())+'</span></button>'+
      '<button class="btn ghost" onclick="show(\'aimark\');scrollToEl(\'prov-claude\')">Switch AI</button></div></div>'+
      '<div class="optway"><h4>Option B — use your own AI, no key needed</h4>'+
      '<p class="hint">Markable packages the test + optimisation instructions into one prompt you paste into your own AI chat.</p>'+
      '<div class="aim-actions" style="margin:8px 0 0"><select id="chat-ai" class="picker" style="margin:0">'+
      '<option value="claude">Claude (claude.ai)</option>'+
      '<option value="chatgpt">ChatGPT (chatgpt.com)</option>'+
      '<option value="copilot">Copilot (copilot.microsoft.com)</option></select>'+
      '<button class="btn" onclick="genPrompt()">📋 Generate the prompt</button></div></div>'+
      '</div></div>';
    $('opt-result').classList.add('active');
    st.textContent='✓ Readiness '+rep.score+'% — ready to optimise.'+docWarnSuffix();
    $('opt-result').scrollIntoView({behavior:'smooth'});
  }catch(err){st.className='status err';st.textContent='Could not read that file: '+err.message}
});
async function optimiseNow(){
  if(!OPT_DOC){scrollToEl('drop-opt');return}
  if(!needKey()){show('aimark');return}
  if(!await cloudConsent('Optimising the assessment',['The full text extracted from “'+OPT_DOC.name+'”']))return;
  const el=$('opt-result');busy(el,'Optimising “'+OPT_DOC.name+'” with '+provName()+'…');
  try{
    const out=await callAI({system:IMPROVE_PACK,schema:IMPROVE_SCHEMA,
      content:[{type:'text',text:'Upgrade this draft test:\n\n'+OPT_DOC.text}]});
    const changes=(out.changes||[]).map(c=>'<li><b>'+esc(c.question_id)+'</b> — '+esc(c.change)+
      ' <span class="muted">('+esc(c.reason)+')</span></li>').join('');
    renderOptimised(out.improved_markdown,changes,out.summary||'');
  }catch(err){el.innerHTML='<div class="card"><p class="status err" style="display:block">Optimisation failed: '+esc(err.message)+'</p></div>'}
}
function renderOptimised(md,changesHtml,summary){
  const el=$('opt-result');
  const after=analyseReadiness(md).score;
  OPT_OUT={md,base:OPT_DOC.name.replace(/\.[^.]+$/,'')+'.optimised'};
  el.innerHTML='<h2 class="section">Step 4 — optimised assessment</h2>'+
    '<div class="card">'+
    '<div class="beforeafter"><div class="ba"><span class="lbl">Before</span>'+gauge(OPT_DOC.before)+'</div>'+
    '<span class="ba-arrow">→</span>'+
    '<div class="ba"><span class="lbl">After</span>'+gauge(after)+'</div>'+
    '<p style="margin:0;max-width:420px">'+esc(summary)+'</p></div>'+
    '<div class="aim-actions">'+fmtSelector()+
    '<button class="btn" onclick="downloadOpt()">⬇ Download optimised test</button>'+
    '<button class="btn ghost" onclick="show(\'aimark\')">Next: mark scripts against it →</button></div>'+
    '<div id="leak-box" class="status err" role="alert" style="display:none"></div>'+
    '<p class="hint">Student copies have every answer marker stripped and are checked for leaks before '+
    'download; the teacher master keeps the * markers <code>markable ingest</code> needs.</p>'+
    (changesHtml?'<h3>Every change, logged <span class="muted">(verify anything inferred)</span></h3>'+
      '<ul class="changes">'+changesHtml+'</ul>':'')+
    '<h3>Preview</h3><pre style="white-space:pre-wrap;background:var(--page);border:1px solid var(--border);border-radius:8px;padding:12px;max-height:420px;overflow:auto">'+
    esc(md)+'</pre>'+
    '<p class="foot">The after-score is Markable\'s own readiness check re-run on the optimised version. '+
    'For the full pipeline, run <code>markable ingest</code> → <code>markable build</code> on the downloaded file.</p></div>';
  el.classList.add('active');el.scrollIntoView({behavior:'smooth'});
}

/* ---- Option B: no API key — Markable packages a prompt for the teacher's own AI ---- */
const CHAT_AIS={claude:['Claude','https://claude.ai/new'],
  chatgpt:['ChatGPT','https://chatgpt.com/'],
  copilot:['Copilot','https://copilot.microsoft.com/']};
function chatPack(){
  // Same instruction pack as the API path, with the JSON contract swapped for a
  // chat-friendly return format the teacher can read and paste back.
  return IMPROVE_PACK.replace(/Return JSON:[\s\S]*$/,
    'Return three things, in this order:\n'+
    '1. The complete upgraded test, in ONE markdown code block (so it can be copied whole).\n'+
    '2. A change log table: | Question | Change | Why |, one row per change, including every\n'+
    '   inference (marks, MCQ answer, type) the teacher must verify.\n'+
    '3. A 2-3 sentence summary for the teacher.');
}
function buildChatPrompt(){
  return chatPack()+'\n\n=== THE DRAFT TEST (extracted by Markable from “'+OPT_DOC.name+'”) ===\n\n'+OPT_DOC.text;
}
function genPrompt(){
  if(!OPT_DOC){scrollToEl('drop-opt');return}
  const which=($('chat-ai')&&$('chat-ai').value)||'claude';
  const [name,url]=CHAT_AIS[which];
  const prompt=buildChatPrompt();
  const el=$('opt-result');
  el.innerHTML='<h2 class="section">Step 3 — your prompt for '+esc(name)+'</h2>'+
    '<div class="card">'+
    '<p style="margin-top:0">Markable has analysed <b>'+esc(OPT_DOC.name)+'</b>, extracted the text and packaged it '+
    'with the optimisation instructions. Copy it, paste it into '+esc(name)+', and it will return the optimised test.</p>'+
    '<div class="aim-actions">'+
    '<button class="btn" onclick="copyPrompt()">📋 Copy prompt</button>'+
    dlButton('⬇ Download prompt (.txt)',prompt,OPT_DOC.name.replace(/\.[^.]+$/,'')+'.prompt.txt','text/plain')+
    '<a class="btn ghost" href="'+url+'" target="_blank" rel="noopener">Open '+esc(name)+' ↗</a>'+
    '<button class="btn ghost" onclick="$(\'drop-opt-input\').value=\'\';OPT_DOC=null;scrollToEl(\'drop-opt\')">← Start over</button></div>'+
    '<pre id="chat-prompt" style="white-space:pre-wrap;background:var(--page);border:1px solid var(--border);border-radius:8px;padding:12px;max-height:320px;overflow:auto">'+
    esc(prompt)+'</pre>'+
    '<h3>Then bring the result back</h3>'+
    '<p class="hint" style="margin-top:0">Paste the optimised test '+esc(name)+' returned (just the test, from the code block) — '+
    'Markable re-scores it and exports it as Markdown, Word or PDF.</p>'+
    '<textarea id="paste-back" placeholder="Paste the optimised test here…" style="width:100%;min-height:140px;padding:10px;border-radius:8px;border:1px solid var(--border);background:var(--page);color:var(--ink);font:13px/1.5 ui-monospace,monospace"></textarea>'+
    '<div class="aim-actions" style="margin-top:10px"><button class="btn" onclick="pasteBack()">✓ Score &amp; export the result</button></div>'+
    '</div>';
  el.classList.add('active');el.scrollIntoView({behavior:'smooth'});
}
function copyPrompt(){
  const text=buildChatPrompt();
  const done=()=>{const b=event&&event.target;if(b){const t=b.textContent;b.textContent='✓ Copied';setTimeout(()=>b.textContent=t,1600)}};
  if(navigator.clipboard&&navigator.clipboard.writeText){
    navigator.clipboard.writeText(text).then(done).catch(()=>fallbackCopy(text,done));
  }else fallbackCopy(text,done);
}
function fallbackCopy(text,done){
  const ta=document.createElement('textarea');ta.value=text;document.body.appendChild(ta);
  ta.select();try{document.execCommand('copy')}catch(e){}document.body.removeChild(ta);done();
}
function pasteBack(){
  const ta=$('paste-back');let md=(ta&&ta.value||'').trim();
  if(!md)return;
  // tolerate a pasted ``` fence around the test
  md=md.replace(/^```[a-z]*\n?/,'').replace(/\n?```\s*$/,'');
  renderOptimised(md,'','Optimised with your own AI — scored by Markable\'s readiness check.');
}
