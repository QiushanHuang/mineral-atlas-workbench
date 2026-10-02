(function (root) {
  'use strict';
  const dot = (a,b) => a.reduce((s,v,i)=>s+v*b[i],0);
  const mat = (A,p) => A.map(r=>dot(r,p));
  const views = {
    front: [[1,0,0],[0,0,1],[0,-1,0]],
    side: [[0,1,0],[0,0,1],[1,0,0]],
    top: [[1,0,0],[0,1,0],[0,0,1]],
    three: [[.866,-.5,0],[.25,.433,.866],[-.433,-.75,.5]]
  };
  function rotation(yaw,pitch) {
    const c=Math.cos(yaw),s=Math.sin(yaw),a=Math.cos(pitch),b=Math.sin(pitch);
    return [[c,-s,0],[s*b,c*b,a],[-s*a,-c*a,b]];
  }
  function rotateFrom(base,yaw,pitch){
    const c=Math.cos(yaw),s=Math.sin(yaw),a=Math.cos(pitch),b=Math.sin(pitch);
    const delta=[[c,0,s],[s*b,a,-c*b],[-s*a,b,c*a]];
    return delta.map(row=>[0,1,2].map(i=>row.reduce((n,v,j)=>n+v*base[j][i],0)));
  }
  function labelLayout(items,width,height){
    const placed=[];
    for(const item of items){
      const w=Math.min(item.width+8,width-12),h=item.height||20;
      let chosen=null;
      for(const offset of [0,1,-1,2,-2,3,-3,4,-4,5,-5,6,-6]){
        const x=Math.max(w/2+6,Math.min(width-w/2-6,item.x)),y=Math.max(h,Math.min(height-6,item.y+offset*(h+4)));
        const box={...item,x,y,left:x-w/2,right:x+w/2,top:y-h,bottom:y+3};
        if(!placed.some(p=>box.left<p.right+3&&box.right+3>p.left&&box.top<p.bottom+3&&box.bottom+3>p.top)){chosen=box;break;}
      }
      if(chosen)placed.push(chosen);
    }
    return placed;
  }
  function framing(model) { return Math.max(.1, ...model.vertices.map(p=>Math.hypot(...p))) * 1.22; }
  function draw(canvas, model, options={}) {
    const box=canvas.getBoundingClientRect(),w=box.width||400,h=box.height||300,dpr=root.devicePixelRatio||1;
    canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);
    const ctx=canvas.getContext('2d');ctx.scale(dpr,dpr);ctx.fillStyle='#f1f4ee';ctx.fillRect(0,0,w,h);
    if(!model) return {hits:[],vertices:[]};
    const R=options.rotation||views[options.view||'three'],scale=Math.min(w,h)/(2*(options.radius||framing(model)))*(options.zoom||1);
    const project=p=>{const q=mat(R,p);return [w/2+q[0]*scale,h/2-q[1]*scale,q[2]];};
    const vertices=model.vertices.map(project), hits=[],labels=[];
    const polygon=(ctx,ids,pts)=>{ctx.beginPath();ids.forEach((id,i)=>i?ctx.lineTo(...pts[id].slice(0,2)):ctx.moveTo(...pts[id].slice(0,2)));ctx.closePath();};
    const sorted=model.faces.map(f=>({f,n:mat(R,f.n),z:dot(R[2],f.center)})).sort((a,b)=>a.z-b.z);
    if(options.before){ctx.save();ctx.strokeStyle='#9d7895';ctx.setLineDash([5,4]);ctx.globalAlpha=options.overlayOpacity??.45;const pv=options.before.vertices.map(project);options.before.faces.forEach(f=>{polygon(ctx,f.ids,pv);ctx.stroke();});ctx.restore();}
    for(const {f,n} of sorted){
      if(n[2]<1e-8)continue;
      polygon(ctx,f.ids,vertices);ctx.fillStyle=(options.selected||[]).includes(f.id)?'#edb66f':`hsl(151 14% ${58+18*Math.max(0,n[2])}%)`;ctx.fill();
      ctx.strokeStyle='#31564a';ctx.lineWidth=(options.selected||[]).includes(f.id)?2.2:1.15;ctx.stroke();
      const p=project(f.center);ctx.font=`${options.fontSize||11}px system-ui`;if(options.showLabels!==false){const text=options.labels?.[f.id]||f.id;labels.push({text,id:f.id,x:p[0],y:p[1],anchor:p,width:ctx.measureText(text).width,height:(options.fontSize||11)+4,selected:(options.selected||[]).includes(f.id)});}hits.push({id:f.id,points:f.ids.map(i=>vertices[i].slice(0,2))});
    }
    if(options.axes){
      const origin=options.axes.origin||[0,0,0],start=project(origin),basis=options.axes.basis;
      const vectors=[0,1,2].map(i=>basis.map(row=>row[i]));
      if(options.axes.index_count===4)vectors.splice(2,0,vectors[0].map((x,i)=>-x-vectors[1][i]));
      vectors.forEach((v,i)=>{const len=Math.hypot(...v),p=project(v.map((x,j)=>origin[j]+x/len*(options.radius||framing(model))*.82));ctx.strokeStyle=['#c45d52','#468559','#bb9e3a','#4d73ad'][i];ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(...start.slice(0,2));ctx.lineTo(...p.slice(0,2));ctx.stroke();const a=Math.atan2(p[1]-start[1],p[0]-start[0]);ctx.beginPath();ctx.moveTo(p[0]-7*Math.cos(a-.4),p[1]-7*Math.sin(a-.4));ctx.lineTo(...p.slice(0,2));ctx.lineTo(p[0]-7*Math.cos(a+.4),p[1]-7*Math.sin(a+.4));ctx.stroke();ctx.fillStyle=ctx.strokeStyle;ctx.font='bold 12px system-ui';ctx.fillText((vectors.length===4?['a₁','a₂','a₃','c']:['a','b','c'])[i],p[0]+10,p[1]-7);});
    }
    ctx.font=`${options.fontSize||11}px system-ui`;ctx.textAlign='center';
    for(const label of labelLayout(labels.sort((a,b)=>Number(b.selected)-Number(a.selected)),w,h)){
      if(Math.hypot(label.x-label.anchor[0],label.y-label.anchor[1])>10){ctx.strokeStyle='#4b6e5c88';ctx.lineWidth=.8;ctx.beginPath();ctx.moveTo(label.anchor[0],label.anchor[1]);ctx.lineTo(label.x,label.y-5);ctx.stroke();}
      if(label.text!==label.id){ctx.fillStyle='#f8fbf0dd';ctx.fillRect(label.left,label.top,label.right-label.left,label.bottom-label.top);}
      ctx.fillStyle='#193e32';ctx.fillText(label.text,label.x,label.y,w-20);
    }
    if(options.showVertices){ctx.fillStyle='#5045a0';vertices.forEach(p=>{ctx.beginPath();ctx.arc(p[0],p[1],3,0,Math.PI*2);ctx.fill();});}
    return {hits,vertices,scale,project};
  }
  function hitTest(hits,p){for(const hit of [...hits].reverse()){let inside=false;const ps=hit.points;for(let i=0,j=ps.length-1;i<ps.length;j=i++){const a=ps[i],b=ps[j];if((a[1]>p[1])!==(b[1]>p[1])&&p[0]<(b[0]-a[0])*(p[1]-a[1])/(b[1]-a[1])+a[0])inside=!inside;}if(inside)return hit.id;}return null;}
  const api={draw,framing,hitTest,rotation,rotateFrom,labelLayout,views};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.AtlasEditorCanvas=api;
})(typeof globalThis!=='undefined'?globalThis:this);
