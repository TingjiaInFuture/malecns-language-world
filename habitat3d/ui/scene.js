import * as THREE from 'three';
import {OrbitControls} from './vendor/OrbitControls.js';

const groundY=(x,z)=>.16*Math.sin(x*.18)*Math.cos(z*.21);
const hash=(n)=>{const v=Math.sin(n*127.1+311.7)*43758.5453;return v-Math.floor(v)};
const colors={food:0xdaba83,water:0x8bb9ca,shade:0x8dbfb0};
const sphere=new THREE.SphereGeometry(1,16,12);
const leafShape=new THREE.Shape();leafShape.moveTo(0,-1);leafShape.bezierCurveTo(-.9,-.4,-.65,.65,0,1);leafShape.bezierCurveTo(.65,.65,.9,-.4,0,-1);
const leafGeo=new THREE.ShapeGeometry(leafShape,14);

function mesh(geo,material,parent,pos=[0,0,0],scale=[1,1,1]){
  const m=new THREE.Mesh(geo,material);m.position.set(...pos);m.scale.set(...scale);m.castShadow=true;m.receiveShadow=true;parent.add(m);return m;
}
function tubeBetween(a,b,r,material,parent){
  const start=new THREE.Vector3(...a),end=new THREE.Vector3(...b),v=end.clone().sub(start);
  const m=mesh(new THREE.CylinderGeometry(r,r*.85,v.length(),5),material,parent);
  m.position.copy(start.add(end).multiplyScalar(.5));m.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),v.normalize());return m;
}
function line(points,material,parent){const g=new THREE.BufferGeometry().setFromPoints(points.map(p=>new THREE.Vector3(...p)));const l=new THREE.Line(g,material);parent.add(l);return l}

