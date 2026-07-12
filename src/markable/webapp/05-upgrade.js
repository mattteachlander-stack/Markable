/* ---------- upgrade: test + instruction pack → improved test ---------- */
let LAST_DOC=null;
function provName(){return PROVIDER==='copilot'?'Copilot':'Claude'}
async function upgradeTest(resultId){
  if(!LAST_DOC){show('home');scrollToEl('drop-doc');return}
  if(!needKey())return;
  if(!await cloudConsent('Reformatting the test',['The full text extracted from “'+LAST_DOC.name+'”']))return;
  const el=$(resultId);busy(el,'Reformatting “'+LAST_DOC.name+'” with '+provName()+'…');
  try{
    const out=await callAI({system:IMPROVE_PACK,schema:IMPROVE_SCHEMA,
      content:[{type:'text',text:'Upgrade this draft test:\n\n'+LAST_DOC.text}]});
    const changes=(out.changes||[]).map(c=>'<li><b>'+esc(c.question_id)+'</b> — '+esc(c.change)+
      ' <span class="muted">('+esc(c.reason)+')</span></li>').join('');
    const fname=LAST_DOC.name.replace(/\.[^.]+$/,'')+'.teacher-master.md';
    el.innerHTML='<h2 class="section">✨ Upgraded test</h2>'+
      '<div class="card"><p style="margin-top:0">'+esc(out.summary||'')+'</p>'+
      '<div class="aim-actions">'+dlButton('⬇ Teacher master (.md — contains answer markers)',out.improved_markdown,fname,'text/markdown')+
      '<button class="btn ghost" onclick="OPT_DOC=LAST_DOC;show(\'optimise\')">Need a student copy? Use the optimiser →</button></div>'+
      '<p class="hint">⚠ The teacher master marks each correct MCQ option with a trailing *. '+
      'Never hand this file to students — the Assessment optimiser exports an answer-stripped student copy.</p>'+
      '<h3>What changed <span class="muted">(verify anything inferred)</span></h3>'+
      '<ul class="changes">'+changes+'</ul>'+
      '<h3>Preview</h3><pre style="white-space:pre-wrap;background:var(--page);border:1px solid var(--border);border-radius:8px;padding:12px;max-height:420px;overflow:auto">'+
      esc(out.improved_markdown)+'</pre>'+
      '<p class="foot">Review the changes, then run <code>markable ingest</code> → <code>markable build</code> on the downloaded file for a scan-ready paper + marking key.</p></div>';
    el.classList.add('active');el.scrollIntoView({behavior:'smooth'});
  }catch(err){el.innerHTML='<div class="card"><p class="status err" style="display:block">Upgrade failed: '+esc(err.message)+'</p></div>'}
}
function upgradeFromAim(){
  if(AIM.test){LAST_DOC=AIM.test;upgradeTest('aim-result')}
  else if(LAST_DOC){upgradeTest('aim-result')}
  else{const s=$('aim-test-status');s.className='status err';s.textContent='Add the test first (step 1).'}
}
