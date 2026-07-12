(function(){
  const k=$('api-key');if(k&&getKey())k.value=getKey();
  const ep=$('cp-endpoint'),ck=$('cp-key');
  if(ep)ep.value=getCp().endpoint; if(ck)ck.value=getCp().key;
  setProvider(PROVIDER);
  const rc=$('remember-creds');if(rc)rc.checked=rememberOn();
  document.querySelectorAll('.prov-name').forEach(e=>e.textContent=provName());
})();
