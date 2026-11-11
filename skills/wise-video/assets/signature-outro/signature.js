/* Seconds relative to signature entry; example timing derives from EP10 cues.
   Explicit renderAt(t) is seek-order independent; no timers, network or audio. */
window.signatureConfig={backgroundStart:314.166,sloganEnabled:true,
 cues:{portrait:[0,.65],brand:[.1,.5],topics:[.967,.45],slogan:[4.4,.45,7.55,.25],subscribe:[7.8,.5],bookmark:[7.95,.45],support:[9.6,.4,12.55,.25],bye:[12.767,.45]}};
window.configureSignature=function(options={}){const {cues,...rest}=options;Object.assign(signatureConfig,rest);if(cues)Object.assign(signatureConfig.cues,cues);};
const clamp=v=>Math.max(0,Math.min(1,v));
window.renderAt=function(t){
 if(!Number.isFinite(t)||t<0)throw Error('t must be finite and nonnegative');
 for(const [id,cue] of Object.entries(signatureConfig.cues)){
  const [at,duration,exit,exitDuration=.25]=cue;const enter=1-Math.pow(1-clamp((t-at)/duration),3);
  const leave=exit===undefined?0:clamp((t-exit)/exitDuration);
  const el=document.getElementById(id);const enabled=id!=='slogan'||signatureConfig.sloganEnabled;
  el.style.opacity=enabled?String(enter*(1-leave)):'0';el.style.transform=`translateY(${(1-enter)*18-leave*8}px)`;
  el.dataset.visible=enabled&&enter*(1-leave)>.01?'true':'false';
 }
 window.drawBackground(signatureConfig.backgroundStart+t);document.getElementById('root').dataset.renderTime=t;
};
renderAt(Number(new URLSearchParams(location.search).get('t')||0));
