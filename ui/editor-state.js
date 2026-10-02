(function (root) {
  'use strict';
  const clone = value => JSON.parse(JSON.stringify(value));
  class History {
    constructor(initial) { this.items = [clone(initial)]; this.index = 0; }
    get current() { return clone(this.items[this.index]); }
    get canUndo() { return this.index > 0; }
    get canRedo() { return this.index < this.items.length - 1; }
    commit(value) {
      this.items = this.items.slice(0, this.index + 1);
      this.items.push(clone(value));
      if (this.items.length > 60) this.items.shift();
      this.index = this.items.length - 1;
      return this.current;
    }
    undo() { if (this.canUndo) this.index--; return this.current; }
    redo() { if (this.canRedo) this.index++; return this.current; }
  }
  function annotation(size, hash) { return {schema_version: 1, image_size: [...size], source_sha256: hash, features: []}; }
  function assertPhotoBinding(value,hash,size){
    if(!value||value.source_sha256!==hash||JSON.stringify(value.image_size)!==JSON.stringify(size))throw Error('这份标注不属于当前照片；请重新选择对应原图。');
  }
  function checkPoint(a, p) {
    if (!Array.isArray(p) || p.length !== 2 || p.some((x, i) => !Number.isFinite(x) || x < 0 || x > a.image_size[i])) throw Error('点必须位于原图像范围内');
    return p.map(v => Math.round(v * 100) / 100);
  }
  function validateFeature(a,f) {
    const ps=f.points,polygon=['silhouette','face','occlusion'].includes(f.kind);
    if(ps.length>(128)||ps.length<(polygon?3:2))throw Error(`此标注至少需要 ${polygon?3:2} 个点，最多128点`);
    if(new Set(ps.map(p=>p.join(','))).size!==ps.length)throw Error('标注含重复点；闭合区域不需要重复首点');
    ps.forEach(p=>checkPoint(a,p));
    if(!polygon)return;
    const cross=(a,b,c)=>(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);
    const on=(a,b,p)=>Math.abs(cross(a,b,p))<1e-8&&p[0]>=Math.min(a[0],b[0])&&p[0]<=Math.max(a[0],b[0])&&p[1]>=Math.min(a[1],b[1])&&p[1]<=Math.max(a[1],b[1]);
    let area=0;
    for(let i=0;i<ps.length;i++){
      const a=ps[i],b=ps[(i+1)%ps.length];area+=a[0]*b[1]-b[0]*a[1];
      for(let j=i+1;j<ps.length;j++){
        if(j===i+1||(i===0&&j===ps.length-1))continue;
        const c=ps[j],d=ps[(j+1)%ps.length];
        if((cross(a,b,c)*cross(a,b,d)<0&&cross(c,d,a)*cross(c,d,b)<0)||on(a,b,c)||on(a,b,d)||on(c,d,a)||on(c,d,b))throw Error('多边形自交，请调整端点');
      }
    }
    if(Math.abs(area)/2<1)throw Error('多边形退化，面积至少1平方像素');
  }
  function addFeature(a, kind, points, faceId = '') {
    if (!['edge','silhouette','face','occlusion','uncertain'].includes(kind)) throw Error('未知标注类型');
    const minimum = ['silhouette','face','occlusion'].includes(kind) ? 3 : 2;
    if (points.length < minimum) throw Error(`此标注至少需要 ${minimum} 个点`);
    const out = clone(a); let n = 1;
    while (out.features.some(f => f.id === `A${n}`)) n++;
    if(out.features.length>=128||out.features.reduce((n,f)=>n+f.points.length,0)+points.length>2048)throw Error('每图最多128项标注、2048个点');
    const feature={id: `A${n}`, kind, points: points.map(p => checkPoint(a, p)), ...(faceId ? {face_id: faceId} : {})};
    validateFeature(a,feature);out.features.push(feature);
    return out;
  }
  function edited(f){if(f.evidence&&!f.evidence.endsWith('；边界经用户编辑'))f.evidence=f.evidence.slice(0,1800)+'；边界经用户编辑';}
  function movePoint(a, id, index, point, options={}) {
    const out = clone(a), f = out.features.find(f => f.id === id);
    if (!f || !f.points[index]) throw Error('标注点不存在');
    const previous=f.points[index],next=checkPoint(a,point);
    for(const feature of out.features){let changed=false;feature.points=feature.points.map((p,i)=>{if((feature.id===id&&i===index)||(options.linked&&Math.hypot(p[0]-previous[0],p[1]-previous[1])<=.05)){changed=true;return [...next];}return p;});if(changed){validateFeature(a,feature);edited(feature);}}
    return out;
  }
  function translateFeature(a,id,delta,options={}){
    if(!Array.isArray(delta)||delta.length!==2||delta.some(v=>!Number.isFinite(v)))throw Error('移动量必须为有限二维坐标');
    const source=a.features.find(f=>f.id===id);if(!source)throw Error('请先选择标注');
    const out=clone(a);
    for(const f of out.features){let changed=false;f.points=f.points.map(p=>{if(f.id===id||(options.linked&&source.points.some(q=>Math.hypot(p[0]-q[0],p[1]-q[1])<=.05))){changed=true;return checkPoint(a,[p[0]+delta[0],p[1]+delta[1]]);}return p;});if(changed){validateFeature(a,f);edited(f);}}
    return out;
  }
  function replaceFeaturePoints(a,id,points){
    const out=clone(a),f=out.features.find(f=>f.id===id);if(!f)throw Error('请先选择标注');
    f.points=points.map(p=>checkPoint(a,p));validateFeature(a,f);edited(f);
    if(out.features.reduce((n,x)=>n+x.points.length,0)>2048)throw Error('每张照片最多2048个点');
    return out;
  }
  function translateSegment(a,id,index,delta,options={}){
    const f=a.features.find(f=>f.id===id),closed=f&&['face','silhouette','occlusion'].includes(f.kind);
    if(!f||!Number.isInteger(index)||index<0||index>=f.points.length-(closed?0:1))throw Error('线段不存在');
    if(!Array.isArray(delta)||delta.length!==2||delta.some(v=>!Number.isFinite(v)))throw Error('移动量必须为有限二维坐标');
    const indices=[index,(index+1)%f.points.length],old=indices.map(i=>f.points[i]),out=clone(a);
    for(const feature of out.features){let changed=false;feature.points=feature.points.map((p,i)=>{if((feature.id===id&&indices.includes(i))||(options.linked&&old.some(q=>Math.hypot(p[0]-q[0],p[1]-q[1])<=.05))){changed=true;return checkPoint(a,[p[0]+delta[0],p[1]+delta[1]]);}return p;});if(changed){validateFeature(a,feature);edited(feature);}}
    return out;
  }
  function insertPoint(a,id,segmentIndex,point){
    const f=a.features.find(f=>f.id===id);if(!f)throw Error('请先选择标注');
    const closed=['face','silhouette','occlusion'].includes(f.kind);
    if(!Number.isInteger(segmentIndex)||segmentIndex<0||segmentIndex>=f.points.length-(closed?0:1))throw Error('线段不存在');
    const ps=clone(f.points);ps.splice(segmentIndex+1,0,checkPoint(a,point));return replaceFeaturePoints(a,id,ps);
  }
  function removePoint(a,id,index){
    const f=a.features.find(f=>f.id===id);if(!f||!Number.isInteger(index)||!f.points[index])throw Error('标注点不存在');
    const ps=clone(f.points);ps.splice(index,1);return replaceFeaturePoints(a,id,ps);
  }
  function hitFeature(a,point,{scale=1,radius=10}={}){
    if(!Array.isArray(point)||point.length!==2||point.some(v=>!Number.isFinite(v))||!(scale>0)||!(radius>=0))return null;
    let vertex=null,segment=null,region=null;
    for(const f of [...a.features].reverse()){
      const ps=f.points,closed=['face','silhouette','occlusion'].includes(f.kind);
      ps.forEach((p,i)=>{const d=Math.hypot(p[0]-point[0],p[1]-point[1])*scale;if(d<=radius&&(!vertex||d<vertex.distance))vertex={featureId:f.id,type:'point',pointIndex:i,point:[...p],distance:d};});
      for(let i=0;i<ps.length-(closed?0:1);i++){
        const p=ps[i],q=ps[(i+1)%ps.length],dx=q[0]-p[0],dy=q[1]-p[1],den=dx*dx+dy*dy;if(den<1e-12)continue;
        const t=Math.max(0,Math.min(1,((point[0]-p[0])*dx+(point[1]-p[1])*dy)/den)),nearest=[p[0]+t*dx,p[1]+t*dy],d=Math.hypot(nearest[0]-point[0],nearest[1]-point[1])*scale;
        if(d<=radius&&(!segment||d<segment.distance||(Math.abs(d-segment.distance)<1e-9&&f.kind==='edge'&&segment.featureKind!=='edge')))segment={featureId:f.id,featureKind:f.kind,type:'segment',segmentIndex:i,point:nearest,distance:d};
      }
      if(closed&&!region){let inside=false;for(let i=0,j=ps.length-1;i<ps.length;j=i++){const p=ps[i],q=ps[j];if((p[1]>point[1])!==(q[1]>point[1])&&point[0]<(q[0]-p[0])*(point[1]-p[1])/(q[1]-p[1])+p[0])inside=!inside;}if(inside)region={featureId:f.id,type:'region',point:[...point],distance:0};}
    }
    return vertex||segment||region;
  }
  function removeFeature(a, id) { const out = clone(a); out.features = out.features.filter(f => f.id !== id); return out; }
  function updateFeature(a, id, patch) {
    const out=clone(a),f=out.features.find(f=>f.id===id);
    if(!f)throw Error('请先选择一项已保存的标注');
    if(patch.kind){addFeature(annotation(a.image_size,a.source_sha256),patch.kind,f.points);f.kind=patch.kind;}
    if('face_id' in patch){
      if(patch.face_id){if(!/^[a-f0-9]{64}$/.test(patch.model_fingerprint||''))throw Error('面关联缺少当前模型指纹');f.face_id=patch.face_id;f.model_fingerprint=patch.model_fingerprint;}
      else{delete f.face_id;delete f.model_fingerprint;}
    }
    if(out.features.filter(f=>f.kind==='silhouette').length>1)throw Error('一张照片只能有一条完整外轮廓');
    return out;
  }
  function pixelPoint(point, transform, size) {
    const p = [(point[0] - transform.x) / transform.s, (point[1] - transform.y) / transform.s];
    return p.some((v, i) => v < 0 || v > size[i]) ? null : p;
  }
  function matchAnnotations(hashes, annotations) {
    const pools=new Map();annotations.forEach(a=>{if(!pools.has(a.source_sha256))pools.set(a.source_sha256,[]);pools.get(a.source_sha256).push(a);});
    const matched=hashes.map(h=>pools.get(h)?.shift()||null);
    for(const h of new Set(hashes))if(pools.get(h)?.length)throw Error('纠错文件有额外重复照片，请同时载入这些照片；相同图片按出现次序匹配');
    return clone(matched);
  }
  const api = {History, annotation, addFeature, movePoint, removeFeature, pixelPoint, updateFeature, matchAnnotations, translateFeature, translateSegment, replaceFeaturePoints, insertPoint, removePoint, hitFeature, assertPhotoBinding};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.AtlasEditorState = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
