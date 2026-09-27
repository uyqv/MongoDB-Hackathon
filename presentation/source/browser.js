const D=window.DECK, stage=document.querySelector('#stage');
const params=new URLSearchParams(location.search), review=params.has('review');
if(review)document.body.classList.add('review');
const el=(tag,attrs={})=>Object.assign(document.createElement(tag),attrs);
function buildItem(v,i){
 let n;
 if(v.type==='text'){
  n=el(v.link?'a':'div',{textContent:v.text});
  if(v.link){n.href=v.link;n.target='_blank';n.rel='noopener';n.style.textDecoration='none'}
  Object.assign(n.style,{fontFamily:v.font,fontWeight:v.weight,fontSize:v.size+'px',color:v.color,textAlign:v.align||'left',lineHeight:v.lineHeight||1.14});
 }else if(v.type==='image'){
  n=el('img',{src:v.src,alt:v.alt,draggable:false});n.classList.add('picture');if(v.motion)n.classList.add(v.motion);
 }else if(v.type==='line'){n=el('div');n.classList.add('rule');n.style.background=v.color;
 }else if(v.type==='memory'){n=el('div');n.classList.add('memory');
 }else if(v.type==='connector'){
  n=el('div');n.innerHTML=`<svg width="${v.w}" height="16" viewBox="0 0 ${v.w} 16" aria-hidden="true"><path d="M0 8 H${v.w-6} M${v.w-14} 1 L${v.w-6} 8 L${v.w-14} 15" stroke="${v.color}" stroke-width="2" fill="none"/></svg>`;n.classList.add('connector');
 }else if(v.type==='chart'){
  const data=v.data.values,lo=Math.floor(Math.min(...data)/10)*10,hi=Math.ceil(Math.max(...data)/10)*10;
  const inner={x:52,y:12,w:v.w-70,h:v.h-46};
  const p=data.map((y,j)=>`${j?'L':'M'}${(inner.x+j/(data.length-1)*inner.w).toFixed(2)},${(inner.y+(hi-y)/(hi-lo)*inner.h).toFixed(2)}`).join(' ');
  const ticks=[lo,(lo+hi)/2,hi].map(y=>{const yy=inner.y+(hi-y)/(hi-lo)*inner.h;return `<line class="grid" x1="52" y1="${yy}" x2="${v.w-18}" y2="${yy}"/><text x="42" y="${yy+7}" text-anchor="end">${y}</text>`}).join('');
  n=el('div');n.classList.add('chart');n.innerHTML=`<svg viewBox="0 0 ${v.w} ${v.h}" role="img" aria-label="Real EEG, channel C3, two seconds, amplitude in microvolts">${ticks}<path d="${p}"/><text x="52" y="${v.h-4}">0 s</text><text x="${v.w-18}" y="${v.h-4}" text-anchor="end">2 s</text></svg>`;
 }else if(v.type==='video'){
  n=el('video',{id:'demoVideo',preload:'metadata',controls:true,playsInline:true,hidden:true});n.classList.add('video');
  if(D.demoReady)n.src=v.src;
  n.addEventListener('ended',()=>toast('Demo complete. Press → to continue.'));
  n.addEventListener('error',()=>{n.hidden=true;toast('The demo could not load. Use “Load demo” to choose second-shift-neuroai-90s-zoom-music.mp4.')});
 }
 n.classList.add('el');if(v.motion)n.classList.add(v.motion);if(!['video','line','connector'].includes(v.type))n.classList.add('reveal');
 Object.assign(n.style,{left:v.x+'px',top:v.y+'px',width:v.w+'px',height:v.h+'px'});
 n.style.setProperty('--delay',Math.min(i*28,310)+'ms');return n;
}
D.slides.forEach((s,j)=>{const section=el('section');section.className='slide';section.dataset.id=s.id;section.setAttribute('aria-label',s.title);s.elements.forEach((v,i)=>section.append(buildItem(v,i)));if(s.id==='demo'&&!D.demoReady){const info=el('div',{textContent:'Demo file missing. Use “Load demo” to choose second-shift-neuroai-90s-zoom-music.mp4.'});info.className='no-video';section.append(info)}stage.append(section)});
const sections=[...stage.children],video=document.querySelector('#demoVideo');
let current=0,hideTimer,started=performance.now(),slideStarted=started,objectURL;
function resize(){stage.style.transform=`scale(${Math.min(innerWidth/1920,innerHeight/1080)})`;document.querySelectorAll('.mini-stage').forEach(n=>n.style.transform=`scale(${n.parentElement.clientWidth/1920})`)}
function show(index){
 const next=Math.max(0,Math.min(5,index));if(current===3&&next!==3){video.pause();video.currentTime=0;video.hidden=true}
 current=next;slideStarted=performance.now();sections.forEach((s,i)=>{s.classList.toggle('active',i===current);s.setAttribute('aria-hidden',i!==current)});
 document.querySelector('#counter').textContent=`${current+1} / 6`;history.replaceState(null,'','#'+(current+1));updateNotes();document.title=`${current+1}. ${D.slides[current].title} · Second Shift`;
}
function toast(message){const t=document.querySelector('#toast');t.textContent=message;t.hidden=false;clearTimeout(t.timer);t.timer=setTimeout(()=>t.hidden=true,6500)}
async function play(){if(!video.src){toast('Choose second-shift-neuroai-90s-zoom-music.mp4 using “Load demo”.');controls();return}video.hidden=false;try{if(video.paused)await video.play();else video.pause()}catch(e){toast('Playback needs a click. Use the video’s play control.')}}
function controls(){document.body.classList.add('controls-visible');clearTimeout(hideTimer);hideTimer=setTimeout(()=>document.body.classList.remove('controls-visible'),2200)}
function fmt(n){return `${Math.floor(n/60)}:${String(Math.floor(n%60)).padStart(2,'0')}`}
function updateNotes(){const s=D.slides[current];document.querySelector('#notes-title').textContent=s.title;document.querySelector('#notes-copy').textContent=s.notes+(s.cue?'\n\n'+s.cue:'');document.querySelector('#notes-cue').textContent=`Pitch ${fmt(s.start)}–${fmt(s.start+s.duration)} · ${s.duration} seconds`;}
function notes(){const n=document.querySelector('#notes');n.hidden=!n.hidden;updateNotes()}
function overview(){const o=document.querySelector('#overview');if(o.childElementCount===0)sections.forEach((s,i)=>{const b=el('button',{title:D.slides[i].title});const m=el('div');m.className='mini-stage';const copy=s.cloneNode(true);copy.querySelectorAll('video').forEach(v=>v.remove());copy.querySelectorAll('[id]').forEach(v=>v.removeAttribute('id'));m.append(copy);b.append(m);b.onclick=()=>{o.hidden=true;show(i)};o.append(b)});o.hidden=!o.hidden;resize()}
document.querySelector('#prev').onclick=()=>show(current-1);document.querySelector('#next').onclick=()=>show(current+1);document.querySelector('#notes-toggle').onclick=notes;document.querySelector('#notes-close').onclick=notes;document.querySelector('#overview-toggle').onclick=overview;
async function fullscreen(){try{if(document.fullscreenElement)await document.exitFullscreen();else await document.documentElement.requestFullscreen()}catch{toast('Use your browser’s fullscreen command.')}}
document.querySelector('#fullscreen').onclick=fullscreen;
document.querySelector('#demo-file').onchange=e=>{const f=e.target.files[0];if(!f)return;video.pause();if(objectURL)URL.revokeObjectURL(objectURL);objectURL=URL.createObjectURL(f);video.src=objectURL;video.hidden=true;sections[3].querySelector('.no-video')?.setAttribute('hidden','');toast('Demo loaded locally. Go to slide 4 and press Enter.')};
document.querySelector('label[for="demo-file"]').onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();e.stopPropagation();document.querySelector('#demo-file').click()}};
document.addEventListener('keydown',e=>{
 if(e.target.tagName==='INPUT')return;
 if(['ArrowRight','PageDown'].includes(e.key)){e.preventDefault();show(current+1)}else if(['ArrowLeft','PageUp'].includes(e.key)){e.preventDefault();show(current-1)}else if(e.key==='Home'){e.preventDefault();show(0)}else if(e.key==='End'){e.preventDefault();show(5)}else if(e.key===' '||e.key==='Enter'){if(e.target.tagName==='BUTTON')return;e.preventDefault();current===3?play():show(current+1)}else if(e.key.toLowerCase()==='f')fullscreen();else if(e.key.toLowerCase()==='n')notes();else if(e.key.toLowerCase()==='o')overview();else if(/^[1-6]$/.test(e.key))show(+e.key-1);else if(e.key==='Escape'){document.querySelector('#notes').hidden=true;document.querySelector('#overview').hidden=true}else if(e.key.toLowerCase()==='r'){started=performance.now();slideStarted=started;toast('Rehearsal timer reset')}
});
document.addEventListener('pointermove',e=>{if(e.clientY>innerHeight-100)controls();if(!matchMedia('(prefers-reduced-motion: reduce)').matches&&!review){stage.style.setProperty('--parallax-x',((e.clientX/innerWidth-.5)*10)+'px');stage.style.setProperty('--parallax-y',((e.clientY/innerHeight-.5)*8)+'px')}});
sections[3].addEventListener('click',e=>{if(!e.target.closest('video'))play()});
setInterval(()=>{document.querySelector('#elapsed').textContent='Total '+fmt((performance.now()-started)/1000);document.querySelector('#slide-elapsed').textContent='Slide '+fmt((performance.now()-slideStarted)/1000)},250);
window.addEventListener('resize',resize);window.addEventListener('hashchange',()=>show((parseInt(location.hash.slice(1))||1)-1));resize();show((parseInt(location.hash.slice(1))||1)-1);controls();
window.secondShift={show,get current(){return current},slides:D.slides};
