#!/usr/bin/env node
import { createServer } from 'node:http';
import { readFile, mkdir } from 'node:fs/promises';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const appPackage = path.join(repo, 'tools/pdoom-video/app/package.json');
const require = createRequire(appPackage);
const { chromium } = require('playwright-core');
const threePath = path.join(path.dirname(require.resolve('three')), 'three.module.js');
const outDir = path.resolve(process.argv[2] || '');
if (!process.argv[2]) throw new Error('usage: node render_pdoom_scenes.mjs <output-dir>');

const html = `<!doctype html><html><head><meta charset="utf-8"><style>
html,body{margin:0;width:1080px;height:1920px;overflow:hidden;background:#09131d;color:#f4f7fa;font-family:"Noto Sans Thai",sans-serif}
#stage{position:absolute;inset:0}canvas{display:block;width:1080px;height:1920px}
#copy{position:absolute;left:82px;right:82px;top:230px;text-align:left}
#eyebrow{font-size:28px;font-weight:600;letter-spacing:1px;color:#50d6c8;text-transform:uppercase}
#title{font-size:62px;line-height:1.12;font-weight:750;margin-top:16px;max-width:900px}
#brand{position:absolute;top:78px;left:82px;font:700 28px sans-serif;color:#50d6c8;letter-spacing:1px}
</style></head><body><div id="stage"></div><div id="brand">SOLOCORP OS · THE POWER OF ONE</div>
<div id="copy"><div id="eyebrow"></div><div id="title"></div></div>
<script type="module" src="/scene.js"></script></body></html>`;

