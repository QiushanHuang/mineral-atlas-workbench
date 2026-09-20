const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const source=fs.readFileSync(process.argv[2],'utf8'),data=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));
const ctx={};let points=[];for(const n of ['scale','fillRect','fillText'])ctx[n]=()=>{};
const sandbox={console,location:{hash:""},DATA:{models:data,views:{},photos:{}},document:{getElementById:()=>({clientWidth:800,clientHeight:470})},ResizeObserver:class{observe(){}},Image:class{},devicePixelRatio:1};vm.createContext(sandbox);
const cutoff=source.indexOf("$('models').innerHTML=");vm.runInContext(source.slice(0,cutoff)+`;canvas=()=>({ctx:externalCtx,w:800,h:470}); drawAxes=()=>{}; drawMesh=(ctx,r,project)=>capture(project); setProjection=m=>projectionMode=m; updateSelection=()=>drawModel();`,sandbox);
sandbox.externalCtx=ctx;sandbox.capture=p=>{points=[p([0,0,0]),p([1,0,0]),p([0,1,0]),p([0,0,1])];};
function run(code){return vm.runInContext(code,sandbox)}
function gain(){return Math.sqrt(points.slice(1).reduce((s,p)=>s+(p[0]-points[0][0])**2+(p[1]-points[0][1])**2,0));}
run("model=DATA.models['333'];key='333';view=null;showAxes=true;zoom=1.6;projectionMode='oblique-free';R=model.indexing.standardRotation;drawModel()");let g=gain();
run('R=[[Math.cos(.7),-Math.sin(.7),0],[Math.sin(.7),Math.cos(.7),0],[0,0,1]];drawModel()');assert.ok(Math.abs(gain()-g)<1e-8,'drag rotation must not refit magnification');
run('showAxes=false;drawModel()');assert.ok(Math.abs(gain()-g)<1e-8,'axis visibility must not change magnification');
run('selectFace(0,true)');assert.equal(run('zoom'),1.6,'face selection must preserve manual zoom');let free=gain();
run('selectFace(2,true)');assert.ok(Math.abs(gain()-free)<1e-8,'different faces must keep the same orthographic magnification');
run('zoom*=1.5;drawModel()');assert.ok(Math.abs(gain()/free-1.5)<1e-10,'explicit zoom still works');
run("view={scale:150,D:10,offset:[600,900]};bounds=[300,500,600,800];projectionMode='photo';zoom=2;selectFace(0,true)");assert.ok(Math.abs(gain()/Math.sqrt(2)-150*(470/800)*2)<1e-8,'photo-to-face selection preserves magnification at the model origin');
for(const key of Object.keys(data)){run(`model=DATA.models['${key}'];view=null;projectionMode='free';zoom=1.7;selectFace(0,true)`);const expected=gain();for(let i=1;i<data[key].faces.length;i++){run(`selectFace(${i},true)`);assert.ok(Math.abs(gain()-expected)<1e-8,`${key} F${i+1} changed scale`);assert.equal(run('zoom'),1.7);}}
for(const key of Object.keys(data)){run(`model=DATA.models['${key}']`);for(const face of data[key].faces){const h=face.modelMiller.join(' ');assert.equal(run(`symbol(${JSON.stringify(h)})`),h);}if(data[key].indexing.indexCount===4)assert.throws(()=>run("symbol('(1 1 1 0)')"));}
console.log('PASS: all 15 models / 226 face rotations, zoom preservation, 3/4-index roundtrip');
