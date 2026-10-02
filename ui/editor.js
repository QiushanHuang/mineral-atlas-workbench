'use strict';
(() => {
const $=id=>document.getElementById(id), S=AtlasEditorState, C=AtlasEditorCanvas, X=AtlasEditorExperience, Snap=AtlasEditorSnap;
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const number=x=>Number(x).toFixed(4).replace(/\.?0+$/,'');
let token,examples=[],result=null,history=null,selected='',radius=1,busy=false,baseline=null,rotation=null;
let photos=[],photoIndex=0,workingPoints=[],photoZoom=1,photoTransform=null,drag=null,axisPicking=null,axisPoints=[],pendingA=null,pendingC=null;
let packet=null,review=null,photoEpoch=0,yaw=.52,pitch=.52;
let prefs=X.preferences(),snapTargets=[],lastPointer=null,hoverSnap=null,shiftHeld=false,workingRedo=[];
let redrawId=null,faceSeedMode=false;
let workspaceNav=null,layoutWorkspace='model',parametersVisited=false;const activePointers=new Map();
try{prefs=X.preferences(JSON.parse(localStorage.getItem('mineral-atlas-editor-preferences')||'{}'));}catch(e){}
const views=[['frontView','front'],['sideView','side'],['topView','top'],['threeView','three']],rendered={};
function status(text,error=false){$('editorStatus').textContent=text;$('editorStatus').title=text;$('editorStatus').className='status'+(error?' error':'');}
async function saveDocument(kind,document){const r=await api('/api/save-document',{kind,document});$('savedDocument').hidden=false;$('savedDocument').innerHTML=`已保存到本机：<a href="${esc(r.url)}" download>${esc(r.path.split('/').pop())}</a> <small>${esc(r.path)}</small>`;$('recentSaveLink').hidden=false;status('已保存到本机；在“保存与复核”查看文件和下载链接。');return r;}
async function api(path,data){const response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-Atlas-Token':token},body:JSON.stringify(data)});const r=await response.json();if(!response.ok)throw Error(r.error||'本机处理失败');return r;}
async function task(fn){if(busy)return;drag=null;busy=true;$('editorControls').disabled=true;refreshLayoutSummary();try{await fn();}catch(e){status(e.message,true);}finally{busy=false;$('editorControls').disabled=false;updateButtons();}}
function store(){try{localStorage.setItem('mineral-atlas-editor-draft-v2',JSON.stringify(result.draft));}catch(e){status('模型已更新；浏览器草稿保存失败，请下载项目 JSON。',true);}}
function adopt(next,{reset=false,commit=true}={}){
  const before=result;if(before?.fingerprint!==next.fingerprint){$('annotationFace').value='';for(const p of photos)p.alignment=null;}result=next;if(!history||reset){history=new S.History(next);baseline=next.model;radius=C.framing(next.model);rotation=null;yaw=.52;pitch=.52;pendingA=null;pendingC=null;axisPicking=null;axisPoints=[];}else if(commit){baseline=before?.model||baseline;history.commit(next);}
  if(!result.model.faces.some(f=>f.id===selected))selected=result.model.faces[0]?.id||'';
  review=null;$('reviewSuggestions').replaceChildren();$('reviewStatus').textContent=packet?'模型已改变；需要重新导出复核包。':'先生成复核包。';packet=null;
  store();render();if(photos.length){updatePhotoList();drawPhoto();}
}
function updateButtons(){if(!history)return;$('modelUndo').disabled=!history.canUndo;$('modelRedo').disabled=!history.canRedo;$('applySuggestions').disabled=!review;const p=photos[photoIndex];$('photoUndo').disabled=!p?.history.canUndo;$('photoRedo').disabled=!p?.history.canRedo;$('downloadPrompt').disabled=!packet;updateDrawingControls();refreshLayoutSummary();}
function visibleCanvas(node){return !!node&&!node.closest('[hidden]')&&node.getBoundingClientRect().width>0;}
function drawViews(){if(!result||!visibleCanvas($('modelStudio')))return;for(const [id,view] of views)if(visibleCanvas($(id)))rendered[id]=C.draw($(id),result.model,{view,rotation:view==='three'?rotation:null,radius,selected:[selected],axes:result.draft.axes,before:$('showBefore').checked?baseline:null,overlayOpacity:+$('overlayOpacity').value,showVertices:!!axisPicking,showLabels:$('showFaceIds').checked,labels:X.faceLabels(result.model.faces,result.analysis.faces,$('showReferenceIndices').checked),fontSize:prefs.audience==='teacher'?15:11});}
function selection(id){if(!id)return;selected=id;$('selectedFace').value=id;const face=result.model.faces.find(f=>f.id===id);$('planeNormal').value=face.n.map(String).join(' ');$('planeDistance').value=face.d;$('planeLabel').value=face.label||'';$('faceDescription').textContent=`${id} · ${face?.label||'未命名面'} · 模块 ${({body:'主体',top:'上端',bottom:'下端',bevel:'截角',single:'单面'})[face?.module]||'单面'} · ${face?.ids.length||0} 条边`;drawViews();}
function render(){
  $('draftTitle').value=result.draft.title||result.draft.id;
  $('selectedFace').innerHTML=result.model.faces.map(f=>`<option value="${esc(f.id)}">${esc(f.id)} · ${esc(f.label||f.module||'单面')}</option>`).join('');
  const old=$('annotationFace').value;$('annotationFace').innerHTML='<option value="">尚未确定</option>'+result.model.faces.map(f=>`<option value="${esc(f.id)}">${esc(f.id)}</option>`).join('');if(result.model.faces.some(f=>f.id===old))$('annotationFace').value=old;
  selection(selected);const a=result.analysis,q=a.quality||{};
  $('geometryQuality').textContent=`${result.model.vertices.length} 顶点 · ${result.model.edges.length} 棱 · ${result.model.faces.length} 面 · ${q.ok?'几何校验通过':'请核对校验结果'}${result.draft.registration_status==='needs_refit'?' · 外形已改变，旧照片配准需重算':''}`;
  $('historyInfo').textContent=`当前操作 ${history.index} / ${history.items.length-1} · 草稿自动保存在此浏览器`;
  $('analysisSummary').innerHTML=[`体积 ${number(a.volume)}`,`总面积 ${number(a.area)}`,`平行面组 ${(a.parallel_groups||[]).length}`,`轴长 ${(a.axes?.lengths||[]).map(number).join(' : ')}`,`轴角 ${(a.axes?.angles||[]).map(number).join(' / ')}°`,`参考单位 · 无实测尺度`].map(x=>`<span>${esc(x)}</span>`).join('');
  const symbol=f=>{const v=f.index_candidates;if(!v)return '未知';return (v.candidates||[]).slice(0,3).map(c=>`(${c.hkl.join(' ')}) · ${number(c.error_deg)}°`).join('；')||'无容差内低阶解';};
  $('analysisFaces').innerHTML='<table><thead><tr><th>面</th><th>面积</th><th>外法线</th><th>面距</th><th>参考指数候选 / 角偏差</th></tr></thead><tbody>'+(a.faces||[]).map(f=>`<tr><td>${esc(f.id)}</td><td>${number(f.area)}</td><td>${f.normal.map(number).join(' / ')}</td><td>${number(f.distance)}</td><td>${esc(symbol(f))}</td></tr>`).join('')+'</tbody></table>';
  $('analysisEdges').innerHTML='<table><thead><tr><th>棱 / 邻面</th><th>长度</th><th>内二面角</th><th>外法线夹角</th></tr></thead><tbody>'+(a.edges||[]).map(e=>`<tr><td>${esc(e.id)} · ${esc((e.face_ids||[]).join(' / '))}</td><td>${number(e.length)}</td><td>${number(e.interior_angle_deg)}°</td><td>${number(e.exterior_angle_deg)}°</td></tr>`).join('')+'</tbody></table>';
  const symmetry=a.geometry_symmetry_candidates;$('analysisStructures').textContent=`当前参考方向中的几何最高相容群：${(symmetry?.highest_candidates||[]).map(x=>x.point_group+' / '+x.order+'项操作').join('；')||'待解析'}。晶带候选 ${(a.zone_candidates||[]).length} 组。只在当前参考方向检查32类操作，不认定实物点群；详情随解析JSON导出。`;
  const axes=result.draft.axes;$('axisBasis').value=axes.basis.map(r=>r.map(String).join(' ')).join('\n');$('axisCount').value=axes.index_count;$('axisOrigin').value=axes.origin.map(String).join(' ');
  $('axesInfo').textContent=`${axes.index_count===4?'四轴参考设置':'三轴参考设置'} · 轴定义来源：${axes.status==='imported_reference'?'导入参考轴':'用户参考轴'}。${(result.warnings||[]).join(' ')}`;
  updateButtons();
}
async function command(c){const next=await api('/api/editor',{action:'apply',draft:result.draft,command:c});adopt(next);status('修改已校验；可撤销，也可另存新修订。');}
function tuple(text,n=3){const v=text.trim().split(/[\s,]+/).map(Number);if(v.length!==n||v.some(x=>!Number.isFinite(x)))throw Error(`请填写 ${n} 个有限数值`);return v;}
function axisArgs(type){return {type,basis:tuple($('axisBasis').value,9).reduce((a,x,i)=>{if(i%3===0)a.push([]);a[a.length-1].push(x);return a;},[]),index_count:+$('axisCount').value,origin:tuple($('axisOrigin').value)};}
function vectorCross(a,b){return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];}
function unit(v){const l=Math.hypot(...v);if(l<1e-8)throw Error('选取的方向退化，请选择不同位置');return v.map(x=>x/l);}
function setDirection(v){
  const wasPicking=!!axisPicking;
  if($('axisTarget').value==='c')pendingC=unit(v);else pendingA=unit(v);
  const c=pendingC||unit(result.draft.axes.basis.map(r=>r[2]));let a=pendingA||unit(result.draft.axes.basis.map(r=>r[0]));
  const b=unit(vectorCross(c,a));a=unit(vectorCross(b,c));
  const vectors=+ $('axisCount').value===4?[a,a.map((x,i)=>-.5*x+Math.sqrt(3)/2*b[i]),c]:[a,b,c];
  $('axisBasis').value=[0,1,2].map(i=>vectors.map(v=>String(v[i])).join(' ')).join('\n');
  $('axisPickStatus').textContent='已填入右手参考方向。点击“定义轴 · 保持外形”应用。';axisPicking=null;axisPoints=[];drawViews();if(wasPicking){workspaceNav?.activate('parameters');$('axesDisclosure').open=true;status('参考方向已填入；请在晶轴面板点击“定义轴 · 保持外形”应用。');}
}
$('newModel').onclick=()=>task(async()=>{adopt(await api('/api/editor',{action:'create',preset:$('preset').value,title:$('preset').selectedOptions[0].textContent}),{reset:true});packet=null;status('新模型已建立。选择一个面或调整主体比例。');});
$('loadReference').onclick=()=>task(async()=>{adopt(await api('/api/editor',{action:'import',spec:examples[+$('referenceModel').value]}),{reset:true});packet=null;status('已载入参考模型的可编辑副本。');});
$('openDraft').onchange=e=>task(async()=>{const file=e.target.files[0];if(!file)return;const data=JSON.parse(await file.text());adopt(await api('/api/editor',data.schema_version===2?{action:'analyze',draft:data}:{action:'import',spec:data}),{reset:true});packet=null;status('项目已打开。');e.target.value='';});
$('restoreDraft').onclick=()=>task(async()=>{const data=localStorage.getItem('mineral-atlas-editor-draft-v2');if(!data)throw Error('此浏览器尚无保存的草稿');adopt(await api('/api/editor',{action:'analyze',draft:JSON.parse(data)}),{reset:true});status('已恢复本机草稿。');});
$('selectedFace').onchange=e=>selection(e.target.value);
$('draftTitle').onchange=()=>task(()=>command({type:'metadata',title:$('draftTitle').value}));
$('moveFace').onclick=()=>task(()=>command({type:'move_faces',face_ids:[selected],delta:+$('moveAmount').value,scope:$('editScope').value}));
$('moveRange').oninput=()=>$('moveAmount').value=$('moveRange').value;
$('moveRange').onchange=()=>{const delta=+$('moveRange').value;$('moveRange').value=0;if(delta)task(()=>command({type:'move_faces',face_ids:[selected],delta,scope:$('editScope').value}));};
$('scaleModel').onclick=()=>task(async()=>{await command({type:'scale',factors:['scaleX','scaleY','scaleZ'].map(id=>+$(id).value)});['scaleX','scaleY','scaleZ'].forEach(id=>$(id).value=1);});
$('cutPreset').onchange=()=>{$('cutNormal').value=({corner:'1 1 1',top:'0 0 1',bottom:'0 0 -1',bevel:'1 1 0'})[$('cutPreset').value];};$('applyPlane').onclick=()=>task(()=>command({type:'set_plane',face_ids:[selected],normal:tuple($('planeNormal').value),distance:+$('planeDistance').value}));$('applyFaceLabel').onclick=()=>task(()=>command({type:'metadata',face_ids:[selected],label:$('planeLabel').value}));
$('cutModel').onclick=()=>task(()=>command({type:'truncate',normal:tuple($('cutNormal').value),distance:+$('cutDistance').value}));
$('modelUndo').onclick=()=>{if(busy)return;adopt(history.undo(),{commit:false});status('已撤销模型操作。');};$('modelRedo').onclick=()=>{if(busy)return;adopt(history.redo(),{commit:false});status('已重做模型操作。');};
$('saveDraft').onclick=()=>task(()=>saveDocument('draft',result.draft));
$('exportModel').onclick=()=>task(async()=>{const r=await api('/api/editor-export',{draft:result.draft});$('exportLinks').innerHTML=`<a target="_blank" rel="noopener" href="/runs/${encodeURIComponent(r.run_id)}/index.html">打开离线预览 ↗</a><a href="/runs/${encodeURIComponent(r.run_id)}/result.zip" download>下载模型、参数和复现包</a>`;status('已生成新修订的离线结果，原输出未覆盖。');});
$('fitWindow').onclick=()=>{radius=C.framing(result.model);drawViews();};$('standardView').onclick=()=>{rotation=null;yaw=.52;pitch=.52;drawViews();};$('faceOn').onclick=()=>{const n=result.model.faces.find(f=>f.id===selected).n,up=Math.abs(n[2])>.9?[0,1,0]:[0,0,1],right=unit(vectorCross(up,n));rotation=[right,vectorCross(n,right),n];drawViews();};$('showBefore').onchange=drawViews;$('overlayOpacity').oninput=drawViews;
$('freeRotate').onchange=()=>{$('threeCaption').textContent=$('freeRotate').checked?'三维预览 · 拖动旋转':'三维预览 · 固定方向';};
$('useAxisPreset').onclick=()=>{try{const a=+$('axisA').value,b=+$('axisB').value,c=+$('axisC').value,beta=+$('axisBeta').value*Math.PI/180;let A;switch($('axesPreset').value){case'orthogonal':A=[[a,0,0],[0,b,0],[0,0,c]];$('axisCount').value=3;break;case'monoclinic':A=[[a,0,c*Math.cos(beta)],[0,b,0],[0,0,c*Math.sin(beta)]];$('axisCount').value=3;break;case'hexagonal':A=[[a,-a/2,0],[0,a*Math.sqrt(3)/2,0],[0,0,c]];$('axisCount').value=4;break;default:return;}$('axisBasis').value=A.map(r=>r.join(' ')).join('\n');}catch(e){status(e.message,true);}};
$('applyAxes').onclick=()=>task(()=>command(axisArgs('set_axes')));$('rebuildAxes').onclick=()=>task(()=>command(axisArgs('rebuild_axes')));
$('pickAxisPoints').onclick=()=>{$('startSection').open=false;workspaceNav?.activate('model');axisPicking='direction';axisPoints=[];$('axisPickStatus').textContent='依次点击起点和终点，方向为起点 → 终点。';status('在模型视图依次点选两个紫色顶点：起点 → 终点。');drawViews();};
$('axisOriginPoint').onclick=()=>{$('startSection').open=false;workspaceNav?.activate('model');axisPicking='origin';axisPoints=[];$('axisPickStatus').textContent='点击一个紫色顶点作为参考原点；外形保持不动。';status('在模型视图点击一个紫色顶点作为参考原点。');drawViews();};
$('axisFromFace').onclick=()=>{try{setDirection(result.model.faces.find(f=>f.id===selected).n);}catch(e){status(e.message,true);}};
$('analyzeModel').onclick=()=>task(async()=>{adopt(await api('/api/editor',{action:'analyze',draft:result.draft}),{commit:false});status('参数已按当前参考轴重新解析。');});
for(const [id] of views){
  const cv=$(id);let rotating=null;
  cv.onpointerdown=e=>{if(busy||!result)return;if(id==='threeView'&&$('freeRotate').checked&&!axisPicking){rotating={x:e.clientX,y:e.clientY,base:rotation||C.views.three};cv.setPointerCapture(e.pointerId);}};
  cv.onpointermove=e=>{if(rotating){rotation=C.rotateFrom(rotating.base,(e.clientX-rotating.x)/150,(e.clientY-rotating.y)/150);drawViews();}};
  cv.onpointerup=e=>{if(rotating){rotating=null;return;}if(busy||!result)return;const b=cv.getBoundingClientRect(),p=[e.clientX-b.left,e.clientY-b.top];
    if(axisPicking){const pts=rendered[id].vertices.map((q,i)=>({i,d:Math.hypot(q[0]-p[0],q[1]-p[1])})).sort((a,b)=>a.d-b.d);if(pts[0]?.d>20)return status('请点在紫色顶点附近。',true);const v=result.model.vertices[pts[0].i];if(axisPicking==='origin'){$('axisOrigin').value=v.map(String).join(' ');axisPicking=null;$('axisPickStatus').textContent='已填入参考原点，点击定义轴应用。';drawViews();workspaceNav?.activate('parameters');$('axesDisclosure').open=true;status('参考原点已填入；请点击定义轴应用。');return;}axisPoints.push(v);if(axisPoints.length===2){try{setDirection(axisPoints[1].map((x,i)=>x-axisPoints[0][i]));}catch(e){axisPoints=[];status(e.message,true);}}else{$('axisPickStatus').textContent='已选起点，请选方向终点。';status('已选起点，请再点一个紫色顶点作为方向终点。');}return;}
    selection(C.hitTest(rendered[id].hits,p));};
  cv.onpointercancel=()=>rotating=null;
}
function currentPhoto(){return photos[photoIndex];}
function photoAnnotation(){return currentPhoto()?.history.current;}
function updatePhotoList(){const previous=$('featureList').value,p=currentPhoto();$('featureList').innerHTML=(photoAnnotation()?.features||[]).map(f=>`<option value="${f.id}">${f.id} · ${{edge:'真实棱',silhouette:'外轮廓',face:'面区域',occlusion:'遮挡',uncertain:'不确定线'}[f.kind]} · ${f.points.length} 点${f.face_id?(f.model_fingerprint===result?.fingerprint?' · '+f.face_id:' · 面关联待核对'):''}</option>`).join('');$('photoInfo').textContent=p?`${p.size.join(' × ')} 原图像素 · ${photoAnnotation().features.length} 项标注 · 拖动端点后自动保存为可撤销步骤`:'尚未选择照片';if(photoAnnotation()?.features.some(f=>f.id===previous))$('featureList').value=previous;refreshSnapTargets();updateButtons();}
const colors={edge:'#ed933b',silhouette:'#27a575',face:'#407fed',occlusion:'#707b81',uncertain:'#a169c5'};
function drawPhoto(){const cv=$('correctionCanvas');if(!visibleCanvas($('photoEditor')))return;const p=currentPhoto(),base=cv.parentElement.clientWidth,stageHeight=cv.parentElement.clientHeight;cv.style.width=base*photoZoom+'px';cv.style.height=Math.max(280,stageHeight)*photoZoom+'px';const b=cv.getBoundingClientRect(),dpr=devicePixelRatio||1;cv.width=b.width*dpr;cv.height=b.height*dpr;const ctx=cv.getContext('2d');ctx.scale(dpr,dpr);ctx.fillStyle='#e9eee4';ctx.fillRect(0,0,b.width,b.height);if(!p){ctx.fillStyle='#597263';ctx.font='15px system-ui';ctx.fillText('选择照片，在图上标出棱、轮廓或面',25,50);return;}
  const {s,x,y}=X.photoFrame(p.size,[b.width,b.height],p.focusBounds);photoTransform={s,x,y};refreshHover();ctx.drawImage(p.image,x,y,p.size[0]*s,p.size[1]*s);
  const ann=drag?.annotation||photoAnnotation();
  function drawFeature(f,inProgress=false){const points=f.points.map(p=>[x+p[0]*s,y+p[1]*s]),closed=['face','silhouette','occlusion'].includes(f.kind);ctx.strokeStyle=colors[f.kind]||'#ed933b';ctx.lineWidth=f.id===$('featureList').value?3:2;ctx.setLineDash(f.kind==='uncertain'?[5,4]:[]);ctx.beginPath();points.forEach((p,i)=>i?ctx.lineTo(...p):ctx.moveTo(...p));if(closed&&!inProgress)ctx.closePath();if(closed&&!inProgress){ctx.fillStyle=(colors[f.kind]||'#aaa')+'22';ctx.fill();}ctx.stroke();ctx.setLineDash([]);points.forEach((p,i)=>{ctx.beginPath();ctx.arc(...p,5,0,Math.PI*2);ctx.fillStyle=colors[f.kind]||'#ed933b';ctx.fill();ctx.strokeStyle='#fff';ctx.lineWidth=1.5;ctx.stroke();if(i===0){ctx.font='bold 12px system-ui';ctx.fillText(f.id||'正在画',p[0]+8,p[1]-8);}});}
  if(prefs.showGuides&&prefs.imageCorners)for(const g of p.guides?.corners||[]){ctx.beginPath();ctx.arc(x+g.point[0]*s,y+g.point[1]*s,3.5,0,Math.PI*2);ctx.strokeStyle=g.priority==='secondary'?'#9a7b9799':'#9a6425aa';ctx.lineWidth=1;ctx.stroke();}
  drawCorrectionLayers(ctx,p,{s,x,y});
  ann.features.forEach(f=>{ctx.save();if(f.id===redrawId)ctx.globalAlpha=.28;drawFeature(f);ctx.restore();});if(workingPoints.length)drawFeature({kind:$('featureKind').value,points:workingPoints},true);
  drawPointerHelp(ctx,p,{s,x,y},b.width,b.height);
}
async function loadPhotos(files){if(!files.length)return;if(files.length>24||[...files].reduce((n,f)=>n+f.size,0)>64*1024*1024)throw Error('最多24张照片，总计不超过64MiB');const epoch=++photoEpoch,loaded=[];for(const file of files){if(file.size>16*1024*1024)throw Error('单张照片不能超过16MiB');const bytes=await file.arrayBuffer(),hash=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(x=>x.toString(16).padStart(2,'0')).join(''),url=await new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result);r.onerror=reject;r.readAsDataURL(file);}),image=await new Promise((resolve,reject)=>{const i=new Image();i.onload=()=>resolve(i);i.onerror=()=>reject(Error('无法读取这张照片'));i.src=url;});const size=[image.naturalWidth,image.naturalHeight];loaded.push({image,url,size,hash,history:new S.History(S.annotation(size,hash))});}if(epoch!==photoEpoch)return;photos=loaded;photoIndex=0;workingPoints=[];workingRedo=[];redrawId=null;faceSeedMode=false;drag=null;lastPointer=null;hoverSnap=null;photoZoom=1;packet=null;review=null;$('reviewStatus').textContent='照片已更换，请重新生成复核包。';$('correctionPhoto').innerHTML=photos.map((p,i)=>`<option value="${i}">照片 ${i+1} · ${p.size.join('×')}</option>`).join('');$('correctedCandidates').replaceChildren();updatePhotoList();drawPhoto();ensurePhotoGuides();status('照片已载入本机。选择“真实棱”或“面区域”，在图中开始标记。');}
$('correctionPhotos').onchange=e=>task(()=>loadPhotos(e.target.files));
$('correctionDemo').onclick=()=>task(async()=>{const d=await (await fetch('/api/demo')).json();const blob=await (await fetch(d.image)).blob();await loadPhotos([new File([blob],'synthetic-demo.png',{type:'image/png'})]);adopt(await api('/api/editor',{action:'import',spec:d.spec}),{reset:true});status('已载入合成模型与照片，供练习拉线、圈面；不是实物识别验证。');});
$('realPhotoDemo').onclick=()=>task(async()=>{const d=await (await fetch('/api/real-demo')).json();const blob=await (await fetch(d.image)).blob();await loadPhotos([new File([blob],'451-public-reference.jpg',{type:'image/jpeg'})]);adopt(await api('/api/editor',{action:'import',spec:d.spec}),{reset:true});currentPhoto().history.commit(d.annotation);updatePhotoList();focusPhotoObject();status(d.notice+' 可直接拖线修正或点选识别面。');});
$('correctionPhoto').onchange=e=>{photoIndex=+e.target.value;workingPoints=[];workingRedo=[];redrawId=null;faceSeedMode=false;drag=null;lastPointer=null;hoverSnap=null;photoZoom=1;updatePhotoList();drawPhoto();ensurePhotoGuides();};
$('featureKind').onchange=()=>setDrawingTool($('featureKind').value);$('featureList').onchange=drawPhoto;
const cv=$('correctionCanvas');
function eventPixel(e){const b=cv.getBoundingClientRect();return S.pixelPoint([e.clientX-b.left,e.clientY-b.top],photoTransform,currentPhoto().size);}
cv.onpointerdown=e=>{
  if(busy||!currentPhoto())return;const raw=eventPixel(e);if(!raw)return;cv.focus({preventScroll:true});lastPointer={raw,shift:e.shiftKey};
  if(faceSeedMode){currentPhoto().faceSeed=[...raw];faceSeedMode=false;task(()=>recognizeFace(raw));return;}
  if($('featureKind').value==='edit'){
    const a=photoAnnotation(),hit=S.hitFeature(a,raw,{scale:photoTransform.s,radius:12});
    if(!hit)return status('点选圆点、线段或面内部后拖动；新增标注请用上方绘图工具。');
    $('featureList').value=hit.featureId;
    try{
      if($('editAction').value==='insert'){
        if(hit.type!=='segment')return status('加节点：请点在线段中间，避开已有端点。');
        commitCorrection(S.insertPoint(a,hit.featureId,hit.segmentIndex,hit.point));return;
      }
      if($('editAction').value==='remove'){
        if(hit.type!=='point')return status('删除节点：请点在已有圆点上。');
        commitCorrection(S.removePoint(a,hit.featureId,hit.pointIndex));return;
      }
      const f=a.features.find(f=>f.id===hit.featureId);
      drag={id:hit.featureId,index:hit.pointIndex,segmentIndex:hit.segmentIndex,
        type:hit.type==='point'?'point':hit.type==='segment'&&['face','silhouette','occlusion'].includes(f.kind)?'segment':'feature',
        start:raw,annotation:a,base:a,photo:currentPhoto(),epoch:photoEpoch,linked:$('linkedPoints').checked};
      cv.setPointerCapture(e.pointerId);
    }catch(error){status(error.message,true);}
  }else{const picked=resolveSnap(raw,e.shiftKey);hoverSnap=picked;if(picked.target?.kind==='start'){finishFeature();return;}placeDrawingPoint(picked.point);}
  drawPhoto();
};
cv.onpointermove=e=>{
  if(busy||!currentPhoto())return;const raw=eventPixel(e);if(!raw){lastPointer=null;hoverSnap=null;drawPhoto();return;}
  lastPointer={raw,shift:e.shiftKey};hoverSnap=resolveSnap(raw,e.shiftKey);
  if(drag){try{
    const delta=raw.map((v,i)=>v-drag.start[i]),options={linked:drag.linked};
    drag.annotation=drag.type==='point'?S.movePoint(drag.base,drag.id,drag.index,hoverSnap.point,options):drag.type==='segment'?S.translateSegment(drag.base,drag.id,drag.segmentIndex,delta,options):S.translateFeature(drag.base,drag.id,delta,options);
  }catch(error){status(error.message+'；保留最后有效位置。',true);}}
  updateSnapFeedback();drawPhoto();
};
cv.onpointerup=()=>{if(busy||drag?.photo!==currentPhoto()||drag?.epoch!==photoEpoch){drag=null;return;}if(drag){currentPhoto().history.commit(drag.annotation);drag=null;updatePhotoList();drawPhoto();invalidateReview();}};
cv.onpointercancel=()=>{drag=null;lastPointer=null;hoverSnap=null;drawPhoto();};
cv.onpointerleave=()=>{if(!drag){lastPointer=null;hoverSnap=null;updateSnapFeedback();drawPhoto();}};