const sceneJs = `import * as THREE from '/three.module.js';
const W=1080,H=1920,host=document.querySelector('#stage');
const renderer=new THREE.WebGLRenderer({antialias:true,alpha:false,preserveDrawingBuffer:true});
renderer.setSize(W,H,false);renderer.setPixelRatio(1);renderer.setClearColor(0x09131d,1);host.appendChild(renderer.domElement);
const scene=new THREE.Scene();scene.background=new THREE.Color(0x09131d);
const camera=new THREE.PerspectiveCamera(35,W/H,0.1,100);camera.position.set(0,0,13);
scene.add(new THREE.AmbientLight(0xbad4e8,2));
const key=new THREE.DirectionalLight(0x75e0d0,3);key.position.set(-4,8,8);scene.add(key);
const colors=[0x23b8a8,0x45a0ff,0xffb84d,0xf06d6d,0x8ad66b,0xb08bff];
function box(x,y,z,w,h,d,color,rough=.35){const m=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),new THREE.MeshStandardMaterial({color,roughness:rough,metalness:.16}));m.position.set(x,y,z);scene.add(m);return m}
function line(points,color=0x426071,r=.035){const c=new THREE.CatmullRomCurve3(points.map(p=>new THREE.Vector3(...p)));const m=new THREE.Mesh(new THREE.TubeGeometry(c,48,r,8,false),new THREE.MeshStandardMaterial({color,emissive:color,emissiveIntensity:.3}));scene.add(m);return m}
function ring(x,y,z,r,color){const o=new THREE.Mesh(new THREE.TorusGeometry(r,.06,12,64),new THREE.MeshStandardMaterial({color,emissive:color,emissiveIntensity:.22}));o.position.set(x,y,z);scene.add(o);return o}
function make(i){
 const c=colors[i%colors.length];
 if(i===0){ring(0,.65,.1,1.05,0xffb84d);box(0,.65,.25,1.45,1.45,.2,0x142b35);line([[-.04,.65,.5],[.48,1.0,.5]],0xffffff,.045);line([[-.04,.65,.52],[-.52,.25,.52]],0xe66d59,.035);box(0,-1.25,-.4,2.8,.32,.22,0x284d5b);for(let n=0;n<4;n++)box(-.95+n*.62,-.35,-.2,.35,.26,.16,colors[n]);}
 else if(i===1){box(0,.45,-.4,2.8,2.1,.28,0x284957);box(0,.45,-.17,2.45,1.78,.12,0x101f2a);box(0,-.85,-.35,3.25,.18,.45,0x9ba9a8);box(0,-.52,-.3,2.75,.42,.24,0x1e3844);for(let n=0;n<6;n++)box(-1.05+n*.42,-.5,-.12,.24,.11,.08,n%2?0xd5dfdc:0x4dc7bb);line([[-1.25,-1.0,.1],[1.25,-1.0,.1]],0x50d6c8,.045);}
 else if(i===2){box(0,1.25,-.35,1.45,.7,.3,0x45a0ff);line([[0,.85,.05],[0,.35,.05]],c,.045);for(let n=0;n<3;n++){const x=(n-1)*1.25;line([[0,.35,.05],[x,-.3,.05]],colors[n],.035);box(x,-.65,-.25,.92,.72,.3,colors[n]);ring(x,-1.35,.05,.2,colors[n]);}}
 else if(i===3){box(0,1.55,-.4,1.5,.48,.3,0x50d6c8);line([[0,1.3,.05],[0,1.05,.05]],0x6d8790,.03);line([[-1.55,1.05,.05],[1.55,1.05,.05]],0x6d8790,.03);for(let n=0;n<18;n++){const col=n%6,row=Math.floor(n/6),x=(col-2.5)*.62,y=.65-row*.68;line([[x,1.05,.05],[x,y+.2,.05]],0x36515d,.018);box(x,y,-.25,.43,.34,.24,colors[n%6]);}}
 else if(i===4){box(0,.05,-.35,3.5,.34,.36,0x45a0ff);for(let n=0;n<4;n++){const x=(n-1.5)*.88;line([[x,1.15,.05],[x,.3,.05]],colors[n],.04);line([[x,-.15,.05],[x,-.8,.05]],colors[n],.04);box(x,1.35,-.25,.55,.55,.3,colors[n]);box(x,-1.05,-.25,.55,.55,.3,colors[n]);}ring(0,.05,.05,.43,0xffb84d);}
 else if(i===5){box(0,.3,-.35,1.2,1.0,.3,0xffb84d);for(let n=0;n<5;n++){const x=(n-2)*.73;line([[0,-.25,.05],[x,-.9,.05]],colors[n],.03);box(x,-1.3,-.25,.55,.6,.3,colors[n]);}}
 else if(i===6){box(-.88,.5,-.3,1.25,1.35,.35,0x23b8a8);box(.88,.5,-.3,1.25,1.35,.35,0x45a0ff);box(0,-.95,-.3,2.9,.32,.34,0xffb84d);line([[-.88,-.2,.05],[-.88,-.65,.05],[0,-.65,.05]],0x23b8a8,.04);line([[.88,-.2,.05],[.88,-.65,.05],[0,-.65,.05]],0x45a0ff,.04);ring(0,-.95,.1,.48,0xffb84d);}
 else if(i===7){const shield=new THREE.Mesh(new THREE.OctahedronGeometry(1.05),new THREE.MeshStandardMaterial({color:0x153d3b,metalness:.2,roughness:.3,wireframe:true}));shield.position.set(-.75,.05,-.3);scene.add(shield);ring(-.75,.05,.5,.47,0xe6aa54);line([[-.75,.05,.62],[-.75,.33,.62]],0xe6aa54,.055);line([[-.75,.05,.62],[-.52,-.1,.62]],0xe6aa54,.04);for(let n=0;n<5;n++){const y=1.35-n*.62;box(1.15,y,.15,.9,.14,.1,n<3?0x4dd0a7:0xe6aa54);box(1.88,y,.16,.2,.2,.1,n<3?0x4dd0a7:0xe6aa54);}}
 else if(i===8){for(let n=0;n<5;n++){const x=(n-2)*.66,y=-1.4+n*.58;box(x,y,-.3,.54,.48,.28,colors[n]);if(n<4)line([[x+.28,y+.2,.05],[x+.38,y+.58,.05]],0x78949b,.035);}ring(0,1.35,.1,.36,0xffb84d);}
 else{const tower=box(-.55,.5,-.5,.48,2.5,.35,0xe5e8dc);box(-.55,1.82,-.35,.86,.26,.4,0x50d6c8);const beam=new THREE.Mesh(new THREE.ConeGeometry(1.5,3.8,32,1,true),new THREE.MeshBasicMaterial({color:0xf5cf82,transparent:true,opacity:.16,side:THREE.DoubleSide}));beam.position.set(.6,1.2,-.8);beam.rotation.z=-Math.PI/2.8;scene.add(beam);line([[-2.0,-1.7,0],[-.8,-1.5,.4],[.7,-1.8,.7],[2.0,-1.4,0]],0xffb84d,.06);for(let n=0;n<3;n++)box(-1.4+n*.85,-1.0,.3,.5,.44,.3,colors[n]);}
 return c;
}
window.drawScene=(item,index)=>{scene.clear();scene.background=new THREE.Color(0x09131d);scene.add(new THREE.AmbientLight(0xbad4e8,2));scene.add(key);make(index);document.querySelector('#eyebrow').textContent=item.kicker||('SCENE '+String(index+1).padStart(2,'0'));document.querySelector('#title').textContent=item.title||'';camera.position.x=Math.sin(index*.42)*.25;camera.lookAt(0,.05,0);renderer.render(scene,camera);};
window.ready=true;`;

