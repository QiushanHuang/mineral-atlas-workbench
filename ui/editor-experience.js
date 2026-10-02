(function(root){
  'use strict';
  function preferences(value={}){
    if(!value||typeof value!=='object')value={};
    const defaults={audience:'beginner',snap:true,radius:12,imageCorners:true,midpoints:false,intersections:true,showGuides:true,loupe:false};
    const result={...defaults};
    for(const key of ['snap','imageCorners','midpoints','intersections','showGuides','loupe'])if(typeof value[key]==='boolean')result[key]=value[key];
    if(['beginner','student','teacher'].includes(value.audience))result.audience=value.audience;
    if([6,12,20].includes(value.radius))result.radius=value.radius;
    return result;
  }
  function keyboardAction({key,tagName='',isContentEditable=false,active=false,ctrlKey=false,metaKey=false,shiftKey=false}){
    if(!active||isContentEditable||['INPUT','TEXTAREA','SELECT','BUTTON','A','SUMMARY'].includes(tagName.toUpperCase()))return null;
    if(ctrlKey||metaKey)return key.toLowerCase()==='z'?(shiftKey?'redo':'undo'):null;
    return {Enter:'finish',Backspace:'back',Escape:'cancel'}[key]||null;
  }
  function drawingHint(kind,count,hasPhoto){
    if(!hasPhoto)return {text:'先选择照片，或点击“试画合成示例”练习。',canFinish:false};
    if(kind==='edit')return {text:'拖动圆点、线段或面内部来修正；可展开“重新拉线”加减节点。',canFinish:false};
    const polygon=['face','silhouette','occlusion'].includes(kind),minimum=polygon?3:2;
    const name={edge:'棱线',face:'面区域',silhouette:'外轮廓',occlusion:'遮挡区域',uncertain:'不确定线'}[kind]||'标注';
    return {text:count===0?`正在画${name}：点击第一个角点。`:count<minimum?`已放 ${count} 个点；再放 ${minimum-count} 个点即可完成${name}。`:`已放 ${count} 个点；按 Enter 完成${name}${polygon?'，也可在拾取开启时点击首点闭合':''}。`,canFinish:count>=minimum};
  }
  function faceLabels(faces,analysisFaces=[],showIndices=false){
    const byId=new Map(analysisFaces.map(f=>[f.id,f]));
    return Object.fromEntries(faces.map(f=>{
      let label=f.id;
      if(showIndices){const known=f.modelMiller,candidate=byId.get(f.id)?.index_candidates?.candidates?.[0]?.hkl;label+=known?' · 参考('+known.join(' ')+')':candidate?' · 候选('+candidate.join(' ')+')':' · 指数未知';}
      return [f.id,label];
    }));
  }
  function photoFrame(size,canvas,bounds=null){
    let [left,top,right,bottom]=bounds||[0,0,...size];
    if(bounds){const pad=Math.max(12,Math.max(right-left,bottom-top)*.06);left=Math.max(0,left-pad);top=Math.max(0,top-pad);right=Math.min(size[0],right+pad);bottom=Math.min(size[1],bottom+pad);}
    if(!(right>left&&bottom>top))throw Error('没有有效的物体范围，请先画外轮廓');
    const s=Math.min(Math.max(1,canvas[0])/(right-left),Math.max(1,canvas[1])/(bottom-top));
    return {s,x:canvas[0]/2-(left+right)/2*s,y:canvas[1]/2-(top+bottom)/2*s};
  }
  function saveAction(workspace,unfinishedPoints,photoCount){
    if(workspace==='photo'){
      if(unfinishedPoints>0)return {target:null,reason:'先完成或取消正在画的标注，再保存。'};
      if(!photoCount)return {target:null,reason:'先选择照片或载入示例，再保存标注。'};
      return {target:'saveAnnotations',reason:null};
    }
    return {target:'saveDraft',reason:null};
  }
  const api={preferences,keyboardAction,drawingHint,faceLabels,photoFrame,saveAction};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.AtlasEditorExperience=api;
})(typeof globalThis!=='undefined'?globalThis:this);
