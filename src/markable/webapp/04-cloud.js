/* ================= AI cloud: provider, keys, transport, upgrade, marking =================
   Credential policy (P0): keys live in sessionStorage (gone when the tab closes)
   unless the teacher explicitly ticks "remember on this device". Legacy keys
   found in localStorage without that opt-in are migrated to session storage.
   Keys are never written into any exported file. */
function scrollToEl(id){const el=$(id);if(el)el.scrollIntoView({behavior:'smooth',block:'center'})}
const KEY_STORE='markable_api_key';           // Anthropic key
const CP_EP_STORE='markable_cp_endpoint';     // Copilot / Azure OpenAI endpoint + key
const CP_KEY_STORE='markable_cp_key';
const PROV_STORE='markable_provider';
const REMEMBER_STORE='markable_remember_creds';
const HOSTS_STORE='markable_allowed_hosts';
function rememberOn(){return localStorage.getItem(REMEMBER_STORE)==='1'}
function credStore(){return rememberOn()?localStorage:sessionStorage}
function credGet(k){return (credStore().getItem(k)||'').trim()}
function credSet(k,v){credStore().setItem(k,v);(rememberOn()?sessionStorage:localStorage).removeItem(k)}
(function migrateLegacyCreds(){
  // pre-policy versions persisted keys in localStorage unconditionally
  if(rememberOn())return;
  [KEY_STORE,CP_EP_STORE,CP_KEY_STORE].forEach(k=>{
    const v=localStorage.getItem(k);
    if(v!==null){sessionStorage.setItem(k,v);localStorage.removeItem(k)}
  });
})();
function clearCreds(){
  [KEY_STORE,CP_EP_STORE,CP_KEY_STORE].forEach(k=>{localStorage.removeItem(k);sessionStorage.removeItem(k)});
  localStorage.removeItem(REMEMBER_STORE);
  ['api-key','cp-endpoint','cp-key'].forEach(id=>{const e=$(id);if(e)e.value=''});
  ['key-status','key-status2'].forEach(id=>{const e=$(id);if(e){e.className='status';e.textContent='Keys cleared from this browser.'}});
}
let PROVIDER=localStorage.getItem(PROV_STORE)||'claude';
function setProvider(p){
  PROVIDER=p;localStorage.setItem(PROV_STORE,p);
  const c=$('prov-claude'),o=$('prov-copilot');
  if(c){c.classList.toggle('on',p==='claude');o.classList.toggle('on',p==='copilot');
    $('keys-claude').style.display=p==='claude'?'flex':'none';
    $('keys-copilot').style.display=p==='copilot'?'flex':'none';}
  document.querySelectorAll('.prov-name').forEach(e=>e.textContent=p==='copilot'?'Copilot':'Claude');
}
function getKey(){return credGet(KEY_STORE)}
function getCp(){return {endpoint:credGet(CP_EP_STORE),key:credGet(CP_KEY_STORE)}}
/* Custom endpoints: HTTPS only, and the hostname must be on the allowlist
   (Azure OpenAI / OpenAI by default; anything else needs explicit teacher
   confirmation, and is then remembered per this browser). */
