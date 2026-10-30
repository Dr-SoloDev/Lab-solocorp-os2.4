#!/usr/bin/env node
// Deterministic, local-only motion graphics for the Model Health v2 campaign.
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {createRequire} from 'node:module';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const require=createRequire(path.join(root,'tools/pdoom-video/app/package.json'));
const {chromium}=require('playwright-core');
const editPath=path.resolve(process.argv[2]||'');
if(!process.argv[2])throw new Error('usage: node render_model_health_frames.mjs edit.json [--preview]');
const out=path.dirname(editPath),preview=process.argv.includes('--preview');
const contentRoot=path.resolve(root,'central_bus/content/local_media');
if(!out.startsWith(contentRoot+path.sep))throw new Error('output must be within central_bus/content/local_media');
const story=JSON.parse(await readFile(editPath,'utf8'));
const html=await readFile(path.join(root,'scripts/media/model_health_motion.html'),'utf8');
await mkdir(path.join(out,'previews'),{recursive:true});
let browser,encoder;
try{
 browser=await chromium.launch({headless:true,executablePath:'/usr/bin/google-chrome',args:['--no-sandbox']});
 const context=await browser.newContext({viewport:{width:1080,height:1920},deviceScaleFactor:1});
 await context.route('**/*',route=>route.abort());
 const page=await context.newPage();
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.setContent(html);await page.evaluate(()=>document.fonts.ready);
 await page.evaluate(data=>{window.story=data;},story);
 const captionChecks=await page.evaluate(()=>window.story.scenes.flatMap(s=>s.cues.map(c=>{
  window.renderFrame((c.start+c.end)/2);
  const rows=splitText(c.text,850,53);
  g.font=font(53,550);
  return {text:c.text,lines:rows.length,widths:rows.map(r=>Math.round(g.measureText(r).width)),start:c.start,end:c.end};
 })));
 if(captionChecks.some(c=>c.lines>2||c.widths.some(w=>w>850)))throw new Error('caption layout check failed');
 const previews=[];
 for(let i=0;i<story.scenes.length;i++){
  const scene=story.scenes[i],t=scene.start+(scene.end-scene.start)*.68;
  await page.evaluate(t=>window.renderFrame(t),t);
  const filename=path.join(out,'previews',`scene-${String(i+1).padStart(2,'0')}.png`);
  await page.screenshot({path:filename});previews.push(filename);
 }
 if(!preview){
  encoder=spawn(process.env.FFMPEG_BIN||'ffmpeg',['-hide_banner','-loglevel','error','-n','-f','image2pipe','-vcodec','mjpeg','-framerate','30','-i','pipe:0','-an','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',path.join(out,'picture.mp4')],{stdio:['pipe','ignore','pipe']});
  let stderr='';encoder.stderr.on('data',b=>stderr+=b.toString());
  const done=new Promise((resolve,reject)=>{encoder.on('error',reject);encoder.on('close',code=>code===0?resolve():reject(new Error(`encoder ${code}: ${stderr.slice(-2000)}`)));});
  // Observe a premature encoder failure immediately; rethrow it when awaited below.
  done.catch(()=>{});
  const frames=Math.ceil(story.duration*30);
  for(let f=0;f<frames;f++){
   if(encoder.exitCode!==null)throw new Error(`encoder exited: ${stderr.slice(-2000)}`);
   await page.evaluate(t=>window.renderFrame(t),f/30);
   const buffer=await page.screenshot({type:'jpeg',quality:94});
   if(!encoder.stdin.write(buffer))await once(encoder.stdin,'drain');
   if(f%150===0)process.stderr.write(`frames ${f}/${frames}\n`);
  }
  encoder.stdin.end();await done;
 }
 if(errors.length)throw new Error(errors.join('\n'));
 const report={status:'completed',engine:'canvas2d-motion-v2',fps:30,duration:story.duration,previews,captionChecks,external_network_used:false};
 await writeFile(path.join(out,preview?'preview-report.json':'picture-report.json'),JSON.stringify(report,null,2));
 process.stdout.write(JSON.stringify(report));
}finally{if(encoder&&encoder.exitCode===null)encoder.kill('SIGTERM');if(browser)await browser.close();}