function invalidateReview(){const p=currentPhoto();if(p){p.faceProposal=null;p.alignment=null;}faceSeedMode=false;invalidateRecognition();review=null;$('applySuggestions').disabled=true;if(packet)$('reviewStatus').textContent='标注已改变，请重新生成复核包。';packet=null;updateCorrectionControls();drawPhoto();}
function invalidateRecognition(){ $('correctedCandidates').replaceChildren();$('recognitionStatus').textContent=photos.length?'输入已改变，请重新识别候选。':'';}
$('photoMorphology').oninput=invalidateRecognition;
function finishFeature(){try{
  if(!currentPhoto())throw Error('请先选择照片');if($('featureKind').value==='edit')return;
  let a=photoAnnotation();const kind=$('featureKind').value;
  if(redrawId)a=S.replaceFeaturePoints(a,redrawId,workingPoints);
  else{
    if(kind==='silhouette'&&a.features.some(f=>f.kind==='silhouette'))throw Error('已有外轮廓；选中它后点“重画所选标注”即可替换。');
    a=S.addFeature(a,kind,workingPoints);if($('annotationFace').value)a=S.updateFeature(a,a.features[a.features.length-1].id,{face_id:$('annotationFace').value,model_fingerprint:result.fingerprint});
  }
  currentPhoto().history.commit(a);workingPoints=[];workingRedo=[];redrawId=null;lastPointer=null;hoverSnap=null;$('featureKind').value='edit';$('featureKind').dataset.previous='edit';updatePhotoList();invalidateReview();status('修正已保存，可继续拖点、拉线或重新识别面。');
}catch(e){status(e.message,true);}}
$('finishFeature').onclick=finishFeature;$('cancelFeature').onclick=cancelDrawing;
$('reclassifyFeature').onclick=()=>{try{if(!currentPhoto())return;currentPhoto().history.commit(S.updateFeature(photoAnnotation(),$('featureList').value,{kind:$('featureKind').value}));updatePhotoList();drawPhoto();invalidateReview();}catch(e){status(e.message,true);}};
$('rebindFeature').onclick=()=>{try{if(!currentPhoto())return;currentPhoto().history.commit(S.updateFeature(photoAnnotation(),$('featureList').value,{face_id:$('annotationFace').value,model_fingerprint:result.fingerprint}));updatePhotoList();drawPhoto();invalidateReview();status('面关联已按当前模型重新确认。');}catch(e){status(e.message,true);}};
$('deleteFeature').onclick=()=>{if(!currentPhoto())return;currentPhoto().history.commit(S.removeFeature(photoAnnotation(),$('featureList').value));updatePhotoList();drawPhoto();invalidateReview();};
$('photoUndo').onclick=()=>{currentPhoto()?.history.undo();workingPoints=[];workingRedo=[];updatePhotoList();drawPhoto();invalidateReview();};$('photoRedo').onclick=()=>{currentPhoto()?.history.redo();updatePhotoList();drawPhoto();invalidateReview();};
$('photoZoomIn').onclick=()=>{photoZoom=Math.min(4,photoZoom*1.3);drawPhoto();};$('photoZoomOut').onclick=()=>{photoZoom=Math.max(.5,photoZoom/1.3);drawPhoto();};$('photoFit').onclick=()=>{photoZoom=1;if(currentPhoto())currentPhoto().focusBounds=null;drawPhoto();};$('focusObject').onclick=()=>{try{focusPhotoObject();}catch(e){status(e.message,true);}};$('focusDrawing').onclick=()=>{document.querySelector('.photo-canvas-wrap').scrollIntoView({block:'center',behavior:'instant'});cv.focus({preventScroll:true});};
$('saveAnnotations').onclick=()=>task(async()=>{const action=X.saveAction('photo',workingPoints.length,photos.length);if(action.reason)throw Error(action.reason);return saveDocument('annotations',{schema_version:1,annotations:photos.map(p=>p.history.current)});});
$('openAnnotations').onchange=e=>task(async()=>{const file=e.target.files[0];if(!file)return;if(!photos.length)throw Error('先载入对应原图，再打开纠错文件');const data=JSON.parse(await file.text()),list=data.annotations||[data];const validated=[],matches=S.matchAnnotations(photos.map(p=>p.hash),list);for(const [index,p] of photos.entries()){const a=matches[index];if(!a){validated.push(null);continue;}validated.push(await api('/api/photo-annotations',{image:p.url,annotation:a}));}if(!validated.some(Boolean))throw Error('纠错文件不属于当前照片');validated.forEach((v,i)=>{if(v){photos[i].history.commit(v.annotation||v);photos[i].alignment=null;photos[i].faceProposal=null;photos[i].faceMessage='纠错已重新载入，可重新识别或对齐。';}});workingPoints=[];workingRedo=[];redrawId=null;faceSeedMode=false;lastPointer=null;hoverSnap=null;updatePhotoList();drawPhoto();invalidateReview();status('已核对图片指纹与尺寸并载入纠错。');e.target.value='';});
$('refineCandidates').onclick=()=>task(async()=>{if(!photos.length)throw Error('请先选择照片');if(workingPoints.length)throw Error('先完成或取消正在画的线');$('recognitionStatus').textContent='在本机提取图像，加入手工修正并比较候选…';const r=await api('/api/from-photos',{images:photos.map(p=>p.url),evidence:{morphology:$('photoMorphology').value,annotations:photos.map(p=>p.history.current.features.length?p.history.current:null)}});$('recognitionStatus').textContent=`${r.performance.photos}张照片 · ${r.fusion.independent_views}组视角。手工辅助结果与自动识别精度分开看。`;$('correctedCandidates').innerHTML=r.candidates.map((c,i)=>`<article><h3>候选 ${i+1} · ${esc(c.template_id)}</h3><p>${esc(c.title)}</p><p>比较得分 ${number(c.score)}（不是置信度）</p><button data-load="${i}">载入继续手动调整</button><a target="_blank" rel="noopener" href="/runs/${encodeURIComponent(c.artifact.run_id)}/index.html">照片与模型对照 ↗</a></article>`).join('');$('correctedCandidates').querySelectorAll('button').forEach(b=>b.onclick=()=>task(async()=>{adopt(await api('/api/editor',{action:'import',spec:r.candidates[+b.dataset.load].spec}),{reset:true});status('修正后的候选已载入，仍需检查深度、不可见面及编号。');}));status((r.warnings||[]).slice(0,2).join(' ')||'已完成本机候选比较。');});
$('exportReview').onclick=()=>task(async()=>{if(workingPoints.length)throw Error('请先完成正在画的线');packet=await api('/api/review-export',{draft:result.draft,annotations:photos.map(p=>p.history.current)});review=null;await saveDocument('review',packet);$('reviewStatus').textContent='复核包已生成，不含原始照片。可同时下载提示词，待助手返回 JSON 后导入。';status('已生成本地复核包；没有自动上传。');});
$('downloadPrompt').onclick=()=>task(async()=>{if(packet)await saveDocument('prompt',packet.prompt);});
$('reviewResponse').onchange=e=>task(async()=>{const file=e.target.files[0];if(!file)return;if(!packet)throw Error('先为当前模型生成复核包');const response=JSON.parse(await file.text()),checked=await api('/api/review-check',{packet,response,current_fingerprint:result.fingerprint});review={response,checked};$('reviewSuggestions').innerHTML=checked.suggestions.map(s=>`<article><label><input type="checkbox" value="${esc(s.id)}"> ${esc(s.id)} · ${esc(s.reason)}</label><p class="hint">${esc(JSON.stringify(s.command))}</p><p>${esc(s.evidence.map(e=>e.detail).join('；'))}</p></article>`).join('')+`<p>仍不确定：${esc((checked.uncertain||[]).join('；')||'回复未列出')}</p>`;$('reviewStatus').textContent='模型、策略和面 ID 已核对。请勾选要采纳的建议；不会自动采纳。';e.target.value='';});
$('applySuggestions').onclick=()=>task(async()=>{const ids=[...$('reviewSuggestions').querySelectorAll('input:checked')].map(e=>e.value);if(!ids.length)throw Error('请先勾选至少一项建议');const checked=await api('/api/review-check',{packet,response:review.response,current_fingerprint:result.fingerprint,selected_ids:ids});let next=result;for(const c of checked.selected_commands)next=await api('/api/editor',{action:'apply',draft:next.draft,command:c});adopt(next);packet=null;status('所选建议全部通过本地重算，已作为一步可撤销修订采纳。');});
function focusPhotoObject(){const p=currentPhoto();if(!p)throw Error('先选择照片');const points=p.history.current.features.find(f=>f.kind==='silhouette')?.points||p.guides?.corners.filter(c=>c.source==='outline').map(c=>c.point);if(!points||points.length<3)throw Error('先画外轮廓，或采用并核对照片轮廓后再聚焦');p.focusBounds=[Math.min(...points.map(x=>x[0])),Math.min(...points.map(x=>x[1])),Math.max(...points.map(x=>x[0])),Math.max(...points.map(x=>x[1]))];photoZoom=1;lastPointer=null;hoverSnap=null;drawPhoto();}
function commitCorrection(annotation,message='修正已保存；可以撤销，或重新对齐当前模型。',p=currentPhoto()){
  if(!p||p!==currentPhoto())throw Error('照片已切换，不能采纳上一张图的结果');S.assertPhotoBinding(annotation,p.hash,p.size);p.history.commit(annotation);p.faceMessage='标注已改变，可重新点选识别面。';updatePhotoList();invalidateReview();status(message);
}
function updateCorrectionControls(){
  const p=currentPhoto();if(p?.faceProposal&&p.faceProposal.snapshot!==JSON.stringify(p.history.current))p.faceProposal=null;if(p?.alignment&&(p.alignment.snapshot!==JSON.stringify(p.history.current)||p.alignment.modelFingerprint!==result?.fingerprint||p.alignment.data.source_sha256!==p.hash))p.alignment=null;const proposal=p?.faceProposal,aligned=p?.alignment;
  $('detectFace').disabled=!p||workingPoints.length>0;$('detectFace').setAttribute('aria-pressed',String(faceSeedMode));
  $('retryFace').disabled=!p?.faceSeed||workingPoints.length>0;
  $('faceProposalActions').hidden=!proposal?.data.polygon.length;
  $('faceProposalStatus').textContent=p?.faceMessage||'点击面内均匀区域；文字或阴影干扰时，先补棱线再识别。';
  $('alignCurrent').disabled=!p||!result||workingPoints.length>0;$('showModelOverlay').disabled=!aligned;
  $('adoptOutline').disabled=!p?.guides?.segments.some(line=>line.source==='outline');
  if(!aligned){$('showModelOverlay').checked=false;$('faceMatchResults').replaceChildren();$('alignmentStatus').textContent='当前没有有效对齐；修改模型、标注或换图后请重新计算。';}else renderAlignmentDetails(p);
}
function drawCorrectionLayers(ctx,p,t){
  const project=point=>[t.x+point[0]*t.s,t.y+point[1]*t.s];
  const path=points=>{ctx.beginPath();points.forEach((point,i)=>i?ctx.lineTo(...project(point)):ctx.moveTo(...project(point)));};
  if($('showImageLines').checked){ctx.save();ctx.setLineDash([3,4]);ctx.lineWidth=1;ctx.strokeStyle='#b48642aa';for(const line of p.guides?.segments||[]){path(line.points);ctx.stroke();}ctx.restore();}
  if(p.alignment&&$('showModelOverlay').checked){ctx.save();ctx.strokeStyle='#a034ba';ctx.lineWidth=1.7;for(const edge of p.alignment.data.projected_edges){path(edge.points);ctx.stroke();}ctx.fillStyle='#79288b';ctx.font='bold 11px system-ui';for(const match of p.alignment.data.metrics.face_matches||[]){if(!match.projected_polygon)continue;const poly=match.projected_polygon;if(match.feature_id===$('featureList').value){path(poly);ctx.closePath();ctx.fillStyle='#c780db22';ctx.fill();ctx.fillStyle='#79288b';}const center=[0,1].map(i=>poly.reduce((n,p)=>n+p[i],0)/poly.length);const q=project(center);ctx.fillText(match.model_face_id+' · 待核对',q[0],q[1]);}ctx.restore();}
  const candidate=p.faceProposal?.data.polygon;if(candidate?.length){ctx.save();path(candidate);ctx.closePath();ctx.fillStyle='#18b7c343';ctx.fill();ctx.strokeStyle='#037d88';ctx.setLineDash([6,4]);ctx.lineWidth=2.5;ctx.stroke();ctx.restore();}
}
async function recognizeFace(seed){
  const p=currentPhoto();if(!p)throw Error('先选择照片');if(workingPoints.length)throw Error('先完成或取消正在画的线');
  const epoch=photoEpoch,annotation=p.history.current,snapshot=JSON.stringify(annotation);p.faceSeed=[...seed];p.faceProposal=null;p.faceMessage='正在本机分析面边界…';updateCorrectionControls();drawPhoto();
  const r=await api('/api/photo-face',{image:p.url,annotation,seed,tolerance:+$('faceTolerance').value});
  if(epoch!==photoEpoch||p!==currentPhoto()||snapshot!==JSON.stringify(p.history.current))return;
  if(r.source_sha256!==p.hash||JSON.stringify(r.image_size)!==JSON.stringify(p.size))throw Error('候选面与当前照片不匹配');
  if(r.polygon?.length){p.faceProposal={data:r,snapshot};p.faceMessage=`找到 ${r.polygon.length} 个边界节点 · ${r.method==='manual_enclosure'?'由手工棱线围成':'颜色 / 梯度辅助'}。先看青色区域是否正确，再采用。`;}
  else p.faceMessage='尚未找到可靠闭合面。'+(r.warnings||[]).slice(-2).join(' ');
  updateCorrectionControls();drawPhoto();status(r.polygon?.length?'面候选已预览，尚未写入标注。':'请补齐分界棱线、调整颜色范围，或手动圈面。');
}
function applyFaceProposal(){
  try{const p=currentPhoto(),proposal=p?.faceProposal;if(!proposal)throw Error('先点选一个候选面');
    if(proposal.snapshot!==JSON.stringify(p.history.current)||proposal.data.source_sha256!==p.hash)throw Error('标注或照片已改变，请重新识别这个面');
    let a=S.addFeature(p.history.current,'face',proposal.data.polygon);const feature=a.features[a.features.length-1];feature.evidence=(proposal.data.evidence+'；用户采纳为待核对面区域').slice(0,2000);
    if($('annotationFace').value)a=S.updateFeature(a,feature.id,{face_id:$('annotationFace').value,model_fingerprint:result.fingerprint});
    setDrawingTool('edit');commitCorrection(a,'已采用为 '+feature.id+'；现在可以拖点、拉边、加减节点继续修正。');$('featureList').value=feature.id;drawPhoto();
  }catch(e){status(e.message,true);}
}
function renderAlignmentDetails(p){
  const r=p.alignment.data;
  $('alignmentStatus').textContent=`已使用 ${r.metrics.manual_edges_used||0} 段手工棱、${r.metrics.manual_faces_used||0} 个面区域；轮廓拟合残差 ${number(r.view.rmse)} px。紫色是模型线框，橙/蓝是你的标注；外形没有改变。`;
  $('faceMatchResults').innerHTML=(r.metrics.face_matches||[]).map((m,i)=>`<article><strong>${esc(m.feature_id)} → ${esc(m.model_face_id||'暂不能对应')}</strong><p class="hint">${m.boundary_rmse_pixels===null||m.boundary_rmse_pixels===undefined?'':`面边界拟合残差 ${number(m.boundary_rmse_pixels)} px。 `}${esc(m.reason||'几何候选对应，仍需核对。')}${m.ambiguity?' 存在接近的其他解释。':''}</p>${m.model_face_id?`<button data-confirm-match="${i}">确认这个面对应</button>`:''}</article>`).join('')+`<p><a href="${esc(r.record_url)}" target="_blank" rel="noopener">本次对齐记录</a></p><p class="hint">F编号属于当前参考模型，不是照片上的数字；对称外形可能存在多个对应。这些标注参与了拟合，误差不是独立精度。若外形仍不符，请调整模型后重新对齐。</p>`;
  $('faceMatchResults').querySelectorAll('[data-confirm-match]').forEach(button=>button.onclick=()=>{
    try{if(p!==currentPhoto()||!p.alignment||p.alignment.data!==r||r.source_sha256!==p.hash||p.alignment.modelFingerprint!==result.fingerprint||p.alignment.snapshot!==JSON.stringify(p.history.current))throw Error('对齐已过期，请重新计算');const match=r.metrics.face_matches[+button.dataset.confirmMatch];const a=S.updateFeature(p.history.current,match.feature_id,{face_id:match.model_face_id,model_fingerprint:result.fingerprint});commitCorrection(a,'面对应已按你的确认记录；重新对齐可将它作为约束使用。',p);}catch(e){status(e.message,true);}
  });
}
async function alignCurrentPhoto(){
  const p=currentPhoto();if(!p||!result)throw Error('先选择照片并载入当前模型');if(workingPoints.length)throw Error('先完成正在绘制的标注');
  const epoch=photoEpoch,modelFingerprint=result.fingerprint,snapshot=JSON.stringify(p.history.current);p.alignment=null;updateCorrectionControls();drawPhoto();$('alignmentStatus').textContent='正在用轮廓、棱线和面边界拟合当前模型的相机…';
  const r=await api('/api/photo-align',{draft:result.draft,expected_fingerprint:modelFingerprint,image:p.url,annotation:p.history.current});
  if(p!==currentPhoto()||epoch!==photoEpoch||modelFingerprint!==result.fingerprint||snapshot!==JSON.stringify(p.history.current))return;
  if(r.source_sha256!==p.hash||r.model_fingerprint!==result.fingerprint)throw Error('对齐结果不属于当前照片与模型');
  p.alignment={data:r,snapshot,modelFingerprint};$('showModelOverlay').checked=true;updateCorrectionControls();

  drawPhoto();status('当前模型已对齐。请在实物照片上核对紫色棱线和每个面。');
}
$('editAction').onchange=()=>{if(workingPoints.length)return status('先完成或取消正在画的标注');setDrawingTool('edit');$('correctionTools').open=false;};
$('redrawFeature').onclick=()=>{
  if(workingPoints.length)return status('先完成或取消正在绘制的标注。',true);
  const f=photoAnnotation()?.features.find(f=>f.id===$('featureList').value);if(!f)return status('先在列表或图中选中要重画的标注。',true);
  setDrawingTool(f.kind);redrawId=f.id;$('correctionTools').open=false;workingPoints=[];workingRedo=[];updateDrawingControls();drawPhoto();status('正在重画 '+f.id+'；完成后替换边界，取消会保留原标注。');
};
$('detectFace').onclick=()=>{if(!currentPhoto())return status('先选择照片');if(workingPoints.length)return status('先完成或取消正在画的线');faceSeedMode=!faceSeedMode;redrawId=null;updateDrawingControls();status(faceSeedMode?'请在照片中点击目标面的内部，尽量避开编号和强阴影。':'已退出点选识别面。');};
$('retryFace').onclick=()=>task(()=>recognizeFace(currentPhoto().faceSeed));
$('faceTolerance').onchange=()=>{const p=currentPhoto();if(p){p.faceProposal=null;p.faceMessage='颜色范围已改变，可按当前范围重试或重新点选面内位置。';updateCorrectionControls();drawPhoto();}};
$('acceptFace').onclick=applyFaceProposal;$('rejectFace').onclick=()=>{const p=currentPhoto();if(p){p.faceProposal=null;p.faceMessage='候选已放弃；可以补线后再识别，或手动圈面。';updateCorrectionControls();drawPhoto();}};
$('alignCurrent').onclick=()=>task(alignCurrentPhoto);$('showModelOverlay').onchange=drawPhoto;$('showImageLines').onchange=drawPhoto;
$('adoptOutline').onclick=()=>{
  try{const p=currentPhoto(),lines=p?.guides?.segments.filter(line=>line.source==='outline');if(!lines?.length)throw Error('没有可靠轮廓建议，请手工画外轮廓');if(workingPoints.length)throw Error('先完成正在绘制的线');
    const points=lines.map(line=>line.points[0]);let a=p.history.current;const existing=a.features.find(f=>f.kind==='silhouette');
    if(existing)a=S.replaceFeaturePoints(a,existing.id,points);else a=S.addFeature(a,'silhouette',points);
    const feature=a.features.find(f=>f.kind==='silhouette');feature.evidence='本机图像轮廓建议经用户采用，边界仍需人工核对；原图SHA256='+p.hash;
    setDrawingTool('edit');commitCorrection(a,'照片轮廓已载入，可拖点修边。补画内部棱线后，再点选识别各个面。');$('featureList').value=feature.id;drawPhoto();
  }catch(e){status(e.message,true);}
};

