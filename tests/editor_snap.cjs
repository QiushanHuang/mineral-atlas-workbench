const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const file = path.join(__dirname, '../ui/editor-snap.js');
assert.ok(fs.existsSync(file), 'optional local snapping must expose a DOM-free module');
const {proposeTargets, pickSnap} = require(file);
const annotation = features => ({image_size:[1000,800],features});
const feature = (id, kind, points) => ({id,kind,points});
const near = (actual, expected, tolerance=1e-8) => actual.every((value,index)=>Math.abs(value-expected[index])<=tolerance);
const freeze = value => { if(value && typeof value==='object'){Object.freeze(value);for(const item of Object.values(value))freeze(item);}return value; };

// Exact geometry is an independent oracle, not a copy of the intersection algorithm.
const source=freeze(annotation([
  feature('B','edge',[[50,0],[50,100]]),
  feature('A','edge',[[0,40],[100,40]]),
  feature('C','face',[[200,100],[260,100],[260,160],[200,160]])
]));
const before=JSON.stringify(source);
const targets=proposeTargets(source,[]);
assert.equal(JSON.stringify(source),before);
assert.ok(targets.some(t=>t.kind==='intersection'&&near(t.point,[50,40])));
assert.ok(targets.some(t=>t.kind==='midpoint'&&t.featureId==='C'&&near(t.point,[200,130])), 'closed face includes closing segment');
assert.ok(targets.some(t=>t.kind==='vertex'&&t.featureId==='A'&&t.pointIndex===0));
assert.deepEqual(targets,proposeTargets(annotation([...source.features].reverse()),[]), 'input feature order does not select a different target');

const excluded=targets.find(t=>t.kind==='vertex'&&t.featureId==='A'&&t.pointIndex===0).id;
assert.equal(pickSnap([0,40],targets,{scale:1,radius:2,exclude:[excluded]}).target,null,'dragged vertex cannot snap to itself');
const single=[{id:'v',point:[20,20],kind:'vertex',label:'已标端点'}];
assert.deepEqual(pickSnap([30.125,20.25],single,{enabled:false,scale:10}).point,[30.125,20.25]);
assert.equal(pickSnap([20,20],single,{bypass:true}).target,null,'Shift bypass must not leave a hidden snap');
assert.equal(pickSnap([26,20],single,{scale:2,radius:12}).target.id,'v');
assert.equal(pickSnap([26.01,20],single,{scale:2,radius:12}).target,null);
assert.equal(pickSnap([31,20],single,{scale:1,radius:12}).target.id,'v');
assert.equal(pickSnap([31,20],single,{scale:2,radius:12}).target,null,'radius is CSS pixels, not original pixels');
assert.equal(pickSnap([20,20],single,{scale:0}).target,null);
assert.throws(()=>pickSnap([NaN,0],single),/有限|finite/);

const tie=[{id:'middle',point:[51,40],kind:'midpoint',label:'中点'},{id:'saved',point:[49,40],kind:'vertex',label:'端点'}];
assert.equal(pickSnap([50,40],tie).target.id,'saved');
assert.equal(pickSnap([50.2,40],tie).target.id,'middle','closer targets beat kind priority');
assert.equal(pickSnap([50,40],[...tie].reverse()).target.id,'saved');
assert.equal(proposeTargets(annotation([]),[[1,1],[5,1]],[],{includeStart:true}).some(t=>t.kind==='start'),false);
const closure=proposeTargets(annotation([feature('old','edge',[[1,1],[80,80]])]),[[1,1],[5,1],[5,5]],[],{includeStart:true});
assert.equal(pickSnap([1,1],closure).target.kind,'start','closing start remains actionable when it shares an existing vertex');
assert.equal(proposeTargets(annotation([]),[[1,1],[5,1],[5,5]]).some(t=>t.kind==='start'),false);