const server = createServer(async (req, res) => {
  if (req.url === '/') { res.writeHead(200, { 'content-type': 'text/html; charset=utf-8' }); res.end(html); return; }
  if (req.url === '/scene.js') { res.writeHead(200, { 'content-type': 'text/javascript; charset=utf-8' }); res.end(sceneJs); return; }
  if (req.url?.endsWith('.js')) {
    const file = path.join(path.dirname(threePath), path.basename(req.url));
    try { res.writeHead(200, { 'content-type': 'text/javascript; charset=utf-8' }); res.end(await readFile(file)); return; }
    catch { res.writeHead(404); res.end('not found'); return; }
  }
  if (req.url === '/favicon.ico') { res.writeHead(204); res.end(); return; }
  res.writeHead(404); res.end('not found');
});
await mkdir(outDir, { recursive: true });
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const address = server.address();
let browser;
try {
  browser = await chromium.launch({ headless: true, executablePath: '/usr/bin/google-chrome', args: ['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-webgl','--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('console', message => { if (message.type() === 'error') process.stderr.write(`browser console: ${message.text()}\n`); });
  page.on('pageerror', error => process.stderr.write(`browser page error: ${error.message}\n`));
  await page.goto(`http://127.0.0.1:${address.port}/`, { waitUntil: 'load' });
  await page.waitForFunction(() => window.ready === true, null, { timeout: 10000 });
  const scenes = JSON.parse(await new Promise(resolve => { let s=''; process.stdin.setEncoding('utf8'); process.stdin.on('data',x=>s+=x); process.stdin.on('end',()=>resolve(s)); }));
  if (!Array.isArray(scenes) || ![6,10].includes(scenes.length)) throw new Error('six or ten scenes are required');
  const output=[];
  for (let i=0;i<scenes.length;i++) {
    await page.evaluate(({item,index}) => window.drawScene(item,index), { item: scenes[i], index: i });
    const file=path.join(outDir,`scene-${String(i+1).padStart(2,'0')}.png`);
    await page.screenshot({path:file});
    output.push(file);
  }
  process.stdout.write(JSON.stringify({status:'completed',engine:'three.js-pdoom-local',scene_count:output.length,frames:output,network_used:false}));
} finally {
  if (browser) await browser.close();
  server.close();
}