function persistPreferences(){try{localStorage.setItem('mineral-atlas-editor-preferences',JSON.stringify(prefs));}catch(e){status('本次设置已生效，浏览器未能记住偏好。');}}
function applyAudience(){
  document.body.dataset.audience=prefs.audience;$('audienceMode').value=prefs.audience;
  $('audienceHint').textContent={beginner:'先练习选点、画棱线和圈面；不需要先懂三维软件。',student:'把照片观察、参考晶轴和指数候选逐项对应，注意模型参数与实物证据的区别。',teacher:'先让学生观察面、棱和方向，再展示参考指数；切回学习模式可继续完整编辑。'}[prefs.audience];
  $('learningTip').innerHTML={beginner:'<strong>第一次使用？</strong> 到“标照片”点击“试画合成示例”，先画一条棱，再圈一个面。全部操作都可撤销。',student:'<strong>学习顺序：</strong> 观察外形 → 标棱和面 → 定义参考轴 → 查看指数候选。更换轴时先保持实体外形不动。',teacher:'<strong>课堂演示：</strong> 可用“显示视图”放大单个视图；先关闭面号与指数，再逐步揭示。当前显示只改变呈现，不修改模型。'}[prefs.audience];
  $('axesDisclosure').open=prefs.audience==='student';$('faceResultsDisclosure').open=prefs.audience==='student';
  $('teachingHint').hidden=prefs.audience!=='teacher';updatePresentation();refreshLayoutSummary();
}
function updatePresentation(){
  const focus=$('viewFocus').value;document.querySelector('.views').classList.toggle('single-view',focus!=='all');
  for(const [id,view] of views)$(id).closest('figure').hidden=focus!=='all'&&view!==focus;
  document.body.classList.toggle('show-reference',$('showReferenceIndices').checked);
  drawViews();
}
function refreshSnapTargets(){
  const annotation=photoAnnotation()||{features:[]};
  snapTargets=Snap.proposeTargets(annotation,workingPoints,currentPhoto()?.guides?.corners||[],{
    includeStart:['face','silhouette','occlusion'].includes($('featureKind').value),includeMidpoints:prefs.midpoints,
    includeIntersections:prefs.intersections,includeImageCorners:prefs.imageCorners
  });
  refreshHover();
}
function resolveSnap(raw,bypass=false){
  const moving=drag?(drag.type==='point'?[drag.base.features.find(f=>f.id===drag.id).points[drag.index]]:drag.base.features.find(f=>f.id===drag.id).points):[];const targets=drag?snapTargets.filter(t=>t.featureId!==drag.id&&!moving.some(p=>Math.hypot(p[0]-t.point[0],p[1]-t.point[1])<=.05)):snapTargets;
  return Snap.pickSnap(raw,targets,{enabled:prefs.snap,bypass:bypass||shiftHeld,scale:photoTransform?.s||1,radius:prefs.radius});
}
function refreshHover(){if(lastPointer)hoverSnap=resolveSnap(lastPointer.raw,lastPointer.shift);else hoverSnap=null;updateSnapFeedback();}
function updateSnapFeedback(){
  let message=!prefs.snap?'自动拾取已关闭 · 自由落点':shiftHeld||lastPointer?.shift?'Shift：临时自由落点':hoverSnap?.target?`已拾取：${hoverSnap.target.label}`:`自动拾取开启 · 范围 ${prefs.radius} 屏幕像素`;
  if(snapTargets.meta?.truncated)message+=' · 复杂标注仅显示部分交点';
  if($('snapFeedback').textContent!==message)$('snapFeedback').textContent=message;
  $('pointerCoordinates').textContent=hoverSnap?`原图 ${hoverSnap.point.map(v=>v.toFixed(1)).join(', ')}`:'';
  $('correctionCanvas').dataset.snapKind=hoverSnap?.target?.kind||'none';
}
function updateDrawingControls(){
  const hint=X.drawingHint($('featureKind').value,workingPoints.length,!!currentPhoto());
  const editHelp=$('featureKind').value==='edit'&&$('editAction').value!=='move'?($('editAction').value==='insert'?'加节点模式：点击线段中间，避开已有端点。':'删节点模式：点击要删除的圆点；线至少保留2点、面至少3点。'):hint.text;const help=faceSeedMode?'请点击目标面的内部均匀区域；先补画分界棱线可避免跨面。':redrawId?`正在重画 ${redrawId}。${hint.text}`:editHelp;if($('drawingHelp').textContent!==help)$('drawingHelp').textContent=help;
  $('finishFeature').disabled=!hint.canFinish;$('backPoint').disabled=!workingPoints.length;$('cancelFeature').disabled=!(workingPoints.length||redrawId||faceSeedMode);
  document.querySelectorAll('[data-draw-tool]').forEach(b=>b.setAttribute('aria-pressed',String(!faceSeedMode&&b.dataset.drawTool===$('featureKind').value)));
  $('pointX').max=currentPhoto()?.size[0]||0;$('pointY').max=currentPhoto()?.size[1]||0;
  const p=currentPhoto();$('guideStatus').textContent=!prefs.imageCorners?'照片候选角点已关闭，仍可拾取手工标注的点。':!p?'选照片后在本机寻找候选角点。':p.guidesLoading?'正在本机寻找角点；可以继续手动绘图。':p.guideError?`${p.guideError}；仍可拾取已标记的端点。`:p.guides?`已找到 ${p.guides.corners.length} 个候选角点。${(p.guides.warnings||[]).join(' ')}`:'照片角点只作落点建议，不自动认定晶棱。';
  $('refreshPhotoGuides').disabled=!p||p.guidesLoading;
  updateSnapFeedback();updateCorrectionControls();
}
async function ensurePhotoGuides(force=false){
  const p=currentPhoto(),epoch=photoEpoch;if(!p||!prefs.imageCorners||p.guidesLoading||(!force&&(p.guides||p.guideError)))return;
  p.guidesLoading=true;updateDrawingControls();
  try{const r=await api('/api/photo-guides',{image:p.url});if(epoch!==photoEpoch||!photos.includes(p))return;
    if(r.source_sha256!==p.hash||JSON.stringify(r.image_size)!==JSON.stringify(p.size))throw Error('角点建议与当前图片不匹配');
    p.guides=r;p.guideError=null;
  }catch(e){if(epoch===photoEpoch&&photos.includes(p))p.guideError=e.message;}
  finally{p.guidesLoading=false;if(epoch===photoEpoch&&p===currentPhoto()){refreshSnapTargets();updateDrawingControls();drawPhoto();}}
}
function setDrawingTool(kind){
  if(busy)return;
  if(kind===$('featureKind').dataset.previous&&!faceSeedMode){$('featureKind').value=kind;updateDrawingControls();return;}
  if(workingPoints.length&&kind!==$('featureKind').dataset.previous){status('先完成或取消正在绘制的标注，再切换工具。',true);$('featureKind').value=$('featureKind').dataset.previous||'edge';return;}
  $('featureKind').value=kind;$('featureKind').dataset.previous=kind;faceSeedMode=false;redrawId=null;lastPointer=null;hoverSnap=null;drag=null;refreshSnapTargets();updateDrawingControls();drawPhoto();
}
function placeDrawingPoint(point){
  if(!currentPhoto())return status('先选择照片或载入合成练习。',true);
  if($('featureKind').value==='edit')return status('先选择“画棱线”“圈面”或“画轮廓”，再放点。',true);
  if(point.some((v,i)=>!Number.isFinite(v)||v<0||v>currentPhoto().size[i]))return status('坐标必须在原图范围内。',true);
  if(workingPoints.some(p=>Math.hypot(p[0]-point[0],p[1]-point[1])<.05))return status('这个点已经放过；圈面时完成即可，无需重复首点。',true);
  workingPoints.push([...point]);workingRedo=[];refreshSnapTargets();updateDrawingControls();drawPhoto();
}
function backDrawingPoint(){if(!workingPoints.length)return;workingRedo.push(workingPoints.pop());lastPointer=null;hoverSnap=null;refreshSnapTargets();updateDrawingControls();drawPhoto();}
function cancelDrawing(){workingPoints=[];workingRedo=[];redrawId=null;faceSeedMode=false;lastPointer=null;hoverSnap=null;drag=null;refreshSnapTargets();updateDrawingControls();drawPhoto();status('已取消本次绘制；已经完成的标注保持不变。');}
function drawPointerHelp(ctx,p,t,width,height){
  if(!hoverSnap)return;const q=hoverSnap.point,x=t.x+q[0]*t.s,y=t.y+q[1]*t.s,target=hoverSnap.target;
  if(workingPoints.length&&$('featureKind').value!=='edit'){const last=workingPoints[workingPoints.length-1];ctx.save();ctx.setLineDash([4,4]);ctx.strokeStyle='#476d61';ctx.lineWidth=1.2;ctx.beginPath();ctx.moveTo(t.x+last[0]*t.s,t.y+last[1]*t.s);ctx.lineTo(x,y);ctx.stroke();ctx.restore();}
  ctx.strokeStyle=target?'#b24e16':'#284f74';ctx.lineWidth=2;ctx.beginPath();ctx.arc(x,y,target?9:5,0,Math.PI*2);ctx.moveTo(x-13,y);ctx.lineTo(x+13,y);ctx.moveTo(x,y-13);ctx.lineTo(x,y+13);ctx.stroke();
  if(target){const label=target.kind==='image_corner'?'候选角点':target.label;ctx.font='bold 12px system-ui';const textWidth=ctx.measureText(label).width+14,bx=Math.max(3,Math.min(width-textWidth-3,x+15)),by=Math.max(22,y-14);ctx.fillStyle='#fff9e8';ctx.fillRect(bx,by-17,textWidth,23);ctx.fillStyle='#824321';ctx.fillText(label,bx+7,by);}
  if(prefs.loupe){const r=50,cx=width-r-10,cy=r+10,sourceWidth=100/Math.max(t.s*2,0.01);ctx.save();ctx.beginPath();ctx.arc(cx,cy,r,0,Math.PI*2);ctx.clip();ctx.fillStyle='white';ctx.fill();ctx.drawImage(p.image,q[0]-sourceWidth/2,q[1]-sourceWidth/2,sourceWidth,sourceWidth,cx-r,cy-r,r*2,r*2);ctx.strokeStyle='#c14a1b';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(cx-10,cy);ctx.lineTo(cx+10,cy);ctx.moveTo(cx,cy-10);ctx.lineTo(cx,cy+10);ctx.stroke();ctx.restore();ctx.strokeStyle='#426e58';ctx.lineWidth=2;ctx.beginPath();ctx.arc(cx,cy,r,0,Math.PI*2);ctx.stroke();}
}
$('audienceMode').onchange=()=>{prefs.audience=$('audienceMode').value;if(prefs.audience==='teacher')$('showReferenceIndices').checked=false;persistPreferences();applyAudience();};
$('viewFocus').onchange=updatePresentation;$('showFaceIds').onchange=drawViews;$('showReferenceIndices').onchange=updatePresentation;
for(const [id,key] of [['snapEnabled','snap'],['snapImageCorners','imageCorners'],['snapMidpoints','midpoints'],['snapIntersections','intersections'],['showSnapGuides','showGuides'],['pointLoupe','loupe']]){
  $(id).checked=prefs[key];$(id).onchange=()=>{prefs[key]=$(id).checked;persistPreferences();refreshSnapTargets();updateDrawingControls();drawPhoto();if(key==='imageCorners')ensurePhotoGuides();};
}
$('snapRadius').value=String(prefs.radius);$('snapRadius').onchange=()=>{prefs.radius=+$('snapRadius').value;persistPreferences();refreshHover();drawPhoto();};
$('refreshPhotoGuides').onclick=()=>ensurePhotoGuides(true);
$('backPoint').onclick=backDrawingPoint;$('placeCoordinate').onclick=()=>{if(!busy)placeDrawingPoint([+$('pointX').value,+$('pointY').value]);};
$('featureKind').dataset.previous=$('featureKind').value;
document.querySelectorAll('[data-draw-tool]').forEach(b=>b.onclick=()=>setDrawingTool(b.dataset.drawTool));

