"""Calculate bootstrap confidence intervals and prepare blinded human annotation forms."""
import ast, hashlib, html, json, random
import os
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
REVISION_DIR=Path(os.environ.get('RAG_REVISION_DIR', str(ROOT.parent/'ispravke')))
OUT=REVISION_DIR/'evaluacija'
CELLS={'Mistral flat':'c105','Mistral hierarchical':'c107','Qwen flat':'c205_api','Qwen hierarchical':'c207_api','Llama flat':'c305_api','Llama hierarchical':'c307_api'}
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def write(p,v): p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def ci(v): return list(map(float,np.quantile(v,[.025,.975])))
def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT/'ocenjivac_A.html').exists(): raise SystemExit('Annotation forms already exist; refusing to overwrite frozen sample.')
    cells={};manifest=[]
    for label,code in CELLS.items():
        cells[label]=[]
        for rep in range(1,6):
            folder=ROOT/'benchmarking/runs'/f'dev_combined_{code}_r{rep:02}'
            ap=folder/'answers.jsonl'; digest=hashlib.sha256(ap.read_bytes()).hexdigest()
            answers={a['id']:a for a in map(json.loads,ap.read_text(encoding='utf-8').splitlines())}
            candidates=[]
            for p in sorted((folder/'scores').glob('*.json')):
                s=read(p)
                if s.get('evaluation_protocol')!='reference_metrics_v5' or s.get('judge',{}).get('model')!='claude-sonnet-5': continue
                rows=s.get('results',[])
                if len(rows)==60 and s.get('answers_sha256')==digest and all(r.get('scores',{}).get('llm_judge',{}).get('score') is not None for r in rows): candidates.append((p,rows))
            if len(candidates)!=1: raise ValueError(f'{folder.name}: expected one matching complete v5 score file; found {len(candidates)}')
            p,rows=candidates[0];scores={r['id']:float(r['scores']['llm_judge']['score']) for r in rows}
            assert len(answers)==60 and set(answers)==set(scores) and all(a['status']=='success' for a in answers.values())
            cells[label].append((answers,scores))
            manifest.append({'cell':label,'run':folder.name,'answers_sha256':digest,'scores_file':str(p.relative_to(ROOT)),'scores_sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    rng=np.random.default_rng(6821);draw=rng.integers(0,60,(10000,60)); means={}
    report={'seed':6821,'replicates':10000,'method':'Percentile bootstrap over questions. Five runs averaged within each question. Paired question resampling for hierarchical-minus-flat differences. Marginal 95% intervals; no multiplicity correction.','generation':{},'paired':{},'retrieval':{}}
    ids=sorted(next(iter(cells.values()))[0][0])
    for label,runs in cells.items():
        m=np.array([[s[q] for q in ids] for a,s in runs]);means[label]=m.mean(axis=0)
        report['generation'][label]={'mean':float(m.mean()),'run_mean_sd':float(m.mean(axis=1).std(ddof=1)),'ci95':ci(means[label][draw].mean(axis=1))}
    for model in ['Mistral','Qwen','Llama']:
        d=means[model+' hierarchical']-means[model+' flat'];report['paired'][model]={'delta':float(d.mean()),'ci95':ci(d[draw].mean(axis=1))}
    for run in read(ROOT/'benchmarking/retrieval_reports/retrieval_2x2_reviewed_v2.json')['runs']:
        rows=sorted([q for q in run['questions'] if q['scope']=='answer'],key=lambda q:q['question_id']);assert len(rows)==52
        rd=rng.integers(0,52,(10000,52));v=np.array([[q['delivered_coverage'],float(q['complete'])] for q in rows])
        ranks=[[r['delivered_locations']['complete_by_rank'] for r in q['requirements'] if r['delivered']] for q in rows];rs=np.array([sum(x) for x in ranks]);rc=np.array([len(x) for x in ranks])
        report['retrieval'][Path(run['run']).name]={'coverage':{'mean':float(v[:,0].mean()),'ci95':ci(v[rd,0].mean(axis=1))},'complete_rate':{'mean':float(v[:,1].mean()),'ci95':ci(v[rd,1].mean(axis=1))},'found_rank':{'mean':float(rs.sum()/rc.sum()),'ci95':ci(rs[rd].sum(axis=1)/rc[rd].sum(axis=1))}}
    write(OUT/'statistics.json',report);write(OUT/'source_manifest.json',manifest)
    lines=['# Statistika za reviziju TELFOR rada','',report['method'],'','| Kombinacija | Srednja ocena | 95% CI |','|---|---:|---|']
    for label,r in report['generation'].items(): lines.append(f"| {label} | {r['mean']:.3f} | [{r['ci95'][0]:.3f}, {r['ci95'][1]:.3f}] |")
    lines+=['','| Model | Hierarchical minus flat | 95% CI |','|---|---:|---|']
    for label,r in report['paired'].items(): lines.append(f"| {label} | {r['delta']:.3f} | [{r['ci95'][0]:.3f}, {r['ci95'][1]:.3f}] |")
    lines+=['','Retrieval intervals resample 52 questions and retain evidence units within each question. Found-rank is a ratio over found evidence. Deterministic retrieval repetitions are not independent samples.','','| Retrieval | Coverage CI | Complete-rate CI | Found-rank CI |','|---|---|---|---|']
    for label,r in report['retrieval'].items(): lines.append('| '+label+' | '+' | '.join('[{:.3f}, {:.3f}]'.format(*r[k]['ci95']) for k in ['coverage','complete_rate','found_rank'])+' |')
    (OUT/'statistics.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    rand=random.Random(6821);first=next(iter(cells.values()))[0][0];groups={}
    for q,a in sorted(first.items()): groups.setdefault(a['expected_behavior'],[]).append(q)
    for g in groups.values(): rand.shuffle(g)
    records=[];key={}
    for cell,(label,runs) in enumerate(cells.items()):
        chosen=[groups['answer'][(cell*17+i)%len(groups['answer'])] for i in range(17)]+[groups[b][cell%len(groups[b])] for b in ['partial_answer','abstain','clarify']]
        for i,q in enumerate(chosen):
            rep=i%5;a,s=runs[rep];bid=hashlib.sha256(f'6821:{label}:{q}:{rep}'.encode()).hexdigest()[:12]
            records.append({'blind_id':bid,**{k:a[q][k] for k in ['question','expected_behavior','expected_answer','required_facts','disallowed_claims','actual_answer']}})
            key[bid]={'cell':label,'run':f'dev_combined_{CELLS[label]}_r{rep+1:02}','question_id':q,'llm_score':s[q]}
    assert len(key)==120
    module=ast.parse((ROOT/'src/evaluation/llm_judge.py').read_text(encoding='utf-8'))
    rubric=next(ast.literal_eval(n.value) for n in module.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='JUDGE_SYSTEM' for t in n.targets))
    template=(REVISION_DIR/'annotation_form_template.html').read_text(encoding='utf-8')
    for who in ['A','B']:
        order=list(records);random.Random(6821+ord(who)).shuffle(order)
        page=template.replace('__DATA__',json.dumps(order,ensure_ascii=False).replace('<','\\u003c')).replace('__RUBRIC__',html.escape(rubric)).replace('__WHO__',who)
        (OUT/f'ocenjivac_{who}.html').write_text(page,encoding='utf-8')
    write(OUT/'analysis_key_DO_NOT_OPEN_BEFORE_ANNOTATION.json',key)
    write(OUT/'sampling_protocol.json',{'seed':6821,'total':120,'per_cell':20,'per_cell_behaviors':{'answer':17,'partial_answer':1,'abstain':1,'clarify':1},'per_cell_repetitions':{str(i):4 for i in range(1,6)},'distinct_questions':len({v['question_id'] for v in key.values()}),'instructions':'Two authors score independently using rubric v5. Freeze both independent sets before discussion. Model, strategy, run, judge score and rationale are hidden. Clarification is deliberately overrepresented; pooled calibration is descriptive for this sample, not an unbiased estimate of all 1800 responses. This evaluates reference-based quality, not grounding.'})
    print(json.dumps(report['paired'],indent=2));print('Prepared 120 blinded responses in each of two forms.')
if __name__=='__main__': main()
