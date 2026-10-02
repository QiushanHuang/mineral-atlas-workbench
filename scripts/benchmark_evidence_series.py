"""Reusable 1/2/4/all-view and uncertain-morphology ablation. Inference sees pixels + explicit hints only."""
import argparse,base64,json,pathlib,sys,statistics
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from atlas.images import from_photos
from atlas.photo_evidence import fuse_scores,morphology_penalties,parse_morphology
from atlas.project import ROOT,source_hash

# These are supplied-information scenarios, not descriptions predicted from the test images.
HINTS={'128':'柱状或长方体，局部看不清','333':'柱状或锥状，信息不完整','511':'四方柱或四方锥','722':'可能五角十二面体或八面体','5518':'四方柱或双锥组合','7518':'八面体或多面体组合','3519':'长方体或柱状','2522':'三方柱或截尖锥','439':'三方柱或三方锥组合','451':'菱面体或倾斜柱状','611':'六方双锥或六方柱，端部信息不完整','6512':'六方柱或六方双锥','671':'三方柱或三方双锥','675':'三方双锥或三方锥'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--photos',type=pathlib.Path,required=True,help='existing photo manifest');p.add_argument('--photo-root',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);p.add_argument('--models',nargs='*');p.add_argument('--reuse-fit-records',type=pathlib.Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    manifest=json.loads(a.photos.read_text(encoding='utf-8'));specs=json.loads((ROOT/'examples/reference-atlas.json').read_text(encoding='utf-8'));fingerprint=source_hash();rows=[];curves=[]
    for key,photos in manifest.items():
        if not photos or (a.models and key not in a.models):continue
        images=[None]*len(photos)
        if a.reuse_fit_records:
            r=json.loads((a.reuse_fit_records/(key+'.json')).read_text(encoding='utf-8'))
        else:
            images=[base64.b64encode((a.photo_root/photo['path']).read_bytes()).decode() for photo in photos]
            r=from_photos(images,evidence={'morphology':HINTS.get(key,'')});(a.out/(key+'.json')).write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
        matrix=r['diagnostics']['score_matrix'];obs=r['observations'];penalties,_=morphology_penalties(specs,parse_morphology(HINTS.get(key,'')))
        variants=[('1',1),('2',2)]+([('4',4)] if len(images)>=4 else [])+[('all',len(images))]
        for label,n in variants:
            subobs=obs[:n];submatrix={k:v[:n] for k,v in matrix.items()}
            if all(o['status']=='unusable' for o in subobs):curves.append({'model':key,'views':label,'status':'no_usable_photos'});continue
            raw=sorted((statistics.mean(v for v in values if v is not None),k) for k,values in submatrix.items())
            robust=fuse_scores(submatrix,subobs);hinted=fuse_scores(submatrix,subobs,penalties)
            curves.append({'model':key,'views':label,'input_photos':n,'independent_views':robust['independent_views'],'mean_rank':[k for _,k in raw].index(key)+1,'robust_rank':[v['template_id'] for v in robust['ranking']].index(key)+1,'hinted_rank':[v['template_id'] for v in hinted['ranking']].index(key)+1,'status':'ok'})
        full=fuse_scores(matrix,obs,penalties)
        row={'model':key,'photos':len(images),'usable':r['performance']['usable_photos'],'independent_views':r['performance']['independent_views'],'hint':HINTS.get(key,''),'top3':[c['template_id'] for c in full['ranking'][:3]],'rank':[x['template_id'] for x in full['ranking']].index(key)+1,'seconds':r['performance']['elapsed_seconds'],'excluded':r['analysis']['excluded_photos'],'conflicts':full['conflicting_photos'],'stable':full['winner_stable_count'],'loo_count':len(full['leave_one_group_out'])};rows.append(row);print(row,flush=True)
        (a.out/'progress.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    aggregates=[]
    for label in ['1','2','4','all']:
        subset=[v for v in curves if v['views']==label and v['status']=='ok'];record={'views':label,'models':len(subset)}
        for mode in ['mean','robust','hinted']:
            record[mode+'_top1']=sum(v[mode+'_rank']==1 for v in subset);record[mode+'_top3']=sum(v[mode+'_rank']<=3 for v in subset)
        aggregates.append(record)
    summary={'source_sha256':fingerprint,'scope':'68 prior development photos; fixed manifest order; reuse identical image fits for fair fusion comparisons','fit_records_reused':bool(a.reuse_fit_records),'hint_scope':'Explicit uncertain prior descriptions declared before evaluation; not automatic morphology recognition','total_photos':sum(r['photos'] for r in rows),'models':len(rows),'rows':rows,'curves':curves,'aggregates':aggregates,'limits':['No physical 3D ground truth; ranks refer to existing library templates.','More views are not guaranteed to improve every case; failures and regressions are retained.','Soft morphology priors may be wrong or incomplete; unknown text is preserved.']}
    (a.out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8');print(aggregates)

if __name__=='__main__':main()
