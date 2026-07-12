function $(id){return document.getElementById(id)}
function navToggle(){const n=document.querySelector('.nav');const open=n.classList.toggle('open');$('nav-toggle').setAttribute('aria-expanded',open)}
function show(view, btn){
  const n=document.querySelector('.nav');if(n)n.classList.remove('open');
  document.querySelectorAll('.view').forEach(v=>v.classList.toggle('active', v.id==='view-'+view));
  document.querySelectorAll('.iframe-wrap').forEach(f=>f.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(b=>b.classList.remove('active'));
  if(btn) btn.classList.add('active');
  else if(view==='home') document.querySelector('.nav-item[data-view=home]').classList.add('active');
}
function openReportByFile(file){
  const btn=document.querySelector('.nav-item[data-file="'+file+'"]');
  if(btn){btn.scrollIntoView({block:'nearest'});openReport(btn);}
}
function openReport(btn){
  document.querySelectorAll('.view').forEach(v=>v.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  const file=btn.dataset.file;
  // pick the matching frame by data-file; embedded frames carry srcdoc already,
  // linked frames lazy-load their sibling file on first open.
  let shown=null;
  document.querySelectorAll('.iframe-wrap iframe').forEach(fr=>{
    if(fr.dataset.file===file){const w=fr.closest('.iframe-wrap');w.classList.add('active');
      if(!fr.getAttribute('srcdoc') && fr.dataset.src && !fr.src) fr.src=fr.dataset.src;
      shown=w;}
  });
  document.querySelectorAll('.iframe-wrap').forEach(w=>{if(w!==shown)w.classList.remove('active')});
}

/* ---------- ZIP (store + deflate-raw) reader, no libraries ---------- */
async function inflateRaw(bytes){
  if(bytes.length===0) return new Uint8Array();
  const ds=new DecompressionStream('deflate-raw');
  const stream=new Blob([bytes]).stream().pipeThrough(ds);
  return new Uint8Array(await new Response(stream).arrayBuffer());
}
async function readZip(buf){
  const dv=new DataView(buf), u8=new Uint8Array(buf);
  // find End Of Central Directory
  let eocd=-1;
  for(let i=u8.length-22;i>=0;i--){if(dv.getUint32(i,true)===0x06054b50){eocd=i;break}}
  if(eocd<0) throw new Error('not a valid .xlsx/.docx (no ZIP directory)');
  let n=dv.getUint16(eocd+10,true), off=dv.getUint32(eocd+16,true);
  const entries={};
  for(let e=0;e<n;e++){
    if(dv.getUint32(off,true)!==0x02014b50) break;
    const method=dv.getUint16(off+10,true);
    const compSize=dv.getUint32(off+20,true);
    const fnLen=dv.getUint16(off+28,true), exLen=dv.getUint16(off+30,true), cmLen=dv.getUint16(off+32,true);
    const lho=dv.getUint32(off+42,true);
    const name=new TextDecoder().decode(u8.subarray(off+46,off+46+fnLen));
    // local header to locate data
    const lfn=dv.getUint16(lho+26,true), lex=dv.getUint16(lho+28,true);
    const start=lho+30+lfn+lex;
    const comp=u8.subarray(start,start+compSize);
    entries[name]={method,comp};
    off+=46+fnLen+exLen+cmLen;
  }
  return {
    async text(name){const en=entries[name];if(!en)return null;
      const raw=en.method===0?en.comp:await inflateRaw(en.comp);
      return new TextDecoder().decode(raw);}
  };
}

/* ---------- XLSX → sheets of 2D cell grids ---------- */
function colToIdx(ref){let s=ref.replace(/[0-9]/g,''),n=0;for(const ch of s)n=n*26+(ch.charCodeAt(0)-64);return n-1}
async function parseXlsx(buf){
  const zip=await readZip(buf);
  const P=new DOMParser();
  const ss=[]; const sst=await zip.text('xl/sharedStrings.xml');
  if(ss!==null && sst){const d=P.parseFromString(sst,'application/xml');
    d.querySelectorAll('si').forEach(si=>{ let t='';si.querySelectorAll('t').forEach(x=>t+=x.textContent);ss.push(t)});}
  const rels=await zip.text('xl/_rels/workbook.xml.rels');
  const relMap={}; if(rels){const d=P.parseFromString(rels,'application/xml');
    d.querySelectorAll('Relationship').forEach(r=>relMap[r.getAttribute('Id')]=r.getAttribute('Target'));}
  const wbx=await zip.text('xl/workbook.xml');
  const sheets=[]; const d=P.parseFromString(wbx,'application/xml');
  d.querySelectorAll('sheets > sheet').forEach(sh=>{
    const rid=sh.getAttribute('r:id')||sh.getAttributeNS('http://schemas.openxmlformats.org/officeDocument/2006/relationships','id');
    let tgt=relMap[rid]||'';
    if(tgt.startsWith('/')) tgt=tgt.slice(1);          // absolute (openpyxl): /xl/worksheets/… → xl/worksheets/…
    else if(tgt && !tgt.startsWith('xl/')) tgt='xl/'+tgt; // relative to xl/
    sheets.push({name:sh.getAttribute('name'), path:tgt});
  });
  const out=[];
  for(const s of sheets){
    const xml=await zip.text(s.path); if(!xml) continue;
    const sd=P.parseFromString(xml,'application/xml'); const grid={};
    sd.querySelectorAll('sheetData > row').forEach(row=>{
      const r=parseInt(row.getAttribute('r'));
      row.querySelectorAll('c').forEach(c=>{
        const ref=c.getAttribute('r'); const t=c.getAttribute('t');
        let v=null; const vEl=c.querySelector('v'); const isEl=c.querySelector('is');
        if(t==='s' && vEl){v=ss[parseInt(vEl.textContent)]}
        else if(t==='inlineStr'&&isEl){v='';isEl.querySelectorAll('t').forEach(x=>v+=x.textContent)}
        else if(vEl){const num=parseFloat(vEl.textContent);v=isNaN(num)?vEl.textContent:num}
        if(v!==null){(grid[r]=grid[r]||{})[colToIdx(ref)]=v}
      });
    });
    out.push({name:s.name, grid});
  }
  return out;
}