export class HabitatView{
  constructor(container,labels,onSelect,onFPS){
    this.container=container;this.labels=labels;this.onSelect=onSelect;this.onFPS=onFPS;
    this.scene=new THREE.Scene();this.scene.background=new THREE.Color(0x111a1c);this.scene.fog=new THREE.FogExp2(0x111a1c,.007);
    this.renderer=new THREE.WebGLRenderer({antialias:true,powerPreference:'high-performance'});
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio,1.5));this.renderer.shadowMap.enabled=true;
    this.renderer.shadowMap.type=THREE.PCFSoftShadowMap;this.renderer.outputColorSpace=THREE.SRGBColorSpace;
    this.renderer.toneMapping=THREE.ACESFilmicToneMapping;this.renderer.toneMappingExposure=1.32;
    container.appendChild(this.renderer.domElement);
    this.camera=new THREE.PerspectiveCamera(42,1,.1,260);this.camera.position.set(44,42,49);
    this.controls=new OrbitControls(this.camera,this.renderer.domElement);this.controls.enableDamping=true;this.controls.dampingFactor=.08;
    this.controls.target.set(0,0,0);this.controls.minDistance=4;this.controls.maxDistance=110;this.controls.maxPolarAngle=Math.PI*.475;
    this.scene.add(new THREE.HemisphereLight(0xcde4d2,0x25332c,1.75));
    this.sun=new THREE.DirectionalLight(0xffdfaa,3.8);this.sun.position.set(-18,32,12);this.sun.castShadow=true;
    Object.assign(this.sun.shadow.camera,{left:-36,right:36,top:30,bottom:-30,near:1,far:100});
    this.sun.shadow.mapSize.set(1536,1536);this.sun.shadow.normalBias=.04;this.sun.shadow.bias=-.0005;this.scene.add(this.sun);
    const fill=new THREE.DirectionalLight(0x89bda9,1.1);fill.position.set(20,12,-25);this.scene.add(fill);
    this.flies=new Map();this.resources=new Map();this.selected='F01';this.following=false;this.trails=true;this.sense=false;
    this.state=null;this.staticBuilt=false;this.frameCount=0;this.lastFPS=performance.now();this.lastFrame=this.lastFPS;
    this.resourceLabels=[];this.raycaster=new THREE.Raycaster();this.pointer=new THREE.Vector2();
    this.signalGroup=new THREE.Group();this.scene.add(this.signalGroup);
    this.signalMaterial=new THREE.LineBasicMaterial({color:0xc8d793,transparent:true,opacity:.28,depthTest:false});
    this.buildGround();this.buildRain();
    const resize=()=>{const w=container.clientWidth,h=container.clientHeight;if(!w||!h)return;this.camera.aspect=w/h;this.camera.updateProjectionMatrix();this.renderer.setSize(w,h,false)};
    this.observer=new ResizeObserver(resize);this.observer.observe(container);resize();
    let down=null;
    container.addEventListener('pointerdown',e=>{down=[e.clientX,e.clientY]});
    container.addEventListener('pointerup',e=>{if(!down||Math.hypot(e.clientX-down[0],e.clientY-down[1])>5)return;const r=container.getBoundingClientRect();this.pointer.set((e.clientX-r.left)/r.width*2-1,-(e.clientY-r.top)/r.height*2+1);this.raycaster.setFromCamera(this.pointer,this.camera);
      const hit=this.raycaster.intersectObjects([...this.flies.values()].map(f=>f.group),true)[0];if(hit){let o=hit.object;while(o&&!o.userData.flyId)o=o.parent;if(o)this.onSelect(o.userData.flyId)}});
    this.animate=this.animate.bind(this);requestAnimationFrame(this.animate);
  }
  buildGround(){
    const earth=new THREE.MeshStandardMaterial({color:0x594b37,roughness:1});
    mesh(new THREE.CylinderGeometry(29.9,29.7,1.65,96),earth,this.scene,[0,-1.08,0],[1,1,.64]);
    const lower=new THREE.MeshStandardMaterial({color:0x28342b,roughness:1});
    mesh(new THREE.CylinderGeometry(29.7,28.9,.7,96),lower,this.scene,[0,-2.23,0],[1,1,.64]);
    const positions=[],c=[],indices=[];const rings=26,segments=96;
    for(let j=0;j<=rings;j++)for(let i=0;i<=segments;i++){
      const r=j/rings,angle=i/segments*Math.PI*2,x=29.8*r*Math.cos(angle),z=19.05*r*Math.sin(angle);
      positions.push(x,groundY(x,z)-.18,z);
      const noise=hash(i+j*107)*.18;const patch=.5+.5*Math.sin(x*.22)*Math.cos(z*.21);
      const color=new THREE.Color().setRGB(.19+patch*.09+noise*.6,.25+patch*.07+noise*.35,.125+patch*.03+noise*.12);
      c.push(color.r,color.g,color.b);
      if(j<rings&&i<segments){const a=j*(segments+1)+i,b=a+segments+1;indices.push(a,b,a+1,b,b+1,a+1)}
    }
    const geo=new THREE.BufferGeometry();geo.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));geo.setAttribute('color',new THREE.Float32BufferAttribute(c,3));geo.setIndex(indices);geo.computeVertexNormals();
    const terrain=mesh(geo,new THREE.MeshStandardMaterial({vertexColors:true,roughness:1,side:THREE.DoubleSide}),this.scene);terrain.castShadow=false;
    const stalkGeo=new THREE.ConeGeometry(.07,.75,3);stalkGeo.translate(0,.36,0);
    const grass=new THREE.InstancedMesh(stalkGeo,new THREE.MeshStandardMaterial({color:0x7c8c42,roughness:1,side:THREE.DoubleSide}),950);
    const dummy=new THREE.Object3D();const shade=new THREE.Color();
    for(let i=0;i<950;i++){
      const theta=hash(i+23)*Math.PI*2,r=Math.sqrt(hash(i+121))*28.9,x=Math.cos(theta)*r,z=Math.sin(theta)*r*.635;
      dummy.position.set(x,groundY(x,z)-.12,z);dummy.rotation.set(hash(i+3)*.35,hash(i+9)*6.28,hash(i+71)*.3);dummy.scale.set(1,.4+hash(i+27)*1.25,1);dummy.updateMatrix();grass.setMatrixAt(i,dummy.matrix);
      shade.setHSL(.17+hash(i+7)*.07,.26+hash(i+5)*.15,.18+hash(i+1)*.15);grass.setColorAt(i,shade);
    }
    grass.receiveShadow=true;this.scene.add(grass);
    const pebbleMat=new THREE.MeshStandardMaterial({color:0x74765d,roughness:1});const pebbles=new THREE.InstancedMesh(new THREE.IcosahedronGeometry(1,0),pebbleMat,120);
    for(let i=0;i<120;i++){const a=hash(i+11)*6.28,r=hash(i+712)*28,x=Math.sin(a)*r,z=Math.cos(a)*r*.6;dummy.position.set(x,groundY(x,z),z);dummy.scale.set(.1+hash(i+73)*.35,.08+hash(i+63)*.13,.1+hash(i+93)*.3);dummy.rotation.set(i,i*.5,i*.2);dummy.updateMatrix();pebbles.setMatrixAt(i,dummy.matrix)}
    pebbles.receiveShadow=true;this.scene.add(pebbles);
    const twigMat=new THREE.MeshStandardMaterial({color:0x705535,roughness:1});
    tubeBetween([-8,0,14],[3,.35,15],.28,twigMat,this.scene);tubeBetween([-4,.15,14.5],[-2,.3,12.2],.13,twigMat,this.scene);
    const green=new THREE.MeshStandardMaterial({color:0x49703c,roughness:.8,side:THREE.DoubleSide});
    for(let j=0;j<22;j++){
      const angle=j/22*Math.PI*2,r=26+hash(j)*2,x=Math.cos(angle)*r,z=Math.sin(angle)*r*.63;
      const stemHeight=1.8+hash(j+55)*2;
      tubeBetween([x,0,z],[x+.3,stemHeight,z+.2],.045,green,this.scene);
      for(let k=0;k<3;k++){const l=mesh(leafGeo,green,this.scene,[x+(k-1)*.7,stemHeight*.45+k*.5,z],[.65,1.3,1]);l.rotation.set(-.5,.5+j,k%2?.8:-.8)}
    }
    const guideMat=new THREE.LineBasicMaterial({color:0x506356,transparent:true,opacity:.35});
    const ring=[];for(let i=0;i<=128;i++){const a=i/128*6.28;ring.push([Math.cos(a)*31.3,-2.6,Math.sin(a)*20])}line(ring,guideMat,this.scene);
  }
  buildRain(){
    const p=new Float32Array(260*6);this.rainBase=[];
    for(let i=0;i<260;i++)this.rainBase.push([(hash(i+9)-.5)*58,hash(i+23)*18,(hash(i+32)-.5)*36]);
    const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(p,3));
    this.rain=new THREE.LineSegments(g,new THREE.LineBasicMaterial({color:0xbcd2ce,transparent:true,opacity:.23}));this.rain.visible=false;this.scene.add(this.rain);
  }
  buildResource(r){
    const group=new THREE.Group();group.position.set(r.x,groundY(r.x,r.z),r.z);this.scene.add(group);
    const indicator=mesh(new THREE.RingGeometry(r.radius+.1,r.radius+.15,48),new THREE.MeshBasicMaterial({color:colors[r.kind],transparent:true,opacity:.3,side:THREE.DoubleSide,depthWrite:false}),group,[0,-.05,0]);indicator.rotation.x=-Math.PI/2;indicator.castShadow=false;
    let surface=null;
    if(r.kind==='food'){
      const rind=new THREE.MeshStandardMaterial({color:r.id==='R1'?0x9a7148:0xb66c38,roughness:.9});
      const flesh=new THREE.MeshStandardMaterial({color:0xd8a561,roughness:.9});
      mesh(sphere,rind,group,[0,.94,0],[r.radius*.72,1.3,r.radius*.62]);
      surface=mesh(new THREE.SphereGeometry(1,24,16,0,Math.PI*2,0,Math.PI*.5),flesh,group,[.3,1.22,.7],[r.radius*.52,.28,r.radius*.48]);surface.rotation.x=.7;
      const seedMat=new THREE.MeshStandardMaterial({color:0x824c29,roughness:1});
      for(let i=0;i<15;i++){const a=hash(i+5)*6.28,rr=hash(i+12)*r.radius*.4;mesh(sphere,seedMat,group,[.3+Math.cos(a)*rr,1.48+hash(i)*.1,.7+Math.sin(a)*rr*.65],[.055,.03,.07])}
      tubeBetween([0,1.8,-.2],[.3,2.7,-.35],.12,new THREE.MeshStandardMaterial({color:0x665135}),group);
      const leaf=mesh(leafGeo,new THREE.MeshStandardMaterial({color:0x6d7c3d,side:THREE.DoubleSide}),group,[.5,2.4,-.3],[.7,1.2,1]);leaf.rotation.set(-.8,0,-.8);
    }else if(r.kind==='water'){
      mesh(sphere,new THREE.MeshStandardMaterial({color:0x707566,roughness:1}),group,[0,-.02,0],[r.radius*1.18,.25,r.radius]);
      surface=mesh(new THREE.CircleGeometry(r.radius,48),new THREE.MeshPhysicalMaterial({color:0x80b7b0,metalness:.22,roughness:.12,transparent:true,opacity:.8,side:THREE.DoubleSide}),group,[0,.18,0]);surface.rotation.x=-Math.PI/2;
      const ripple=mesh(new THREE.RingGeometry(r.radius*.6,r.radius*.61,48),new THREE.MeshBasicMaterial({color:0xd4ece3,transparent:true,opacity:.2,side:THREE.DoubleSide}),group,[0,.2,0]);ripple.rotation.x=-Math.PI/2;
      for(let i=0;i<4;i++){const a=i*1.7;mesh(sphere,new THREE.MeshPhysicalMaterial({color:0xb4d5c5,roughness:.05,transparent:true,opacity:.7}),group,[Math.cos(a)*r.radius*.9,.24,Math.sin(a)*r.radius*.8],[.15,.1,.15])}
      if(r.protected){const leaf=mesh(leafGeo,new THREE.MeshStandardMaterial({color:0x547537,side:THREE.DoubleSide}),group,[-1,1.1,-1],[1.2,2.4,1]);leaf.rotation.set(-1.05,.6,-.4)}
    }else{
      const green=new THREE.MeshStandardMaterial({color:r.id==='R3'?0x759443:0x577b3b,roughness:.85,side:THREE.DoubleSide});
      const g=leafGeo.clone();const pos=g.attributes.position;
      for(let i=0;i<pos.count;i++){const x=pos.getX(i),y=pos.getY(i);pos.setXYZ(i,x*r.radius*.95,1.6+(1-y*y)*1.3+Math.sin(x*3)*.45,y*r.radius)}g.computeVertexNormals();
      surface=mesh(g,green,group);const veinMat=new THREE.LineBasicMaterial({color:0xa6b36d,transparent:true,opacity:.7});
      const mid=[];for(let j=0;j<=24;j++){const z=-r.radius+2*r.radius*j/24;mid.push([0,1.63+(1-(z/r.radius)**2)*1.3,z])}line(mid,veinMat,group);
      for(let i=0;i<6;i++){const z=(i/6-.5)*r.radius*1.5;for(const sign of [-1,1])line([[0,1.68+(1-(z/r.radius)**2)*1.3,z],[sign*r.radius*.58,2.45,z+.65]],veinMat,group)}
      tubeBetween([0,.1,r.radius+1],[0,1.6,r.radius],.11,new THREE.MeshStandardMaterial({color:0x747244}),group);
    }
    this.resources.set(r.id,{group,surface,kind:r.kind});
  }
  buildFly(f){
    const group=new THREE.Group();group.userData.flyId=f.id;this.scene.add(group);
    const body=new THREE.MeshStandardMaterial({color:0xa7834b,roughness:.62});
    const dark=new THREE.MeshStandardMaterial({color:0x39382b,roughness:.72});
    const eyes=new THREE.MeshStandardMaterial({color:0x9f3523,roughness:.4});
    mesh(sphere,body,group,[0,0,0],[.24,.23,.28]);mesh(sphere,body,group,[0,-.025,-.4],[.25,.22,.42]);
    mesh(sphere,dark,group,[0,.025,.38],[.23,.21,.2]);
    mesh(sphere,eyes,group,[-.18,.06,.43],[.13,.16,.13]);mesh(sphere,eyes,group,[.18,.06,.43],[.13,.16,.13]);
    for(let i=0;i<4;i++){const ring=mesh(new THREE.TorusGeometry(.235-i*.035,.025,5,14),dark,group,[0,-.02,-.26-i*.14]);ring.scale.y=.87}
    const wingMat=new THREE.MeshPhysicalMaterial({color:0xd5e3d8,transparent:true,opacity:.53,roughness:.22,side:THREE.DoubleSide,depthWrite:false});
    const wings=[];
    for(const sign of [-1,1]){
      const pivot=new THREE.Group();pivot.position.set(sign*.15,.16,-.03);group.add(pivot);
      const w=mesh(sphere,wingMat,pivot,[sign*.26,.015,-.22],[.28,.018,.62]);w.rotation.y=sign*.38;w.castShadow=false;
      const vein=line([[0,.02,0],[sign*.32,.03,-.6]],new THREE.LineBasicMaterial({color:0x819d90,transparent:true,opacity:.45}),pivot);vein.renderOrder=1;
      wings.push({pivot,sign});
      tubeBetween([sign*.12,.02,.5],[sign*.15,.09,.7],.014,dark,group);
      mesh(sphere,body,group,[sign*.29,-.025,-.23],[.043,.043,.043]);
    }
    const legs=[];
    for(let j=0;j<3;j++)for(const sign of [-1,1]){
      const pivot=new THREE.Group();pivot.position.set(sign*.16,-.12,.18-j*.22);group.add(pivot);
      tubeBetween([0,0,0],[sign*.24,-.13,.1-j*.1],.019,dark,pivot);
      tubeBetween([sign*.24,-.13,.1-j*.1],[sign*.44,-.28,.19-j*.18],.012,dark,pivot);
      legs.push({pivot,sign,phase:j*Math.PI*.7+(sign<0?Math.PI:0)});
    }
    const marker=mesh(new THREE.RingGeometry(.88,.92,48),new THREE.MeshBasicMaterial({color:f.color,transparent:true,opacity:.7,side:THREE.DoubleSide,depthWrite:false}),this.scene);
    marker.rotation.x=-Math.PI/2;marker.castShadow=false;
    const sense=mesh(new THREE.RingGeometry(7.96,8,64),new THREE.MeshBasicMaterial({color:f.color,transparent:true,opacity:.23,side:THREE.DoubleSide,depthWrite:false}),this.scene);sense.rotation.x=-Math.PI/2;sense.castShadow=false;sense.visible=false;
    const trail=line([],new THREE.LineBasicMaterial({color:f.color,transparent:true,opacity:.35}),this.scene);
    const label=document.createElement('div');label.className='fly-label';label.textContent=f.id;this.labels.append(label);
    const entry={group,wings,legs,marker,sense,trail,label,target:new THREE.Vector3(f.x,f.y,f.z),heading:f.heading,state:f};
    group.position.copy(entry.target);this.flies.set(f.id,entry);return entry;
  }
  setState(s){
    this.state=s;
    if(!this.staticBuilt){
      s.resources.forEach(r=>this.buildResource(r));
      s.rocks.forEach((r,i)=>{const rock=mesh(new THREE.DodecahedronGeometry(1,1),new THREE.MeshStandardMaterial({color:i%2?0x6b7160:0x858674,roughness:1,flatShading:true}),this.scene,[r.x,r.height*.36,r.z],[r.r,r.height*.72,r.r*.77]);rock.rotation.y=i*1.3});
      this.staticBuilt=true;
    }
    const ids=new Set(s.flies.map(f=>f.id));
    for(const [id,e] of this.flies)if(!ids.has(id)){this.scene.remove(e.group,e.marker,e.sense,e.trail);e.label.remove();this.flies.delete(id)}
    for(const f of s.flies){const e=this.flies.get(f.id)||this.buildFly(f);e.target.set(f.x,f.y,f.z);e.heading=f.heading;e.state=f;
      e.trail.geometry.dispose();e.trail.geometry=new THREE.BufferGeometry().setFromPoints(f.trail.map(p=>new THREE.Vector3(...p)));e.trail.visible=this.trails;
    }
    for(const r of s.resources){const e=this.resources.get(r.id);if(r.kind==='water'){e.surface.visible=r.amount>.025;e.surface.scale.setScalar(Math.max(.12,Math.sqrt(r.amount)));e.surface.material.opacity=.4+r.amount*.4}else if(r.kind==='food'){e.surface.material.color.setHSL(.085,.42,.27+.3*r.amount)}}
    for(const child of [...this.signalGroup.children]){child.geometry.dispose();this.signalGroup.remove(child)}
    if(s.communication)for(const m of s.messages){if(m.sender!==this.selected&&!m.recipients.includes(this.selected))continue;
      for(const id of m.recipients){const f=s.flies.find(f=>f.id===id);if(f&&(m.sender===this.selected||id===this.selected))line([m.origin,[f.x,f.y+.2,f.z]],this.signalMaterial,this.signalGroup)}
    }
  }
  select(id){this.selected=id;this.setState(this.state);if(this.following)this.follow(id)}
  follow(id=this.selected){this.following=true;this.selected=id;const e=this.flies.get(id);if(e){this.camera.position.copy(e.target).add(new THREE.Vector3(6,5,8));this.controls.target.copy(e.target)}}
  overview(){this.following=false;this.camera.position.set(44,42,49);this.controls.target.set(0,0,0)}
  top(){this.following=false;this.camera.position.set(0,70,.05);this.controls.target.set(0,0,0)}
  animate(now){
    requestAnimationFrame(this.animate);const dt=Math.min(.1,(now-this.lastFrame)/1000);this.lastFrame=now;
    if(this.state){
      const s=this.state,rate=Math.min(s.runtime.speed,.25*s.runtime.speed/Math.max(.25,s.runtime.step_ms/1000));
      const time=s.t+(s.runtime.paused?0:Math.min(.25,(now-(this.stateReceived||now))/1000*rate));
      this.sun.intensity=2.1+s.weather.light*2;this.sun.color.setHSL(.11,.25+.1*s.weather.light,.8);
      for(const [id,e] of this.flies){
        const f=e.state;e.group.position.lerp(e.target,1-Math.exp(-dt*10));const diff=Math.atan2(Math.sin(e.heading-e.group.rotation.y),Math.cos(e.heading-e.group.rotation.y));e.group.rotation.y+=diff*(1-Math.exp(-dt*10));e.group.rotation.z=f.alive?0:Math.PI;
        const flying=f.alive&&Math.max(0,f.motors?.[2]||0)>0&&f.y>groundY(f.x,f.z)+.5;
        e.wings.forEach(w=>w.pivot.rotation.z=w.sign*(flying?.28+Math.sin(time*85)*.55*Math.max(0,f.motors?.[2]||0):.12));
        e.legs.forEach(l=>l.pivot.rotation.x=f.alive&&f.speed>.1?Math.sin(time*13+l.phase)*.2:0);
        e.marker.position.set(e.group.position.x,groundY(f.x,f.z)+.02,e.group.position.z);e.marker.visible=id===this.selected;
        e.sense.position.copy(e.marker.position);e.sense.visible=this.sense&&id===this.selected;
        e.trail.visible=this.trails;
        const projected=e.group.position.clone().add(new THREE.Vector3(0,1.0,0)).project(this.camera);
        const rect=this.container.getBoundingClientRect();e.label.style.left=`${(projected.x*.5+.5)*rect.width}px`;e.label.style.top=`${(-projected.y*.5+.5)*rect.height}px`;e.label.style.display=projected.z<1&&projected.z>-1?'block':'none';e.label.classList.toggle('selected',id===this.selected);
        const text=f.last_word&&s.t-f.last_signal_t<4&&s.communication?f.last_word:null;
        if(e.label.dataset.word!==(text||'')){e.label.replaceChildren(document.createTextNode(id));if(text){const b=document.createElement('span');b.className='speech';b.textContent=text;e.label.append(b)}e.label.dataset.word=text||''}
      }
      if(this.following){const e=this.flies.get(this.selected);if(e){const delta=e.group.position.clone().sub(this.controls.target).multiplyScalar(1-Math.exp(-dt*5));this.controls.target.add(delta);this.camera.position.add(delta)}}
      this.rain.visible=s.weather.rain>.1;
      if(this.rain.visible){const p=this.rain.geometry.attributes.position;for(let i=0;i<this.rainBase.length;i++){const [x,yy,z]=this.rainBase[i],y=((yy-time*10)%18+18)%18;p.setXYZ(i*2,x,y,z);p.setXYZ(i*2+1,x+.12,y+.8,z-.1)}p.needsUpdate=true;this.rain.material.opacity=.12+s.weather.rain*.23}
    }
    this.controls.update();this.renderer.render(this.scene,this.camera);this.frameCount++;
    if(now-this.lastFPS>1000){this.onFPS(Math.round(this.frameCount*1000/(now-this.lastFPS)));this.frameCount=0;this.lastFPS=now}
  }
}
