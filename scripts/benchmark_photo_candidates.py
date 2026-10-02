"""Photo-first regression. Private cases/annotations are read only by the scorer, not inference."""
import argparse,base64,json,pathlib,sys,time,statistics
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from atlas.images import from_photos
from atlas.project import source_hash

def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',type=pathlib.Path,required=True);p.add_argument('--source-root',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);p.add_argument('--limit',type=int);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    fingerprint=source_hash();cases=json.loads(a.cases.read_text(encoding='utf-8'));cases=cases[:a.limit] if a.limit else cases;rows=[]
    import numpy as np,cv2
    for case in cases:
        im=(a.source_root/case['source_relative_path']).read_bytes();encoded=base64.b64encode(im).decode();row={'id':case['id'],'expected_template':case['model_id']};start=time.perf_counter()
        try:
            r=from_photos([encoded]);ranks=[s['template_id'] for s in r['ranking']];row.update(status='ok',rank=ranks.index(case['model_id'])+1,top3=ranks[:3],score=r['candidates'][0]['score'],ranking=r['ranking'],warnings=r['warnings'])
            observation=r['observations'][0];row['segmentation_warnings']=observation['warnings'];poly=case['annotation']['silhouette']
            if poly:
                W,H=observation['image_size'];factor=min(1,600/max(W,H));shape=(round(H*factor),round(W*factor));truth=np.zeros(shape,'uint8');found=truth.copy()
                cv2.fillPoly(truth,[np.round(np.array(poly)*factor).astype('int32')],1);cv2.fillPoly(found,[np.round(np.array(observation['silhouette'])*factor).astype('int32')],1)
                row['silhouette_iou']=float(np.logical_and(truth,found).sum()/max(1,np.logical_or(truth,found).sum()))
            (a.out/(case['id']+'.json')).write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
        except Exception as e:row.update(status='error',error=f'{type(e).__name__}: {e}')
        row['seconds']=time.perf_counter()-start;rows.append(row);print(row['id'],row.get('rank'),round(row.get('silhouette_iou',-1),3),round(row['seconds'],2),row.get('error',''),flush=True)
        (a.out/'progress.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    groups=[]
    for key in sorted(set(c['model_id'] for c in cases)):
        rs=[r for r in rows if r['expected_template']==key and r['status']=='ok']
        if not rs:continue
        scores={s['template_id']:0 for s in rs[0]['ranking']}
        for r in rs:
            for s in r['ranking']:scores[s['template_id']]+=s['score']/len(rs)
        ranks=sorted(scores,key=scores.get);groups.append({'model':key,'views':len(rs),'rank':ranks.index(key)+1,'top3':ranks[:3]})
    good=[r for r in rows if r['status']=='ok'];ious=[r['silhouette_iou'] for r in good if 'silhouette_iou' in r]
    summary={'source_hash':fingerprint,'scope':'photo-first closed-set development regression; annotations are evaluation-only; not blind generalization','cases':len(rows),'successes':len(good),'failures':len(rows)-len(good),'segmentation_cases':len(ious),'median_iou':statistics.median(ious) if ious else None,'mean_iou':statistics.mean(ious) if ious else None,'top1':sum(r['rank']==1 for r in good),'top3':sum(r['rank']<=3 for r in good),'multiview_groups':len(groups),'multiview_top1':sum(g['rank']==1 for g in groups),'multiview_top3':sum(g['rank']<=3 for g in groups),'median_seconds':statistics.median(r['seconds'] for r in rows),'rows':rows,'multiview':groups,'limits':['Photographs and templates are previously seen development cases; template retrieval is not arbitrary 3D recovery.','No ground-truth depth or new physical Miller indices are measured.','No case ID, filename, old camera, hand annotation, or truth mesh selection enters inference.']}
    (a.out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8');print({k:v for k,v in summary.items() if k not in ('rows','multiview','limits')})

if __name__=='__main__':main()
