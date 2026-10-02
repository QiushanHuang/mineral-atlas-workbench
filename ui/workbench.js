'use strict';
const $=id=>document.getElementById(id);let config,spec,examples,model,run,image=null,imageData=null,imageSize=null,points=[],silhouette=[],centers={},fitView=null,holdout=[];let currentModelSpec=null;
const escapeHTML=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function status(s,error=false){$('status').textContent=s;$('status').className=error?'error':'';}
async function api(path,data){const response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-Atlas-Token':config.token},body:JSON.stringify(data)});let result=await response.json();if(!response.ok)throw Error(result.error||'本机处理失败');return result;}
function download(name,data,type='application/json'){const url=URL.createObjectURL(new Blob([typeof data==='string'?data:JSON.stringify(data,null,2)],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),500);}
function read(file){return new Promise((resolve,reject)=>{const r=new FileReader();r.onerror=reject;r.onload=()=>resolve(r.result);r.readAsDataURL(file);});}
function sync(){spec.id=$('projectId').value.trim();spec.title=$('projectTitle').value.trim();$('specEditor').value=JSON.stringify(spec,null,2);}
function renderSpec(){
 $('projectId').value=spec.id;$('projectTitle').value=spec.title||spec.id;$('summary').textContent=`${spec.crystal_system} · ${spec.point_group} · ${spec.index_count===4?'四轴 h k i l':'三轴 h k l'} · ${spec.expected_faces||'待计算'} 面`;
 const rows=spec.faces||spec.forms;const mode=spec.faces?'faces':'forms';$('rows').innerHTML='<table><thead><tr><th>面 / 晶形</th><th>指数</th><th>支持距离</th><th>说明</th></tr></thead><tbody>'+rows.map((f,i)=>`<tr><td>${escapeHTML(f.id||'晶形 '+(i+1))}</td><td><input data-row="${i}" data-field="hkl" aria-label="第${i+1}项指数" value="${f.hkl.join(' ')}"></td><td><input data-row="${i}" data-field="distance" aria-label="第${i+1}项面距" type="number" min="0.00001" step="0.05" value="${f.distance}"></td><td>${escapeHTML(f.label||'按指定点群展开')}</td></tr>`).join('')+'</tbody></table>';
 $('rows').querySelectorAll('input').forEach(e=>e.addEventListener('change',()=>{const f=spec[mode][+e.dataset.row];if(e.dataset.field==='distance')f.distance=Number(e.value);else f.hkl=e.value.trim().split(/[ ,]+/).map(Number);sync();}));sync();points=[];centers={};holdout=[];fitView=null;model=null;currentModelSpec=null;$('face').replaceChildren();$('faceInfo').textContent='修改参数后请重新生成模型。';
}
async function busy(button,fn){button.disabled=true;try{await fn();}catch(e){status(e.message,true);}finally{button.disabled=false;}}
async function showRun(result){
 run=result;const base='/runs/'+encodeURIComponent(result.run_id)+'/';$('viewer').src=base+'index.html';$('viewer').hidden=false;$('openViewer').href=base+'index.html';$('openViewer').hidden=false;const q=result.quality;$('quality').innerHTML=[`V ${q.vertices}`,`E ${q.edges}`,`F ${q.faces}`,`Euler ${q.euler}`,q.ok?'几何检查通过':'未通过',result.cached?'命中已校验缓存':`构形 ${result.elapsed_seconds.toFixed(3)}s`].map(x=>'<span>'+escapeHTML(x)+'</span>').join('');
 $('links').innerHTML=[['result.zip','完整离线包'],['report.html','五项报告'],['input.json','输入参数'],['quality.json','校验结果'],['receipt.json','复现记录']].map(([p,t])=>`<a href="${base+p}" target="_blank" rel="noopener" ${p.endsWith('.zip')?'download':''}>${t}</a>`).join('');
 model=await (await fetch(base+'model.json')).json();currentModelSpec=JSON.stringify(spec);const oldFace=$('face').value;$('face').innerHTML=model.faces.map(f=>`<option value="${f.id}">${f.id} (${f.modelMiller.join(' ')}) · ${escapeHTML(f.label)}</option>`).join('');$('centerFace').innerHTML=$('face').innerHTML;if(model.faces.some(f=>f.id===oldFace))$('face').value=oldFace;faceInfo();
}
function faceInfo(){if(!model)return;const f=model.faces.find(f=>f.id===$('face').value);$('faceInfo').textContent=`需要 ${f.ids.length} 个角点；顶点ID：${f.ids.join('、')}。先根据原图确认面编号，再沿边界点击。`;}
function annotation(){return {schema_version:1,face_id:$('face').value,image_size:imageSize,mode:'cyclic',points,silhouette,face_centers:centers,holdout,loss:$('loss').value,orientation:'browser-display-exif-applied',mirror:'not_assumed'};}
function draw(){
 const cv=$('photoCanvas'),box=cv.getBoundingClientRect(),dpr=devicePixelRatio||1;cv.width=Math.round(box.width*dpr);cv.height=Math.round(box.height*dpr);const ctx=cv.getContext('2d');ctx.scale(dpr,dpr);const w=box.width,h=box.height;ctx.fillStyle='#e9eee6';ctx.fillRect(0,0,w,h);
 if(!image){ctx.fillStyle='#647c6b';ctx.font='14px system-ui';ctx.fillText('选择本地照片后，依次点击晶面的角点',20,40);return;}
 const s=Math.min(w/imageSize[0],h/imageSize[1]),ox=(w-imageSize[0]*s)/2,oy=(h-imageSize[1]*s)/2;cv.viewTransform={s,ox,oy};ctx.drawImage(image,ox,oy,imageSize[0]*s,imageSize[1]*s);
 for(const [list,color] of [[points,'#397dff'],[silhouette,'#e7ac31']]){ctx.strokeStyle=color;ctx.lineWidth=2;ctx.beginPath();list.forEach((p,i)=>{const x=ox+p[0]*s,y=oy+p[1]*s;i?ctx.lineTo(x,y):ctx.moveTo(x,y);});if(list.length>2)ctx.closePath();ctx.stroke();list.forEach((p,i)=>{ctx.beginPath();ctx.arc(ox+p[0]*s,oy+p[1]*s,4,0,Math.PI*2);ctx.fillStyle=color;ctx.fill();ctx.font='bold 12px system-ui';ctx.fillText(i+1,ox+p[0]*s+7,oy+p[1]*s-5);});}
 for(const [id,p] of Object.entries(centers)){ctx.fillStyle='#fff';ctx.font='bold 12px system-ui';ctx.fillText(id,ox+p[0]*s,oy+p[1]*s);}
 if(fitView&&model){const v=fitView;function project(p){const q=v.R.map(r=>r.reduce((a,x,i)=>a+x*p[i],0));return [ox+(q[0]*v.scale/(1-q[2]/v.D)+v.offset[0])*s,oy+(-q[1]*v.scale/(1-q[2]/v.D)+v.offset[1])*s];}ctx.lineWidth=1.5;ctx.strokeStyle='#27f1c4';for(const f of model.faces){const n=v.R.map(r=>r.reduce((a,x,i)=>a+x*f.n[i],0)),c=v.R.map(r=>r.reduce((a,x,i)=>a+x*f.center[i],0));if(n[0]*-c[0]+n[1]*-c[1]+n[2]*(v.D-c[2])<=0)continue;ctx.beginPath();f.ids.forEach((id,i)=>{const p=project(model.vertices[id]);i?ctx.lineTo(...p):ctx.moveTo(...p);});ctx.closePath();ctx.stroke();}}
 $('annotationInfo').textContent=`${imageSize.join(' × ')} 像素 · ${points.length} 个面角点 · ${silhouette.length} 个外轮廓点 · ${Object.keys(centers).length} 个面中心`;
}
$('photoCanvas').addEventListener('click',e=>{if(!image)return;const b=e.currentTarget.getBoundingClientRect(),t=e.currentTarget.viewTransform,p=[(e.clientX-b.left-t.ox)/t.s,(e.clientY-b.top-t.oy)/t.s];if(p.some((x,i)=>x<0||x>imageSize[i]))return;const rounded=p.map(x=>Math.round(x*10)/10);if($('layer').value==='points')points.push(rounded);else if($('layer').value==='silhouette')silhouette.push(rounded);else if($('centerFace').value)centers[$('centerFace').value]=rounded;fitView=null;draw();});
$('photo').onchange=async e=>{try{const file=e.target.files[0];if(!file)return;if(file.size>16*1024*1024)throw Error('照片超过16MiB');imageData=await read(file);const im=new Image();im.onload=()=>{image=im;imageSize=[im.naturalWidth,im.naturalHeight];points=[];silhouette=[];centers={};holdout=[];fitView=null;draw();};im.src=imageData;}catch(e){status(e.message,true);}};
$('demo').onclick=()=>busy($('demo'),async()=>{const d=await (await fetch('/api/demo')).json();spec=d.spec;renderSpec();const result=await api('/api/build',{spec});await showRun(result);imageData=d.image;await new Promise((resolve,reject)=>{const im=new Image();im.onload=()=>{image=im;imageSize=[im.naturalWidth,im.naturalHeight];resolve();};im.onerror=reject;im.src=imageData;});const a=d.annotation;$('face').value=a.face_id;points=a.points;silhouette=a.silhouette;centers={};holdout=a.holdout;$('loss').value=a.loss;faceInfo();fitView=null;draw();status('已载入合成几何与已知相机标注；这是流程校验示例，不是实物照片。');});
$('layer').onchange=()=>{$('centerFaceLabel').hidden=$('layer').value!=='center';};
$('face').onchange=()=>{faceInfo();points=[];fitView=null;draw();};$('undo').onclick=()=>{const l=$('layer').value;if(l==='points')points.pop();else if(l==='silhouette')silhouette.pop();else delete centers[$('centerFace').value];fitView=null;draw();};$('clear').onclick=()=>{const l=$('layer').value;if(l==='points')points=[];else if(l==='silhouette')silhouette=[];else centers={};fitView=null;draw();};
$('saveAnnotation').onclick=()=>{if(!imageSize)return status('请先选择照片',true);download((spec?.id||'photo')+'-annotation.json',annotation());};
$('importAnnotation').onchange=async e=>{try{const a=JSON.parse(await e.target.files[0].text());if(a.mode&&a.mode!=='cyclic')throw Error('界面仅编辑逐面cyclic标注；指定跨面顶点对应请使用CLI，以免丢失vertex_ids');if(imageSize&&JSON.stringify(imageSize)!==JSON.stringify(a.image_size))throw Error('标注图像尺寸与当前照片不同；请确认是同一原图和方向');$('face').value=a.face_id;points=a.points||[];silhouette=a.silhouette||[];centers=a.face_centers||{};holdout=a.holdout||[];$('loss').value=a.loss||'soft_l1';faceInfo();fitView=null;draw();status('标注已载入；图片与面编号还需人工核对。');}catch(e){status(e.message,true);}};
$('example').onchange=()=>{spec=structuredClone(examples[+$('example').value]);renderSpec();};$('projectId').onchange=sync;$('projectTitle').onchange=sync;
$('applyJson').onclick=()=>{try{spec=JSON.parse($('specEditor').value);renderSpec();status('参数已应用；生成时会重新检查。');}catch(e){status('参数JSON无效：'+e.message,true);}};
$('saveSpec').onclick=()=>{sync();download(spec.id+'.json',spec);};$('importButton').onclick=()=>$('importSpec').click();$('importSpec').onchange=async e=>{try{spec=JSON.parse(await e.target.files[0].text());renderSpec();status('参数已导入。');}catch(e){status(e.message,true);}};
$('build').onclick=()=>busy($('build'),async()=>{sync();status('正在构形并检查…');const result=await api('/api/build',{spec});fitView=null;await showRun(result);status('模型与报告已生成。');});
$('fit').onclick=()=>busy($('fit'),async()=>{if(!image||!model)throw Error('请先生成模型并选择照片');sync();if(JSON.stringify(spec)!==currentModelSpec)throw Error('参数已改变，请先重新生成模型');status('正在本机配准相机姿态…');const result=await api('/api/fit',{spec,annotation:annotation(),image:imageData});fitView=result.view;$('fitQuality').textContent=JSON.stringify(result.quality,null,2);if(result.artifact)await showRun(result.artifact);draw();status(result.quality.ambiguity?'配准存在多个近似解；请用另一视角或编号消歧。':'配准完成，请核对未参与拟合的棱与其他照片。');});
for(const [id,path] of [['inspect','/api/inspect'],['ocr','/api/ocr'],['vision','/api/vision']])$(id).onclick=()=>busy($(id),async()=>{if(!imageData)throw Error('请先选择照片');status('正在本机处理图像…');const result=await api(path,{image:imageData,model_name:$('visionModel').value,language:'eng'});$('suggestions').textContent=JSON.stringify(result,null,2);status('图像工具返回了待核对结果；没有更改模型参数。');});
new ResizeObserver(draw).observe($('photoCanvas'));
(async()=>{try{[config,examples]=await Promise.all([fetch('/api/config').then(r=>r.json()),fetch('/api/examples').then(r=>r.json())]);$('example').innerHTML=examples.map((s,i)=>`<option value="${i}">${escapeHTML(s.id+' · '+s.title)}</option>`).join('');spec=structuredClone(examples[0]);renderSpec();$('doctor').textContent=JSON.stringify(config.doctor);$('fit').disabled=!config.doctor.fit;$('fit').title=config.doctor.fit?'':'当前Python缺少NumPy/SciPy；仍可使用核心建模与报告';$('ocr').disabled=!config.doctor.tesseract;$('generateCandidates').disabled=!config.doctor.photo_candidates;if(!config.doctor.photo_candidates)$('candidateStatus').textContent='当前Python缺少照片算法依赖，请配置requirements-photo.lock';status('离线核心已就绪。'+(config.doctor.fit?'相机拟合可用。':'可选相机拟合依赖尚未安装。'));draw();}catch(e){status('无法连接本机服务：'+e.message,true);}})();

let candidateImages=[],candidateResult=null,candidateEpoch=0,candidateLoading=false;
function coverageControl(i,value='unknown'){
 return `<label>这张照片<select data-coverage="${i}">${[['unknown','完整性不确定'],['complete','物体完整可见'],['partial','有遮挡或残缺']].map(([v,t])=>`<option value="${v}" ${v===value?'selected':''}>${t}</option>`).join('')}</select></label>`;
}
$('candidatePhotos').onchange=async event=>{
 const epoch=++candidateEpoch;candidateImages=[];candidateResult=null;$('generateCandidates').disabled=true;
 $('candidateResults').replaceChildren();$('candidateWarnings').hidden=true;$('saveCandidates').hidden=true;$('evidenceAnalysis').hidden=true;
 try{
  const files=[...event.target.files];if(!files.length)return;
  const policy=config.photo_policy||{max_photos:24,max_total_bytes:64*1024*1024};
  if(files.length>policy.max_photos||files.reduce((n,f)=>n+f.size,0)>policy.max_total_bytes)throw Error('请选择1–24张照片，合计不超过64MiB');
  $('candidateStatus').textContent='正在读取照片…';
  const loaded=await Promise.all(files.map(read));if(epoch!==candidateEpoch)return;candidateImages=loaded;
  $('photoInputs').innerHTML=candidateImages.map((data,i)=>`<figure><img src="${data}" alt="输入照片${i+1}"><figcaption>照片 ${i+1}</figcaption>${coverageControl(i)}</figure>`).join('');
  $('candidateStatus').textContent=`已选择${files.length}张照片`;
 }catch(e){status(e.message,true);$('candidateStatus').textContent='照片未载入，请重新选择';}
 finally{if(epoch===candidateEpoch)$('generateCandidates').disabled=!config?.doctor?.photo_candidates||!candidateImages.length;}
};
function residualSummary(candidate){
 const groups=[['symmetric_outline_rmse','双向轮廓偏差'],['clipped_one_sided_outline','局部截断评分（仅排序）']];
 return groups.map(([metric,label])=>{const rows=candidate.per_photo.filter(p=>p?.metric===metric);return rows.length?`${label} ${(100*rows.reduce((n,p)=>n+p.normalized_silhouette_rmse,0)/rows.length).toFixed(2)}%`:'';}).filter(Boolean).join('；');
}
$('generateCandidates').onclick=()=>busy($('generateCandidates'),async()=>{
 if(!candidateImages.length)throw Error('请先选择同一物体的照片');
 const requestImages=[...candidateImages],epoch=++candidateEpoch;
 const locked=[...document.querySelectorAll('#photoStart input,#photoStart select,#photoStart textarea')].map(element=>[element,element.disabled]);locked.forEach(([element])=>element.disabled=true);
 try{
 const constraints={};if($('candidateSystem').value)constraints.crystal_system=$('candidateSystem').value;
 if($('candidateCount').value)constraints.expected_faces=Number($('candidateCount').value);
 const boxes=$('candidateBoxes').value.trim()?JSON.parse($('candidateBoxes').value):undefined;
 $('candidateStatus').textContent='正在本机提取轮廓并比较候选…';status('正在生成照片候选，请稍候…');
 const evidence={morphology:$('candidateMorphology').value,strength:$('morphologyStrength').value,coverage:[...$('photoInputs').querySelectorAll('select[data-coverage]')].map(element=>element.value)};
 const r=await api('/api/from-photos',{images:requestImages,boxes,constraints,evidence});if(epoch!==candidateEpoch)return;candidateResult=r;
 $('photoInputs').innerHTML=r.observations.map((o,i)=>{
  const group=r.fusion.groups.findIndex(g=>g.members.includes(i));
  return `<figure><img src="${o.preview||requestImages[i]}" alt="照片${i+1}的处理结果"><figcaption>照片 ${i+1} · ${o.status==='unusable'?'未参与排序':`视角组${group+1} · 组权重 ${r.fusion.groups[group].effective_weight.toFixed(2)}`}<br>${escapeHTML(o.warnings.filter(w=>!w.startsWith('自动物体定位')).join('；'))}</figcaption>${coverageControl(i,o.input_coverage||'unknown')}</figure>`;
 }).join('');
 const parsed=r.morphology.parsed,analysis=r.analysis,loo=r.fusion.leave_one_group_out;
 $('evidenceAnalysis').innerHTML=`<h3>证据与不确定项</h3><p>${r.performance.photos}张输入，${r.performance.usable_photos}张可用，合并为${r.fusion.independent_views}组；${r.fusion.redundant_photos}张重复或高度相似。</p><p>形态原文：${escapeHTML(parsed.raw||'未提供')}<br>识别到的线索：${escapeHTML(parsed.matched.join('、')||'无')}<br>未理解的片段：${escapeHTML(parsed.unparsed||'无')}</p><p>${loo.length?`去掉一组视角后，首选保持 ${r.fusion.winner_stable_count}/${loo.length} 次；这不是正确率。`:'有效视角组不足3组，暂不计算删一组稳定性。'}${analysis.prior_changed_winner?'形态软提示改变了首选，请同时核对图像依据。':''}</p><p>冲突照片：${r.fusion.conflicting_photos.map(i=>i+1).join('、')||'未检出'}；未采用照片：${analysis.excluded_photos.map(i=>i+1).join('、')||'无'}。</p><ul>${analysis.next_observations.map(t=>`<li>${escapeHTML(t)}</li>`).join('')}</ul>`;
 $('evidenceAnalysis').hidden=false;
 $('candidateWarnings').textContent=r.warnings.join(' ');$('candidateWarnings').hidden=false;
 $('candidateResults').innerHTML=r.candidates.map((c,i)=>`<article class="candidate"><h3>候选 ${i+1} · ${escapeHTML(c.template_id)}</h3><p>${escapeHTML(c.title)}</p><p class="muted">${residualSummary(c)} · 不是识别置信度</p><p class="muted">融合图像得分 ${c.image_score.toFixed(4)} · 形态不符惩罚 ${c.morphology_penalty.toFixed(4)}</p><iframe title="候选${i+1}的交互3D预览" src="/runs/${encodeURIComponent(c.artifact.run_id)}/index.html?compact=1"></iframe><div class="row"><button class="primary" data-candidate="${i}">载入此候选继续核对</button><a target="_blank" rel="noopener" href="/runs/${encodeURIComponent(c.artifact.run_id)}/index.html">独立查看</a></div></article>`).join('');
 $('candidateResults').querySelectorAll('button[data-candidate]').forEach(button=>button.onclick=()=>busy(button,async()=>{
  if(candidateLoading)return;candidateLoading=true;
  let controls=[];
  try{
  const c=r.candidates[Number(button.dataset.candidate)];spec=structuredClone(c.spec);renderSpec();
  controls=[...document.querySelectorAll('button,input,select,textarea')].map(element=>[element,element.disabled]);controls.forEach(([element])=>element.disabled=true);
  await showRun(c.artifact);
  const photoIndex=c.representative_photo;imageData=requestImages[photoIndex];await new Promise((resolve,reject)=>{const im=new Image();im.onload=()=>{image=im;imageSize=[im.naturalWidth,im.naturalHeight];resolve();};im.onerror=reject;im.src=imageData;});
  silhouette=r.observations[photoIndex].silhouette;points=[];centers={};holdout=[];fitView=c.views[photoIndex];$('fitQuality').textContent='候选视角来自自动外轮廓。请先确认面编号，再标注角点进行精修。';draw();status('已载入初始候选；面号和晶体学参数仍是待核对先验。');$('preview').scrollIntoView({behavior:'smooth',block:'start'});
  }finally{controls.forEach(([element,disabled])=>element.disabled=disabled);candidateLoading=false;}
 }));
 $('saveCandidates').hidden=false;$('candidateStatus').textContent=`${r.performance.photos}张照片 / ${r.fusion.independent_views}组视角 · ${r.performance.templates}种参考形态 · ${r.performance.elapsed_seconds.toFixed(1)}秒`;
 status('候选已生成。请先检查分割轮廓，再选择合适的3D候选。');
 }finally{locked.forEach(([element,disabled])=>element.disabled=disabled);}
});
$('saveCandidates').onclick=()=>{if(candidateResult)download('photo-candidates.json',candidateResult);};

$('editCurrentModel').onclick=()=>{sync();sessionStorage.setItem('mineral-atlas-edit-spec',JSON.stringify(spec));location.href='editor.html';};