const DEFAULT_HOST_SUFFIXES=['.openai.azure.com','.azure.com','.azure-api.net','api.openai.com'];
function allowedHosts(){try{return JSON.parse(localStorage.getItem(HOSTS_STORE)||'[]')}catch(e){return []}}
function validateEndpoint(url){
  let u;
  try{u=new URL(url)}catch(e){return {ok:false,msg:'That is not a valid URL.'}}
  if(u.protocol!=='https:')return {ok:false,msg:'Endpoint must use HTTPS — keys must never travel over plain HTTP.'};
  const host=u.hostname;
  const known=DEFAULT_HOST_SUFFIXES.some(s=>host===s||host.endsWith(s))||allowedHosts().includes(host);
  if(!known){
    if(!confirm('The endpoint host "'+host+'" is not a recognised Azure OpenAI / OpenAI domain.\n\n'+
      'Your API key and assessment content will be sent to this host. Only continue if your IT team gave you this exact address.\n\nAllow '+host+'?'))
      return {ok:false,msg:'Endpoint not saved — host "'+host+'" was not approved.'};
    const hosts=allowedHosts();hosts.push(host);localStorage.setItem(HOSTS_STORE,JSON.stringify(hosts));
  }
  return {ok:true,host};
}
function endpointHost(){try{return new URL(getCp().endpoint).hostname}catch(e){return ''}}
function saveKey(){
  const rem=$('remember-creds');
  if(rem)localStorage.setItem(REMEMBER_STORE,rem.checked?'1':'0');
  if(PROVIDER==='claude'){
    credSet(KEY_STORE,$('api-key').value.trim());
    const s=$('key-status');s.className='status';
    s.textContent=getKey()?(rememberOn()?'✓ Saved on this device.':'✓ Saved for this session only (cleared when the tab closes).'):'Cleared.';
  }else{
    const ep=$('cp-endpoint').value.trim();
    if(ep){const v=validateEndpoint(ep);
      if(!v.ok){const s=$('key-status2');s.className='status err';s.textContent=v.msg;return}}
    credSet(CP_EP_STORE,ep);
    credSet(CP_KEY_STORE,$('cp-key').value.trim());
    const s=$('key-status2');s.className='status';
    s.textContent=(getCp().endpoint&&getCp().key)
      ?('✓ Saved'+(rememberOn()?' on this device':' for this session')+' — data will go to '+endpointHost()+'.')
      :'Cleared.';
  }
}
function haveCreds(){return PROVIDER==='claude'?!!getKey():!!(getCp().endpoint&&getCp().key)}
function needKey(){
  if(haveCreds())return true;
  show('aimark');scrollToEl('prov-claude');
  const s=$(PROVIDER==='claude'?'key-status':'key-status2');s.className='status err';
  s.textContent=PROVIDER==='claude'
    ?'Add your Anthropic API key first — the cloud steps need it.'
    :'Add your Copilot/Azure OpenAI endpoint URL and key first.';
  return false;
}
/* ---- consent gate: nothing goes to the cloud without an explicit OK ---- */
function cloudDestination(){
  return PROVIDER==='claude'
    ?{provider:'Claude (Anthropic)',host:'api.anthropic.com'}
    :{provider:'Copilot / Azure OpenAI',host:endpointHost()||'(no endpoint saved)'};
}
function cloudConsent(action,items){
  // items: list of strings describing exactly what will be sent
  return new Promise(resolve=>{
    const d=cloudDestination();
    const old=$('consent-overlay');if(old)old.remove();
    const ov=document.createElement('div');ov.id='consent-overlay';
    ov.innerHTML='<div class="consent" role="dialog" aria-modal="true" aria-labelledby="consent-h">'+
      '<h3 id="consent-h">☁️ Send to '+esc(d.provider)+'?</h3>'+
      '<p>'+esc(action)+' will send the following from this browser to <b>'+esc(d.host)+'</b> over HTTPS:</p>'+
      '<ul>'+items.map(i=>'<li>'+esc(i)+'</li>').join('')+'</ul>'+
      '<p class="consent-warn">Check for student names first: use student IDs on scans and cover any names. '+
      'If you cannot, get school approval before sending. Nothing is sent until you confirm.</p>'+
      '<div class="aim-actions"><button class="btn" id="consent-ok">Send to '+esc(d.host)+'</button>'+
      '<button class="btn ghost" id="consent-no">Cancel</button></div></div>';
    document.body.appendChild(ov);
    $('consent-ok').focus();
    $('consent-ok').onclick=()=>{ov.remove();resolve(true)};
    $('consent-no').onclick=()=>{ov.remove();resolve(false)};
    ov.addEventListener('keydown',e=>{
      if(e.key==='Escape'){ov.remove();resolve(false)}
      if(e.key==='Tab'){e.preventDefault();
        (document.activeElement===$('consent-ok')?$('consent-no'):$('consent-ok')).focus()}
    });
  });
}
/* ---- transport: one entry point, two providers; one retry on rate-limit/5xx ---- */
async function callAI(opts){  // {system, schema, content(anthropic blocks)}
  const fn=PROVIDER==='claude'?callClaude:callOpenAI;
  try{return await fn(opts)}
  catch(e){
    if(/429|500|529|overloaded|rate limit/i.test(String(e.message))){
      await new Promise(r=>setTimeout(r,2500));
      return await fn(opts);   // one retry, then surface the error
    }
    throw e;
  }
}
async function callClaude(opts){
  // Direct browser → Anthropic; the CORS opt-in header acknowledges the key
  // lives client-side (it is the teacher's own key, stored only locally).
  const res=await fetch('https://api.anthropic.com/v1/messages',{
    method:'POST',
    headers:{'content-type':'application/json','x-api-key':getKey(),
      'anthropic-version':'2023-06-01','anthropic-dangerous-direct-browser-access':'true'},
    body:JSON.stringify({model:AI_MODELS.claude,max_tokens:16000,thinking:{type:'adaptive'},
      system:[{type:'text',text:opts.system,cache_control:{type:'ephemeral'}}],
      output_config:{format:{type:'json_schema',schema:opts.schema}},
      messages:[{role:'user',content:opts.content}]})});
  const data=await res.json().catch(()=>({}));
  if(!res.ok){throw new Error((data.error&&data.error.message)||('API error '+res.status))}
  if(data.stop_reason==='refusal')throw new Error('the model declined to process this document');
  const block=(data.content||[]).find(b=>b.type==='text');
  if(!block)throw new Error('no text in the response');
  return JSON.parse(block.text);
}
async function callOpenAI(opts){
  // OpenAI-compatible chat-completions endpoint (Azure OpenAI / a workplace
  // Copilot gateway). Anthropic content blocks are converted; JSON is enforced
  // via json_object mode + the schema inlined in the prompt.
  const cp=getCp();
  if(!/^https:/i.test(cp.endpoint))throw new Error('the saved endpoint is not HTTPS — re-save it under Claude / Copilot setup');
  const content=[];
  for(const b of opts.content){
    if(b.type==='text')content.push({type:'text',text:b.text});
    else if(b.type==='image')content.push({type:'image_url',
      image_url:{url:'data:'+b.source.media_type+';base64,'+b.source.data}});
    else if(b.type==='document')
      throw new Error('PDF scans need Claude — with Copilot/Azure OpenAI, upload scans as images (PNG/JPG), or switch provider.');
  }
  const headers={'content-type':'application/json'};
  if(/azure|\bapi-key\b/i.test(cp.endpoint))headers['api-key']=cp.key;
  else headers['authorization']='Bearer '+cp.key;
  const res=await fetch(cp.endpoint,{method:'POST',headers,body:JSON.stringify({
    messages:[{role:'system',content:opts.system+'\n\nRespond ONLY with a JSON object matching this schema:\n'+JSON.stringify(opts.schema)},
      {role:'user',content}],
    response_format:{type:'json_object'},max_tokens:8000})});
  const data=await res.json().catch(()=>({}));
  if(!res.ok){throw new Error((data.error&&data.error.message)||('endpoint error '+res.status+
    ' — if this is a CORS/network error, your workplace endpoint may not allow browser calls; ask IT or use Claude'))}
  const text=data.choices&&data.choices[0]&&data.choices[0].message&&data.choices[0].message.content;
  if(!text)throw new Error('no content in the response');
  return JSON.parse(text);
}
let CLOUD_CANCEL=false;
function busy(el,msg,cancellable){
  el.innerHTML='<div class="card"><p><span class="spin"></span>'+esc(msg)+
  ' <span class="muted">(can take a minute — the AI is thinking)</span>'+
  (cancellable?' <button class="btn ghost" onclick="CLOUD_CANCEL=true;this.textContent=\'Cancelling…\'">Cancel</button>':'')+
  '</p></div>';el.classList.add('active')}
function dlButton(label,content,fname,mime){
  const id='dl'+Math.random().toString(36).slice(2,8);
  setTimeout(()=>{const b=$(id);if(b)b.onclick=()=>{
    const a=document.createElement('a');
    a.href=URL.createObjectURL(new Blob([content],{type:mime||'text/plain'}));
    a.download=fname;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),2000)}},0);
  return '<button class="btn" id="'+id+'">'+esc(label)+'</button>';
}