new ResizeObserver(()=>{drawViews();}).observe(document.querySelector('.view-area'));
new ResizeObserver(()=>{drawPhoto();}).observe(document.querySelector('.photo-canvas-wrap'));
new ResizeObserver(entries=>document.documentElement.style.setProperty('--shell-height',Math.ceil(entries[0].borderBoxSize?.[0]?.blockSize||entries[0].contentRect.height)+'px')).observe(document.querySelector('.app-shell'));
document.addEventListener('keydown',e=>{
  if(e.key==='Shift'){shiftHeld=true;refreshHover();drawPhoto();}
  const node=e.target,active=node===cv||$('photoEditor').contains(node),editable=node.isContentEditable||['INPUT','SELECT','TEXTAREA'].includes(node.tagName);
  if(e.key==='Escape'&&axisPicking&&!editable&&!busy){axisPicking=null;axisPoints=[];drawViews();}
  const action=X.keyboardAction({key:e.key,tagName:node.tagName,isContentEditable:node.isContentEditable,active,ctrlKey:e.ctrlKey,metaKey:e.metaKey,shiftKey:e.shiftKey});
  if(!action||busy)return;e.preventDefault();
  if(action==='finish')finishFeature();else if(action==='back'||(action==='undo'&&workingPoints.length))backDrawingPoint();else if(action==='cancel')cancelDrawing();else if(action==='undo')$('photoUndo').click();else if(action==='redo'){if(workingRedo.length){workingPoints.push(workingRedo.pop());refreshSnapTargets();updateDrawingControls();drawPhoto();}else $('photoRedo').click();}
});
document.addEventListener('keyup',e=>{if(e.key==='Shift'){shiftHeld=false;if(lastPointer)lastPointer.shift=false;refreshHover();drawPhoto();}});
window.addEventListener('blur',()=>{shiftHeld=false;lastPointer=null;hoverSnap=null;drag=null;drawPhoto();});
function refreshLayoutSummary(){
  if(!$('quickSave'))return;
  $('quickSave').textContent=layoutWorkspace==='photo'?'保存标注':'保存模型';$('quickSave').disabled=busy||!result;
  $('layoutProjectTitle').textContent=result?.draft.title||'正在载入项目';$('layoutProjectTitle').title=result?.draft.title||'';
  $('layoutProjectMeta').textContent=result?`${result.model.faces.length} 个面 · ${photos.length} 张照片 · 本机参考模型`:'参考模型 · 保留来源';
  $('revealReference').hidden=!(prefs.audience==='teacher'&&!$('showReferenceIndices').checked);
}
function afterWorkspaceChange({key,source}){
  layoutWorkspace=key;drag=null;lastPointer=null;hoverSnap=null;if(!['initial','hashchange','popstate'].includes(source))window.scrollTo({top:0,behavior:'instant'});
  for(const [node,pointerId] of activePointers){try{if(node.hasPointerCapture(pointerId))node.releasePointerCapture(pointerId);}catch(error){}node.dispatchEvent(new Event('pointercancel'));}activePointers.clear();
  if(key==='parameters'&&!parametersVisited){$('faceResultsDisclosure').open=true;parametersVisited=true;}
  if(key==='model'&&location.hash==='#startSection')$('startSection').open=true;
  if(key==='parameters'&&location.hash==='#axesSection')$('axesDisclosure').open=true;
  refreshLayoutSummary();requestAnimationFrame(()=>{drawViews();drawPhoto();});
}
for(const id of [...views.map(v=>v[0]),'correctionCanvas']){
  $(id).addEventListener('gotpointercapture',e=>activePointers.set($(id),e.pointerId));
  $(id).addEventListener('lostpointercapture',()=>activePointers.delete($(id)));
}
$('quickSave').onclick=()=>{if(busy||!result)return;const action=X.saveAction(layoutWorkspace,workingPoints.length,photos.length);if(action.reason)return status(action.reason,true);$(action.target).click();};
$('expandStatus').onclick=()=>{const expanded=$('expandStatus').getAttribute('aria-expanded')!=='true';$('expandStatus').setAttribute('aria-expanded',String(expanded));document.querySelector('.status-bar').classList.toggle('expanded',expanded);};
$('closeLayoutHelp').onclick=()=>{$('layoutHelp').open=false;$('layoutHelp').querySelector('summary').focus();};
$('revealReference').onclick=()=>{$('showReferenceIndices').checked=true;updatePresentation();refreshLayoutSummary();};
const inspectorMedia=matchMedia('(max-width:850px)');let mobileInspectorOpen=false;
$('photoInspectorDisclosure').querySelector('summary').addEventListener('click',()=>{if(inspectorMedia.matches)mobileInspectorOpen=!$('photoInspectorDisclosure').open;});
function resizeInspector(){ $('photoInspectorDisclosure').open=!inspectorMedia.matches||mobileInspectorOpen; }
inspectorMedia.addEventListener('change',resizeInspector);resizeInspector();
workspaceNav=AtlasEditorNavigation.mount({document,window,onChange:afterWorkspaceChange});
document.querySelectorAll('[data-workspace-link]').forEach(link=>link.addEventListener('click',event=>{if(event.button!==0||event.ctrlKey||event.metaKey||event.shiftKey||event.altKey)return;const destination=link.dataset.workspaceLink;$('layoutHelp').open=false;if(destination==='startSection')$('startSection').open=true;if(destination==='axesSection')$('axesDisclosure').open=true;}));

