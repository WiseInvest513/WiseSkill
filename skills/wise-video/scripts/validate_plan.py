#!/usr/bin/env python3
"""Read-only semantic planning preflight. Does not judge natural-language truth."""
import argparse,json
from pathlib import Path

def validate(p,captions):
    errors=[]
    def need(ok,msg):
        if not ok: errors.append(msg)
    need(p.get('version')==1,'unsupported plan version')
    scope=p.get('scope_caption_ids',[]);source={c['caption_id']:c for c in captions}
    need(bool(scope) and len(scope)==len(set(scope)),'scope empty or duplicate')
    need(set(scope)<=set(source),'scope contains unknown captions')
    entities=p.get('entities',[]);em={e.get('id'):e for e in entities}
    need(len(em)==len(entities) and None not in em,'duplicate or missing entity ID')
    for e in entities:
        n=e.get('id');r=e.get('representation')
        need(bool(e.get('name')) and isinstance(e.get('identity_required'),bool),f'{n}: entity classification missing')
        need(r in ['icon','text','omit'],f'{n}: representation invalid')
        if r=='icon':need(e.get('asset_status')=='ready' and bool(e.get('asset_id')),f'{n}: unresolved visual asset')
        if r in ['text','omit']:
            need(bool(e.get('reason')),f'{n}: fallback/omission needs reason')
            if e.get('identity_required'):need(e.get('fallback_approved') is True and bool(e.get('fallback_evidence')),f'{n}: identity fallback not authorized')
    beats=p.get('beats',[]);bm={b.get('id'):b for b in beats}
    need(bool(beats) and len(bm)==len(beats) and None not in bm,'duplicate or missing beat ID')
    kinds={'identity','relation_change','quantity_change','transfer','comparison','hold'}
    properties={'opacity','scale','position','distance','membership','count','direction','unit','grouping','focus','labels'}
    used=set()
    for b in beats:
        n=b.get('id');ids=b.get('source_caption_ids',[]);used.update(b.get('entity_ids',[]))
        need(bool(ids) and set(ids)<=set(scope),f'{n}: source outside scope or empty')
        need(set(b.get('entity_ids',[]))<=set(em),f'{n}: unknown entity')
        if ids and all(i in source for i in ids):need(b.get('text')==''.join(source[i]['text'] for i in ids),f'{n}: source text mismatch')
        need(b.get('kind') in kinds,f'{n}: invalid semantic kind')
        for key in ['meaning','before','after','action','acceptance']:need(bool(b.get(key)),f'{n}: missing {key}')
        changes=set(b.get('changes',[]));need(changes<=properties,f'{n}: unsupported change property')
        if b.get('kind')=='hold':need(bool(b.get('hold_reason')),f'{n}: hold needs reason')
        else:need(b.get('before')!=b.get('after'),f'{n}: unchanged state')
        if b.get('kind') in {'relation_change','quantity_change','transfer','comparison'}:
            need(bool(changes-{'opacity','scale'}),f'{n}: semantic change reduced to cosmetic motion')
        if b.get('kind')=='quantity_change':need(bool(changes&{'membership','count'}),f'{n}: quantity needs member/count change')
    need(set(em)<=used,'entities not mapped to any beat')
    cov=p.get('coverage',[]);cm={r.get('caption_id'):r for r in cov}
    need(len(cm)==len(cov) and set(cm)==set(scope),'coverage does not match full scope')
    for cid,r in cm.items():
        refs=r.get('beat_ids',[])
        need(bool(refs) or bool(r.get('hold_reason')),f'caption {cid}: unexplained visual gap')
        for ref in refs:need(ref in bm and cid in bm[ref].get('source_caption_ids',[]),f'caption {cid}: broken beat reference')
    return errors

def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('plan',type=Path);a.add_argument('--captions',required=True,type=Path);args=a.parse_args()
    try:errors=validate(json.loads(args.plan.read_text(encoding='utf-8')),json.loads(args.captions.read_text(encoding='utf-8')))
    except (ValueError,KeyError,TypeError,OSError) as e:errors=['invalid input: '+str(e)]
    print(json.dumps({'ok':not errors,'errors':errors,'limit':'structural planning check only; human semantic review and rendered evidence still required'},ensure_ascii=False,indent=2))
    return bool(errors)
if __name__=='__main__':raise SystemExit(main())
