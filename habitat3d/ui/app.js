import {HabitatView} from './scene.js';
const $=id=>document.getElementById(id);
let state=null,selected='F01',filter='all',view=null,failures=0,lastEvent=-1,lastPopulation='',inFlight=false,topology=null;
let toastTimer,pollSequence=0,renderSequence=0;
function toast(text,error=false){$('toast').textContent=text;$('toast').classList.toggle('error',error);$('toast').classList.add('visible');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').classList.remove('visible'),4500)}
async function command(action,extra={}){
  if(state?.provenance.mode==='full')toast('正在处理；控制操作会等待当前全图步完成。');
  try{const res=await fetch('/api/control',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action,...extra})});const data=await res.json();if(!res.ok)throw new Error(data.error||`HTTP ${res.status}`);await poll(true);return data}
  catch(e){toast(e.message,true);throw e}
}
function safe(fn){return e=>{Promise.resolve().then(()=>fn(e)).catch(()=>{})}}
function select(id){selected=id;if(view){view.select(id)}poll(true)}
function clock(t){const total=Math.floor((t%360)/360*1440),h=Math.floor(total/60),m=total%60;return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}`}
function shortTime(t){return `D${String(Math.floor(t/360)+1).padStart(2,'0')} ${clock(t)}`}
function node(tag,cls,text){const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n}
function initResources(resources){$('resource-list').replaceChildren();for(const r of resources){const row=node('div',`resource-item ${r.kind}`),icon=node('span','resource-icon',r.kind==='food'?'◉':r.kind==='water'?'◌':'⌁');const info=node('div','resource-info'),head=node('div');head.append(node('span','',r.label),node('span','',r.kind==='shade'?'庇护':'—'));head.lastChild.id=`resource-value-${r.id}`;const track=node('div','resource-track'),fill=node('i');fill.id=`resource-fill-${r.id}`;track.append(fill);info.append(head,track);row.append(icon,info);$('resource-list').append(row)}}
function renderPopulation(flies){
  const signature=flies.map(f=>f.id).join(',');
  if(lastPopulation!==signature){lastPopulation=signature;$('population-list').replaceChildren();for(const f of flies){const button=node('button','fly-row');button.dataset.id=f.id;button.setAttribute('aria-label',`观察 ${f.id}`);const icon=node('span','fly-avatar');icon.style.color=f.color;const info=node('div');info.append(node('strong','',f.id));const bars=node('div','row-activity');for(let i=0;i<6;i++)bars.append(node('i'));info.append(bars);button.append(icon,info,node('span','row-state'));button.addEventListener('click',()=>select(f.id));$('population-list').append(button)}}
  for(const f of flies){const row=$('population-list').querySelector(`[data-id="${f.id}"]`);row.classList.toggle('active',f.id===selected);row.classList.toggle('dead',!f.alive);row.querySelector('.row-state').textContent=f.state;[...row.querySelectorAll('.row-activity i')].forEach((e,i)=>e.style.background=i<Math.ceil(f.energy*6)?f.color:'#2d3b32')}
}
function renderVitals(f){const data=[['能量',f.energy,'#daba83'],['水分',f.hydration,'#8bb9ca'],['精力',1-f.fatigue,'#8dbfb0']];$('vitals').replaceChildren();for(const [name,value,color]of data){const r=node('div','vital'),track=node('span','track'),i=node('i');i.style.width=`${Math.max(0,Math.min(100,value*100))}%`;i.style.background=color;track.append(i);r.append(node('span','',name),track,node('b','',`${Math.round(value*100)}%`));$('vitals').append(r)}}
function drawBrain(s){
  const canvas=$('neural-canvas'),ctx=canvas.getContext('2d'),w=canvas.width,h=canvas.height;ctx.clearRect(0,0,w,h);
  const points=s.brain.activity.map((a,i)=>({x:22+(i%20)*26,y:22+Math.floor(i/20)*37,a}));
  if(topology){ctx.lineWidth=.7;for(let j=0;j<topology.pre.length;j+=7){const a=points[topology.pre[j]],b=points[topology.post[j]];const activity=(Math.abs(a.a)+Math.abs(b.a))/2;ctx.strokeStyle=`rgba(142,170,116,${.045+activity*.15})`;ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke()}}
  for(const p of points){ctx.beginPath();ctx.fillStyle=p.a>=0?`rgba(211,190,120,${.18+Math.abs(p.a)*.8})`:`rgba(115,183,179,${.18+Math.abs(p.a)*.8})`;ctx.arc(p.x,p.y,2+Math.abs(p.a)*2.8,0,Math.PI*2);ctx.fill()}
}
function drawHistory(history){const canvas=$('history-chart'),rect=canvas.getBoundingClientRect(),ratio=window.devicePixelRatio||1;canvas.width=Math.max(10,rect.width*ratio);canvas.height=rect.height*ratio;const ctx=canvas.getContext('2d'),w=canvas.width,h=canvas.height;ctx.strokeStyle='#324a37';ctx.lineWidth=ratio*.4;for(const y of [.25,.5,.75]){ctx.beginPath();ctx.moveTo(0,h*y);ctx.lineTo(w,h*y);ctx.stroke()}if(history.length<2)return;const t0=history[0].t,t1=history.at(-1).t;for(const [key,color]of [['energy','#daba83'],['hydration','#8bb9ca']]){ctx.beginPath();ctx.strokeStyle=color;ctx.lineWidth=ratio*1.1;history.forEach((p,i)=>{const x=(p.t-t0)/Math.max(1,t1-t0)*w,y=h*(1-p[key])*.85+h*.075;i?ctx.lineTo(x,y):ctx.moveTo(x,y)});ctx.stroke()}}
function drawDay(phase){const c=$('day-arc'),ctx=c.getContext('2d');ctx.clearRect(0,0,70,44);ctx.beginPath();ctx.strokeStyle='#485d43';ctx.lineWidth=1;ctx.arc(35,39,28,Math.PI,2*Math.PI);ctx.stroke();const a=Math.PI+phase*Math.PI;ctx.beginPath();ctx.fillStyle='#daba83';ctx.arc(35+28*Math.cos(a),39+28*Math.sin(a),3,0,7);ctx.fill()}
function renderEvents(events,force=false){
  if(lastEvent===state.tick&& !force)return;lastEvent=state.tick;
  const list=events.filter(e=>filter==='all'||['signal','follow','verified','miss','human'].includes(e.kind)).slice(-25).reverse();
  const fragment=document.createDocumentFragment();for(const e of list){const row=node('div',`event ${e.kind}`);const icon=node('span','event-icon',({signal:'↗',follow:'↝',verified:'✓',miss:'·',weather:'☂',death:'−',human:'↑'})[e.kind]||'○');const copy=node('div');copy.append(node('h3','',e.title),node('p','',e.detail),node('time','',shortTime(e.t)));row.append(icon,copy);fragment.append(row)}if(!list.length)fragment.append(node('p','muted','尚无交流记录。观察附近个体的发现。'));$('event-list').replaceChildren(fragment);
}
function render(s){
  state=s;if(!s.flies.some(f=>f.id===selected))selected=s.flies[0].id;
  if(!$('resource-list').children.length)initResources(s.resources);
  renderPopulation(s.flies);const f=s.flies.find(f=>f.id===selected)||s.flies[0];
  $('selected-id').textContent=f.id;$('selected-state').textContent=f.state;$('selected-color').style.background=f.color;renderVitals(f);
  $('alive-count').textContent=s.flies.filter(f=>f.alive).length;$('total-count').textContent=s.flies.length;
  $('weather-label').textContent=s.weather.label;$('weather-icon').textContent=s.weather.rain>.2?'☂':s.weather.light<.2?'☾':'☀';
  $('weather-detail').textContent=`光照 ${Math.round(s.weather.light*100)}% · 降雨 ${Math.round(s.weather.rain*100)}%`;
  $('world-time').replaceChildren(document.createTextNode(`第 ${String(s.day).padStart(2,'0')} 日 `),node('span','',clock(s.t)));
  $('seed-label').textContent=`SEED ${s.seed}`;
  for(const r of s.resources){$(`resource-fill-${r.id}`).style.width=`${r.amount*100}%`;$(`resource-value-${r.id}`).textContent=r.kind==='shade'?'稳定':`${Math.round(r.amount*100)}%`}
  $('pause-button').textContent=s.runtime.paused?'▶':'Ⅱ';$('pause-button').setAttribute('aria-label',s.runtime.paused?'继续':'暂停');$('step-button').disabled=!s.runtime.paused;
  $('run-state').textContent=s.runtime.paused?'世界已暂停':`${s.runtime.speed}× 时间流速`;
  document.querySelectorAll('[data-speed]').forEach(b=>b.classList.toggle('active',+b.dataset.speed===s.runtime.speed));
  $('communication-toggle').checked=s.communication;$('plasticity-toggle').checked=s.plasticity;
  const full=s.provenance.mode==='full';$('plasticity-toggle').disabled=full;
  if(full&&!s.runtime.paused)$('run-state').textContent=`目标 ${s.runtime.speed}× · 实际约 ${(.25/Math.max(.25,s.runtime.step_ms/1000)).toFixed(3)}×`;
  $('plasticity-toggle').parentElement.title=full?'全量模式固定公开结构权重；经验和信任仍更新':'';
  $('graph-size').textContent=full?'全图 · 1.52 亿边':'97 节点 / 1,606 边';
  $('graph-size').title=`实际计算 ${s.provenance.nodes.toLocaleString()} 分割单元、${s.provenance.edges.toLocaleString()} 条连接；图中仅显示 97 个探针节点`;
  $('about-graph').textContent=full?'完整公开连接表：88,384,522 个分割单元，151,856,684 条边；包含大量碎片，非同等数量完整神经元。图中只显示 97 个探针。':'当前为旧版 MBON 子图：97 节点、1,606 条边。';
  $('message-input').disabled=!s.communication;$('message-form').querySelector('button').disabled=!s.communication;
  $('neural-rms').textContent=full?s.brain.rms.toExponential(2):s.brain.rms.toFixed(3);$('gain-change').textContent=full?'固定权重':s.brain.gain_change.toFixed(5);
  $('known-count').textContent=f.known;$('helped-count').textContent=f.helped;$('age').textContent=`${f.age.toFixed(1)} 日`;
  $('sent-count').textContent=s.metrics.sent;$('followed-count').textContent=s.metrics.followed;$('verified-count').textContent=s.metrics.verified;
  $('save-status').textContent=s.runtime.saved_at?'已存档 '+s.runtime.saved_at.slice(11,19):full?'全图每 120 秒自动保存':'自动保存每 20 秒';$('step-ms').textContent=`${s.runtime.step_ms.toFixed(1)} ms / tick`;
  drawDay(s.day_phase);drawHistory(s.history);drawBrain(s);renderEvents(s.events);
  if(view){if(view.state?.tick!==s.tick)view.stateReceived=performance.now();view.selected=selected;view.setState(s)}
  $('loading').classList.add('hidden');$('connection').textContent=s.runtime.error?'仿真已停止：内部错误':s.runtime.paused?'已连接 · 暂停':'本机世界 · 运行中';$('live-dot').style.background=s.runtime.error?'#ca7866':s.runtime.paused?'#daba83':'#91caa6';
  if(s.runtime.error)toast('仿真发生错误，已暂停。请检查 server.err.log。',true);
  window.__habitatState=s;
}
async function poll(force=false){
  if(inFlight&&!force)return;inFlight=true;const sequence=++pollSequence,requested=selected;
  try{const res=await fetch(`/api/state?selected=${encodeURIComponent(requested)}`,{signal:AbortSignal.timeout(5000)});if(!res.ok)throw new Error(`HTTP ${res.status}`);const s=await res.json();if(sequence<renderSequence||requested!==selected)return;renderSequence=sequence;failures=0;render(s)}
  catch(e){failures++;$('connection').textContent='连接中断 · 正在重试';$('live-dot').style.background='#bb7866';if(failures===2)toast('无法连接本机服务，画面保留最后状态，正在重试。',true)}finally{inFlight=false}
}
async function boot(){
  try{view=new HabitatView($('viewport'),$('labels'),select,fps=>$('fps').textContent=`${fps} FPS`);window.__habitatView=view}
  catch(e){$('loading').querySelector('strong').textContent='3D 渲染器未能启动';$('loading').querySelector('span').textContent='需要启用浏览器 WebGL 2 / 硬件加速。'+e.message;throw e}
  topology=await fetch('/api/topology').then(r=>{if(!r.ok)throw new Error('拓扑读取失败');return r.json()});
  await poll();setInterval(()=>poll(),500);
}
$('pause-button').onclick=safe(()=>command('pause',{value:!state.runtime.paused}));$('step-button').onclick=safe(()=>command('step'));
document.querySelectorAll('[data-speed]').forEach(b=>b.onclick=safe(()=>command('speed',{value:+b.dataset.speed})));
$('overview-button').onclick=()=>{view.overview();$('follow-button').classList.remove('active')};$('top-button').onclick=()=>{view.top();$('follow-button').classList.remove('active')};
function follow(){view.follow(selected);$('follow-button').classList.add('active')}$('follow-button').onclick=()=>{if(view.following){view.overview();$('follow-button').classList.remove('active')}else follow()};$('focus-button').onclick=follow;
$('trails-toggle').onchange=e=>view.trails=e.target.checked;$('sense-toggle').onchange=e=>view.sense=e.target.checked;
$('communication-toggle').onchange=safe(e=>command('communication',{value:e.target.checked}));$('plasticity-toggle').onchange=safe(e=>command('plasticity',{value:e.target.checked}));
for(const [id,action,text]of [['rain-button','rain','已引入阵雨，观察个体如何寻找庇护。'],['dry-button','dry','露水已暂时蒸干，旧线索可能失效。'],['fruit-button','fruit','果实已补充，个体仍需自行发现。']])$(id).onclick=safe(async()=>{await command(action);toast(text)});
$('save-button').onclick=safe(async()=>{await command('save');toast('当前世界、个体记忆与神经状态已保存。')});
$('export-button').onclick=safe(async()=>{const res=await fetch('/api/export');if(!res.ok)throw new Error('导出失败');const b=await res.blob(),url=URL.createObjectURL(b),a=node('a');a.href=url;a.download=`micro-habitat-${state.seed}-day${state.day}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);toast('完整观察存档已导出。')});
$('message-form').onsubmit=safe(async e=>{e.preventDefault();const text=$('message-input').value.trim();if(!text)return;await command('message',{text,recipient:'all'});$('message-input').value='';toast('词符已发送，后续行为由个体状态和局部信息决定。')});
$('message-form').addEventListener('submit',e=>e.preventDefault());
for(const [id,value]of [['tab-all','all'],['tab-signal','signal']])$(id).onclick=()=>{filter=value;for(const tid of ['tab-all','tab-signal']){$(tid).classList.toggle('active',tid===id);$(tid).setAttribute('aria-selected',tid===id?'true':'false')}renderEvents(state.events,true)};
$('about-button').onclick=()=>$('about-dialog').showModal();document.querySelectorAll('#about-dialog .dialog-close').forEach(b=>b.onclick=()=>$('about-dialog').close());
$('new-world-button').onclick=()=>{$('reset-seed').value=state.seed;$('reset-count').value=state.flies.length;$('reset-dialog').showModal()};document.querySelector('#reset-dialog .reset-close').onclick=()=>$('reset-dialog').close();
$('confirm-reset').onclick=safe(async()=>{await command('reset',{seed:+$('reset-seed').value,count:+$('reset-count').value});$('reset-dialog').close();view.overview();toast('旧世界已归档，新世界开始运行。')});
document.addEventListener('keydown',safe(async e=>{if(e.code==='Space'&&!['INPUT','TEXTAREA','BUTTON'].includes(e.target.tagName)&&!document.querySelector('dialog[open]')){e.preventDefault();if(state)await command('pause',{value:!state.runtime.paused})}}));
boot().catch(e=>{console.error(e);toast('启动失败：'+e.message,true)});