(async()=>{try{const [config,refs]=await Promise.all([fetch('/api/config').then(r=>r.json()),fetch('/api/examples').then(r=>r.json())]);token=config.token;examples=refs;$('referenceModel').innerHTML=examples.map((s,i)=>`<option value="${i}">${esc(s.id)} · ${esc(s.title||'参考外形')}</option>`).join('');
  const carried=sessionStorage.getItem('mineral-atlas-edit-spec');if(carried){const spec=JSON.parse(carried);adopt(await api('/api/editor',{action:'import',spec}),{reset:true});sessionStorage.removeItem('mineral-atlas-edit-spec');}else{const local=localStorage.getItem('mineral-atlas-editor-draft-v2');if(local){try{adopt(await api('/api/editor',{action:'analyze',draft:JSON.parse(local)}),{reset:true});}catch(e){status('已存草稿无法解析，可打开项目或新建。'+e.message,true);$('editorControls').disabled=false;return;}}else adopt(await api('/api/editor',{action:'create',preset:'box',title:'方柱 / 长方体'}),{reset:true});}
  $('editorControls').disabled=false;applyAudience();if(location.hash==='#axesSection')$('axesDisclosure').open=true;if(layoutWorkspace==='parameters')$('faceResultsDisclosure').open=true;updateButtons();drawPhoto();status('本机编辑器已就绪。选择面调整形状，或切换到“照片修正”拉线纠错。');
}catch(e){status(e.message,true);}})();
})();
