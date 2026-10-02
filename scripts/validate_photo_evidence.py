"""Stress photo evidence with repeats, blur, occlusion and uncertain/unknown hints."""
import argparse,base64,io,json,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from PIL import Image,ImageDraw,ImageFilter
from atlas.images import from_photos
from atlas.project import source_hash

def encode(im):
    b=io.BytesIO();im.save(b,format='PNG');return base64.b64encode(b.getvalue()).decode()

def main():
    p=argparse.ArgumentParser();p.add_argument('--renders',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True);rows=[];fingerprint=source_hash()
    for key in ['611','451','7518','6512']:
        first=Image.open(a.renders/(key+'-0.png')).convert('RGB');second=Image.open(a.renders/(key+'-1.png')).convert('RGB');x,y=encode(first),encode(second)
        baseline=from_photos([x,y]);repeated=from_photos([x,y]+[x]*6)
        assert baseline['ranking']==repeated['ranking'],'Identical repeats changed the ranking'
        assert repeated['fusion']['independent_views']==baseline['fusion']['independent_views']
        blurred=encode(first.filter(ImageFilter.GaussianBlur(5)));rblur=from_photos([x,y,blurred])
        occluded=first.copy();ImageDraw.Draw(occluded).rectangle((0,295,480,560),fill=(194,210,216));rpartial=from_photos([x,y,encode(occluded)],evidence={'coverage':['complete','complete','partial'],'morphology':'可能柱状或双锥，局部信息残缺，未知螺旋条纹'})
        assert len(rpartial['ranking'])==15,'Soft/unknown priors removed candidates'
        assert '螺旋条纹' in rpartial['morphology']['parsed']['unparsed']
        assert rpartial['observations'][2]['coverage']=='partial'
        assert rpartial['candidates'][0]['views'][2] is None or rpartial['candidates'][0]['views'][2]['fitMetric']=='partial_silhouette'
        def rank(result):return [r['template_id'] for r in result['ranking']].index(key)+1
        row={'template':key,'baseline_rank':rank(baseline),'repeated_rank':rank(repeated),'blur_rank':rank(rblur),'partial_and_uncertain_hint_rank':rank(rpartial),'baseline_groups':baseline['fusion']['independent_views'],'repeated_groups':repeated['fusion']['independent_views'],'sharp_quality':rblur['observations'][0]['quality_weight'],'blur_quality':rblur['observations'][2]['quality_weight'],'partial_status':rpartial['status'],'unknown_text':rpartial['morphology']['parsed']['unparsed']};rows.append(row);print(row,flush=True)
        (a.out/(key+'.json')).write_text(json.dumps({'baseline':baseline,'repeat':repeated,'blur':rblur,'partial':rpartial},ensure_ascii=False,indent=2),encoding='utf-8')
    result={'source_sha256':fingerprint,'scope':'synthetic stress, four known templates; no independent physical reconstruction accuracy claim','results':rows,'assertions':'duplicates leave ranking unchanged; partial and unknown evidence stay explicit; soft priors keep all templates'}
    (a.out/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':main()