const extensions=proposeTargets(annotation([
  feature('short','edge',[[0,10],[20,10]]),feature('distant','edge',[[30,0],[30,20]])
]),[]);
assert.equal(extensions.some(t=>t.kind==='intersection'),false,'supporting lines are not extended');
const parallel=proposeTargets(annotation([
  feature('a','edge',[[0,10],[100,10]]),feature('b','edge',[[0,10.00001],[100,9.99999]])
]),[]);
assert.equal(parallel.some(t=>t.kind==='intersection'),false,'near-parallel crossings are too unstable');
const ignored=proposeTargets(annotation([feature('occluded','occlusion',[[10,10],[90,10],[90,90]]),feature('uncertain','uncertain',[[50,0],[50,100]])]),[]);
assert.ok(ignored.every(t=>t.kind==='vertex'),'uncertain and occlusion strokes do not yield inferred segments');

const hints=freeze([{id:'good',point:[400,300],confidence:.9},{id:'weak',point:[450,350],confidence:.2},[500,400],{point:[NaN,0]}]);
assert.equal(proposeTargets(annotation([]),[],hints).length,0);
const hinted=proposeTargets(annotation([]),[],hints,{includeImageCorners:true});
assert.equal(hinted.length,2);
assert.ok(hinted.every(t=>t.kind==='image_corner'&&/候选|未确认/.test(t.label)));
const reusedHintIds=proposeTargets(annotation([]),[],[{id:'corner',point:[100,200]},{id:'corner',point:[200,300]}],{includeImageCorners:true});
assert.equal(new Set(reusedHintIds.map(t=>t.id)).size,2,'reused detector labels must not collapse distinct target identities');
assert.deepEqual(proposeTargets(source,[],undefined),proposeTargets(source,[],null),'missing image service does not remove existing annotation targets');

const duplicates=annotation([feature('b','edge',[[10+1e-8,10],[30,30]]),feature('a','edge',[[10,10],[30,30]])]);
const d=proposeTargets(duplicates,[]);
assert.deepEqual(d,proposeTargets(annotation([...duplicates.features].reverse()),[]));
assert.equal(d.filter(t=>near(t.point,[10,10],1e-6)).length,1);
assert.ok(d.every(t=>t.point.every(Number.isFinite)));
const malformed=proposeTargets({features:[null,{id:'bad',kind:'edge',points:[[NaN,0],[0,0],null,[1,1]]}]},[],[{point:[Infinity,1]}],{includeImageCorners:true});
assert.ok(malformed.every(t=>t.point.every(Number.isFinite)));

const many=annotation(Array.from({length:128},(_,i)=>feature(`F${String(i).padStart(3,'0')}`,'edge',Array.from({length:16},(_,j)=>[j*50,(i*5+j)%790]))));
const bounded=proposeTargets(many,[],[],{maxSegments:32,maxTargets:128});
assert.equal(bounded.meta.truncated,true);
assert.ok(bounded.meta.segments_used<=32);
assert.ok(bounded.length<=128);
assert.ok(bounded.meta.intersections_tested<=32*31/2);
assert.equal(new Set(bounded.map(t=>t.id)).size,bounded.length);
assert.deepEqual(proposeTargets(many,[],[],{maxSegments:32,maxTargets:128}),bounded);
const immutableTargets=freeze([{id:'immutable',point:[11,12],kind:'vertex',label:'端点'}]);
const picked=pickSnap([10,12],immutableTargets);picked.point[0]=99;picked.target.point[1]=99;
assert.deepEqual(immutableTargets[0].point,[11,12],'result points do not alias the supplied targets');
const vm=require('node:vm'),browser=vm.createContext({});
vm.runInContext(fs.readFileSync(file,'utf8'),browser);
assert.equal(typeof browser.AtlasEditorSnap.pickSnap,'function','browser export must load without DOM globals');
console.log('PASS snapping: geometry, CSS radius, disabled/Shift bypass, stable ties, self exclusion, closure, image hints and bounded work');
