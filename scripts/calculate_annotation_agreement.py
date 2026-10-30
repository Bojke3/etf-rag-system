"""Calculate independent human agreement and calibration: A.json B.json."""
import argparse,json
import os
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
REVISION_DIR=Path(os.environ.get('RAG_REVISION_DIR', str(ROOT.parent/'ispravke')))
OUT=REVISION_DIR/'evaluacija'
def kappa(x,y,weighted=False):
    if len(x)!=len(y) or not x: raise ValueError('Paired nonempty labels required')
    labels=sorted(set(x)|set(y));n=len(x)
    distance=lambda a,b:(a-b)**2/25 if weighted else float(a!=b)
    observed=sum(distance(a,b) for a,b in zip(x,y))/n
    expected=sum(distance(a,b)*x.count(a)*y.count(b)/n**2 for a in labels for b in labels)
    return None if expected==0 else 1-observed/expected

def agreement(a,b,key):
    if a['annotator']==b['annotator']: raise ValueError('Two different annotators required')
    ids=sorted(key)
    for d in [a,b]:
        if d['protocol']!='telfor6821-v1' or set(d['grades'])!=set(ids): raise ValueError('Incomplete or mismatched sample')
        if not all(type(g['score']) is int and 0<=g['score']<=5 for g in d['grades'].values()): raise ValueError('Every response needs integer score 0-5')
    x,y=[[d['grades'][q]['score'] for q in ids] for d in [a,b]]
    report={'n':len(ids),'human_human':{'cohen_kappa':kappa(x,y),'quadratic_weighted_kappa':kappa(x,y,True),'exact_agreement':sum(i==j for i,j in zip(x,y))/len(ids)},'llm_calibration':{}}
    judge=np.array([key[q]['llm_score'] for q in ids])
    for d,v in [(a,x),(b,y)]:
        report['llm_calibration'][d['annotator']]={'mae':float(np.abs(judge-v).mean()),'signed_llm_minus_human':float((judge-v).mean()),'quadratic_weighted_kappa':kappa(v,judge.tolist(),True)}
    report['note']='Independent pre-adjudication labels. LLM decimals preserved in weighted kappa; no rounding. Descriptive stratified-sample calibration, not population error rate.'
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('a',type=Path);p.add_argument('b',type=Path);args=p.parse_args()
    read=lambda f:json.loads(f.read_text(encoding='utf-8'))
    result=agreement(read(args.a),read(args.b),read(OUT/'analysis_key_DO_NOT_OPEN_BEFORE_ANNOTATION.json'))
    (OUT/'agreement.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
