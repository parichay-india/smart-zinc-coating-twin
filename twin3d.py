"""Game-like 3-D digital-twin scene of the hot-dip galvanizing air-knife coating section.

scene_html(params) returns a self-contained HTML document (embedded by Streamlit via
components.html). A continuous steel strip rises out of a glowing molten-zinc pot, through
the snout and a pair of opposed air knives whose high-velocity jets wipe the coating to
spec. Coating sheath colour/thickness, knife stand-off, jet intensity, strip speed, steam
and sparks all react live to the model output and the process controls. Cinematic lighting,
damped orbit camera, preset views, pause and auto-rotate give it an interactive, game feel.

Rendered with three.js r128 (manual orbit controls — OrbitControls is not bundled in r128).
"""
import json


def scene_html(params: dict) -> str:
    data = json.dumps(params)
    html = r"""
<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
  html,body{margin:0;height:100%;overflow:hidden;background:radial-gradient(ellipse at 50% 22%,#16222f 0%,#080b10 75%);
            font-family:'Inter','Segoe UI',Arial,sans-serif;color:#cfe3ff}
  #c{width:100%;height:100%;display:block;cursor:grab} #c:active{cursor:grabbing}
  .panel{position:absolute;background:rgba(9,15,22,.62);border:1px solid rgba(90,140,200,.30);
         border-radius:10px;backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px)}
  #hud{left:12px;top:11px;padding:10px 13px;font-size:12px;line-height:1.7;min-width:150px}
  #hud .row{display:flex;justify-content:space-between;gap:14px}
  #hud b{color:#7fd1ff;font-variant-numeric:tabular-nums}
  #hud .lbl{color:#90a9c6}
  #qbar{height:7px;border-radius:4px;margin-top:8px;background:#16212e;overflow:hidden;border:1px solid #21384c}
  #qfill{height:100%;width:50%;transition:width .4s,background .4s}
  #badge{right:14px;top:12px;padding:8px 16px;border-radius:22px;font-weight:700;font-size:13px;letter-spacing:.4px}
  .ok{background:#10331d;color:#86ffae;border:1px solid #2f7d4f;box-shadow:0 0 22px rgba(60,200,120,.30)}
  .bad{background:#3a1c1c;color:#ff9d9d;border:1px solid #7d3030;box-shadow:0 0 22px rgba(220,80,80,.26)}
  #ctrl{right:14px;bottom:12px;padding:7px;display:flex;gap:6px}
  #ctrl button{background:#13263b;color:#bcd6f2;border:1px solid #2b5070;border-radius:7px;
               padding:6px 10px;font-size:11px;cursor:pointer;transition:.15s}
  #ctrl button:hover{background:#1d3a59;color:#eaf4ff}
  #ctrl button.on{background:#1f6feb;color:#fff;border-color:#3b82f6}
  #tip{left:12px;bottom:11px;padding:6px 10px;color:#7c93ad;font-size:11px}
  #title{position:absolute;left:50%;top:12px;transform:translateX(-50%);font-size:11px;
         font-weight:700;letter-spacing:1px;color:#5b7a99}
</style></head>
<body>
<canvas id="c"></canvas>
<div id="hud" class="panel">
  <div class="row"><span class="lbl">Line speed</span><b><span id="vSpeed"></span> m/min</b></div>
  <div class="row"><span class="lbl">Air-knife</span><b><span id="vPress"></span> kPa</b></div>
  <div class="row"><span class="lbl">Stand-off</span><b><span id="vGap"></span> mm</b></div>
  <div class="row"><span class="lbl">Coating</span><b><span id="vCoat"></span> g/m²</b></div>
  <div class="row"><span class="lbl">Target</span><b><span id="vTgt"></span> g/m²</b></div>
  <div id="qbar"><div id="qfill"></div></div>
</div>
<div id="badge" class="panel"></div>
<div id="ctrl" class="panel">
  <button id="bOver" class="on">Overview</button>
  <button id="bWipe">Wiping zone</button>
  <button id="bPot">Pot</button>
  <button id="bRot" class="on">Auto-rotate</button>
  <button id="bPause">Pause</button>
</div>
<div id="tip" class="panel">drag to orbit · scroll to zoom</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script>if(typeof THREE==='undefined'){document.write('<scr'+'ipt src="https://cdn.jsdelivr.net/npm/three@0.128.0/build/three.min.js"><\/scr'+'ipt>');}</script>
<script>if(typeof THREE==='undefined'){document.write('<scr'+'ipt src="https://unpkg.com/three@0.128.0/build/three.min.js"><\/scr'+'ipt>');}</script>
<script>
const P = __PARAMS__;
const clamp=(v,a,b)=>Math.min(b,Math.max(a,v));
const map=(v,a,b,c,d)=>c+(d-c)*clamp((v-a)/(b-a),0,1);
const lerp=(a,b,t)=>a+(b-a)*t;

// ---------------- HUD (filled first, so the live values show even if WebGL is unavailable) ----------------
const ratio=P.coating/Math.max(P.target,1);
document.getElementById('vSpeed').textContent=P.speed.toFixed(0);
document.getElementById('vPress').textContent=P.pressure.toFixed(1);
document.getElementById('vGap').textContent=P.gap.toFixed(1);
document.getElementById('vCoat').textContent=P.coating.toFixed(1);
document.getElementById('vTgt').textContent=P.target.toFixed(0);
const oc=clamp((ratio-1)*100,-20,40);
const qfill=document.getElementById('qfill');
qfill.style.width=map(Math.abs(P.coating-P.target),0,P.target*0.3,8,100).toFixed(0)+'%';
qfill.style.background=P.on_target?'#3fe08a':(ratio>1.10?'#ff5a3c':'#ffcf5a');
const badge=document.getElementById('badge');
badge.className='panel '+(P.on_target?'ok':'bad');
badge.textContent=P.on_target?'\u25CF ON TARGET':('\u25B2 OVER-COATING +'+oc.toFixed(1)+'%');

const cv=document.getElementById('c');
try {
if(typeof THREE==='undefined') throw new Error('three.js did not load');
const renderer=new THREE.WebGLRenderer({canvas:cv,antialias:true,alpha:true});
renderer.setPixelRatio(Math.min(window.devicePixelRatio,2));
renderer.toneMapping=THREE.ACESFilmicToneMapping; renderer.toneMappingExposure=1.12;
const scene=new THREE.Scene(); scene.fog=new THREE.FogExp2(0x080b10,0.020);
const cam=new THREE.PerspectiveCamera(46,16/9,0.1,300);

// ---------------- lights ----------------
scene.add(new THREE.HemisphereLight(0x9fc0ff,0x14202c,0.55));
scene.add(new THREE.AmbientLight(0x445a82,0.35));
const key=new THREE.DirectionalLight(0xbfd4ff,0.85); key.position.set(7,12,8); scene.add(key);
const rim=new THREE.DirectionalLight(0x3a6ea5,0.5); rim.position.set(-7,4,-6); scene.add(rim);
const glow=new THREE.PointLight(0xff7a18,3.0,26,2); glow.position.set(0,-0.5,0); scene.add(glow);
const knifeL=new THREE.PointLight(0x8fe0ff,0.6,10); knifeL.position.set(0,0.2,0); scene.add(knifeL);

// ---------------- floor + grid ----------------
const floor=new THREE.Mesh(new THREE.PlaneGeometry(80,80),
  new THREE.MeshStandardMaterial({color:0x0c151e,metalness:0.6,roughness:0.65}));
floor.rotation.x=-Math.PI/2; floor.position.y=-2.62; scene.add(floor);
const grid=new THREE.GridHelper(60,60,0x244563,0x142838); grid.position.y=-2.6; scene.add(grid);

// ---------------- steel support frame ----------------
const steel=new THREE.MeshStandardMaterial({color:0x36404b,metalness:0.85,roughness:0.45});
const safety=new THREE.MeshStandardMaterial({color:0xc9a227,metalness:0.6,roughness:0.5});
function column(x,z){const c=new THREE.Mesh(new THREE.BoxGeometry(0.22,9.4,0.22),steel);c.position.set(x,2.1,z);scene.add(c);}
[-2.6,2.6].forEach(x=>[-1.9,1.9].forEach(z=>column(x,z)));
const topBeamG=new THREE.BoxGeometry(5.6,0.26,0.26);
[-1.9,1.9].forEach(z=>{const b=new THREE.Mesh(topBeamG,steel);b.position.set(0,6.7,z);scene.add(b);});

// ---------------- zinc pot ----------------
const pot=new THREE.Mesh(new THREE.BoxGeometry(4.6,1.9,3.2),
  new THREE.MeshStandardMaterial({color:0x262b31,metalness:0.9,roughness:0.38}));
pot.position.y=-1.55; scene.add(pot);
const potRim=new THREE.Mesh(new THREE.TorusGeometry(2.05,0.10,12,40),safety); // hazard rim
potRim.rotation.x=Math.PI/2; potRim.position.y=-0.58; potRim.scale.z=0.72; scene.add(potRim);
// molten surface (animated emissive)
const moltenMat=new THREE.MeshStandardMaterial({color:0xff6a00,emissive:0xff4a00,emissiveIntensity:1.5,
  metalness:0.5,roughness:0.25});
const molten=new THREE.Mesh(new THREE.PlaneGeometry(4.0,2.7,40,28),moltenMat);
molten.rotation.x=-Math.PI/2; molten.position.y=-0.6; scene.add(molten);
const moltenBase=molten.geometry.attributes.position.array.slice();
// glow halo sprite over the pot
function halo(color,size,y){const cnv=document.createElement('canvas');cnv.width=cnv.height=128;const g=cnv.getContext('2d');
  const grd=g.createRadialGradient(64,64,0,64,64,64);grd.addColorStop(0,color);grd.addColorStop(1,'rgba(0,0,0,0)');
  g.fillStyle=grd;g.fillRect(0,0,128,128);const sp=new THREE.Sprite(new THREE.SpriteMaterial({map:new THREE.CanvasTexture(cnv),
  blending:THREE.AdditiveBlending,depthWrite:false,opacity:0.85}));sp.scale.set(size,size,1);sp.position.set(0,y,0);scene.add(sp);return sp;}
const potHalo=halo('rgba(255,130,30,0.9)',6.5,-0.5);

// ---------------- snout (angled hood into the bath) ----------------
const snout=new THREE.Mesh(new THREE.BoxGeometry(2.0,1.5,0.5),steel);
snout.position.set(0,-0.1,0.95); snout.rotation.x=-0.5; scene.add(snout);

// ---------------- rolls ----------------
const rollMat=new THREE.MeshStandardMaterial({color:0x707d8a,metalness:0.95,roughness:0.3});
const topRoll=new THREE.Mesh(new THREE.CylinderGeometry(0.34,0.34,3.0,28),rollMat);
topRoll.rotation.z=Math.PI/2; topRoll.position.set(0,5.6,0); scene.add(topRoll);

// ---------------- strip ----------------
function stripTexture(){const c=document.createElement('canvas');c.width=64;c.height=256;const x=c.getContext('2d');
  x.fillStyle='#c9d3df';x.fillRect(0,0,64,256);
  for(let i=0;i<256;i+=14){x.fillStyle=i%28?'#b6c2d1':'#dde4ee';x.fillRect(0,i,64,7);}
  const t=new THREE.CanvasTexture(c);t.wrapS=t.wrapT=THREE.RepeatWrapping;t.repeat.set(1,5);return t;}
const stripTex=stripTexture();
const W=map(P.width,900,1530,1.15,2.45);
const strip=new THREE.Mesh(new THREE.BoxGeometry(W,8.2,0.06),
  new THREE.MeshStandardMaterial({map:stripTex,color:0xe9eff6,metalness:0.92,roughness:0.3,
  emissive:0x5a1e00,emissiveIntensity:0.30}));
strip.position.y=1.7; scene.add(strip);

// ---------------- coating sheath (deposited zinc above the knives) ----------------
let col=0x9effc4, em=0x3fe08a;                    // on-target: green
if(ratio>1.10){col=0xff6a4c;em=0xff3a1e;}         // heavy over-coat: red
else if(ratio>1.03){col=0xffd24a;em=0xffb020;}    // mild over-coat: amber
const sheathT=map(P.coating,40,220,0.06,0.40);
const sheath=new THREE.Mesh(new THREE.BoxGeometry(W+sheathT,4.9,0.06+sheathT),
  new THREE.MeshStandardMaterial({color:col,emissive:em,emissiveIntensity:0.55,metalness:0.7,
  roughness:0.28,transparent:true,opacity:0.5}));
sheath.position.y=2.35; scene.add(sheath);

// ---------------- air-knife assembly ----------------
const g=map(P.gap,12,26,0.18,0.66);
const housMat=new THREE.MeshStandardMaterial({color:0x9fb6cc,metalness:0.95,roughness:0.22});
const header=new THREE.Mesh(new THREE.BoxGeometry(W*1.15,0.2,0.2),steel); header.position.set(0,0.55,0); scene.add(header);
const jetMat=()=>new THREE.MeshBasicMaterial({color:0x8fe0ff,transparent:true,opacity:0.30,
  blending:THREE.AdditiveBlending,depthWrite:false,side:THREE.DoubleSide});
const jets=[];
[1,-1].forEach(s=>{
  const z=s*(0.03+g);
  // housing
  const h=new THREE.Mesh(new THREE.BoxGeometry(W*0.98,0.22,0.30),housMat); h.position.set(0,-0.05,z*1.7); scene.add(h);
  // tapered nozzle toward the strip
  const noz=new THREE.Mesh(new THREE.BoxGeometry(W*0.96,0.13,0.18),housMat); noz.position.set(0,-0.05,z*0.95); scene.add(noz);
  // mounting arm to header
  const arm=new THREE.Mesh(new THREE.BoxGeometry(0.12,0.7,0.12),steel); arm.position.set(W*0.4,0.25,z*1.7); scene.add(arm);
  // jet sheet
  const jm=jetMat();
  const jet=new THREE.Mesh(new THREE.PlaneGeometry(W*0.92,0.5,1,1),jm);
  jet.position.set(0,-0.05,z*0.5); jet.rotation.y=Math.PI/2*(s>0?-1:1);
  jet.scale.x=g*2.0; scene.add(jet); jets.push({m:jm,s:s});
});

// ---------------- particle systems ----------------
function pts(n,size,color,op){const pos=new Float32Array(n*3);const geo=new THREE.BufferGeometry();
  geo.setAttribute('position',new THREE.BufferAttribute(pos,3));
  return new THREE.Points(geo,new THREE.PointsMaterial({color:color,size:size,transparent:true,opacity:op,
  blending:THREE.AdditiveBlending,depthWrite:false}));}
// steam/fume rising from wiping zone
const NF=200, fume=pts(NF,0.11,0xffbf80,0.45), fpa=fume.geometry.attributes.position.array, fv=[];
for(let i=0;i<NF;i++){fpa[i*3]=(Math.random()-0.5)*W;fpa[i*3+1]=-0.1+Math.random()*3.6;fpa[i*3+2]=(Math.random()-0.5)*1.7;fv.push(0.004+Math.random()*0.012);}
scene.add(fume);
// sparks at the wiping line
const NS=70, spark=pts(NS,0.05,0xffe6a0,0.9), spa=spark.geometry.attributes.position.array, sv=[];
for(let i=0;i<NS;i++){spa[i*3]=(Math.random()-0.5)*W;spa[i*3+1]=-0.05;spa[i*3+2]=(Math.random()-0.5)*0.3;sv.push([(Math.random()-0.5)*0.04,0.02+Math.random()*0.05,(Math.random()-0.5)*0.04]);}
scene.add(spark);

// ---------------- camera (damped orbit + presets) ----------------
let tgt={r:13,th:0.72,ph:1.12,fx:0,fy:0.8};            // target spherical + focus
let cur={r:13,th:0.72,ph:1.12,fx:0,fy:0.8};            // current (damped)
let drag=false,px=0,py=0,auto=true,paused=false;
function applyCam(){cam.position.set(cur.fx+cur.r*Math.sin(cur.ph)*Math.sin(cur.th),
  cur.r*Math.cos(cur.ph)+cur.fy, cur.fx+cur.r*Math.sin(cur.ph)*Math.cos(cur.th));
  cam.lookAt(0,cur.fy,0);}
cv.addEventListener('pointerdown',e=>{drag=true;auto=false;setBtn('bRot',false);px=e.clientX;py=e.clientY;});
window.addEventListener('pointerup',()=>drag=false);
window.addEventListener('pointermove',e=>{if(!drag)return;tgt.th-=(e.clientX-px)*0.01;
  tgt.ph=clamp(tgt.ph-(e.clientY-py)*0.01,0.30,1.5);px=e.clientX;py=e.clientY;});
cv.addEventListener('wheel',e=>{tgt.r=clamp(tgt.r+e.deltaY*0.012,5,24);e.preventDefault();},{passive:false});
function setBtn(id,on){document.getElementById(id).classList.toggle('on',on);}
document.getElementById('bOver').onclick=()=>{tgt={r:13,th:0.72,ph:1.12,fx:0,fy:0.8};};
document.getElementById('bWipe').onclick=()=>{tgt={r:6.5,th:0.5,ph:1.25,fx:0,fy:0.2};};
document.getElementById('bPot').onclick =()=>{tgt={r:7.5,th:1.1,ph:1.42,fx:0,fy:-0.7};};
document.getElementById('bRot').onclick =()=>{auto=!auto;setBtn('bRot',auto);};
document.getElementById('bPause').onclick=()=>{paused=!paused;setBtn('bPause',paused);
  document.getElementById('bPause').textContent=paused?'Play':'Pause';};

// ---------------- animate ----------------
let t0=performance.now();
const scroll=map(P.speed,27,180,0.004,0.034);
function resize(){const w=cv.clientWidth||cv.parentElement.clientWidth,h=cv.clientHeight||480;
  renderer.setSize(w,h,false);cam.aspect=w/h;cam.updateProjectionMatrix();}
function animate(){
  requestAnimationFrame(animate);
  const t=(performance.now()-t0)/1000;
  if(!paused){
    stripTex.offset.y-=scroll;
    moltenMat.emissiveIntensity=1.25+0.4*Math.sin(t*2.6); glow.intensity=2.4+0.7*Math.sin(t*2.6);
    potHalo.material.opacity=0.7+0.18*Math.sin(t*2.6);
    // molten surface ripple
    const mp=molten.geometry.attributes.position;
    for(let i=0;i<mp.count;i++){const x=moltenBase[i*3],y=moltenBase[i*3+1];
      mp.array[i*3+2]=Math.sin(x*2.0+t*3)*0.05+Math.cos(y*2.5+t*2.3)*0.05;}
    mp.needsUpdate=true;
    // jet flicker
    jets.forEach((j,k)=>{j.m.opacity=0.22+0.14*Math.abs(Math.sin(t*8+k))*map(P.pressure,8,55,0.5,1.4);});
    knifeL.intensity=0.4+0.3*Math.sin(t*9);
    // fumes
    const sp=0.6+P.speed/120;
    for(let i=0;i<NF;i++){let y=fpa[i*3+1]+fv[i]*sp;if(y>3.7)y=-0.1;fpa[i*3+1]=y;}
    fume.geometry.attributes.position.needsUpdate=true;
    // sparks (intensity scales with pressure)
    const si=map(P.pressure,8,55,0.3,1.0);
    for(let i=0;i<NS;i++){spa[i*3]+=sv[i][0];spa[i*3+1]+=sv[i][1]*si;spa[i*3+2]+=sv[i][2];
      if(spa[i*3+1]>1.4){spa[i*3]=(Math.random()-0.5)*W;spa[i*3+1]=-0.05;spa[i*3+2]=(Math.random()-0.5)*0.3;}}
    spark.geometry.attributes.position.needsUpdate=true;
    if(auto) tgt.th+=0.0028;
  }
  // damp camera toward target
  for(const k in cur) cur[k]=lerp(cur[k],tgt[k],0.08);
  applyCam(); renderer.render(scene,cam);
}
window.addEventListener('resize',resize); resize(); applyCam(); animate();
} catch(err){
  console.error('twin 3-D init failed:', err);
  cv.style.display='none';
  const m=document.createElement('div');
  m.style.cssText='position:absolute;inset:0;display:flex;align-items:center;justify-content:center;'+
    'text-align:center;padding:24px;color:#9fb8d0;font-size:13px;line-height:1.6';
  m.innerHTML='The 3-D view could not start in this browser (WebGL disabled or the graphics script was blocked).<br>'+
    'The live coating values are shown above, and every other tab works normally.';
  document.body.appendChild(m);
}
</script></body></html>
"""
    return html.replace("__PARAMS__", data)
