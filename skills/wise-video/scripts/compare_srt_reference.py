#!/usr/bin/env python3
"""Read-only SRT/reference comparison. Emits candidates, never edits source text."""
import argparse, difflib, hashlib, json, re
from pathlib import Path

def normalized(text):
    return ''.join(c.lower() for c in text if c.isalnum())

def compare(srt, reference):
    raw=srt.read_text(encoding='utf-8-sig')
    cues=[]; stream=[]; mapping=[]
    for block in re.split(r'\n\s*\n', raw.strip()):
        lines=block.splitlines()
        if len(lines)<3 or not lines[0].isdigit() or ' --> ' not in lines[1]:
            raise ValueError('Invalid SRT block; preserve original and inspect it')
        cue={'caption_id':int(lines[0]),'time':lines[1],'text':'\n'.join(lines[2:])}
        cues.append(cue)
        chunk=normalized(cue['text']);stream.append(chunk);mapping.extend([cue['caption_id']]*len(chunk))
    source=''.join(stream);target=normalized(reference.read_text(encoding='utf-8-sig'))
    differences=[]
    for kind,a,b,c,d in difflib.SequenceMatcher(None,source,target,autojunk=False).get_opcodes():
        if kind=='equal':continue
        ids=sorted(set(mapping[a:b])) if b>a else [mapping[min(a,len(mapping)-1)]] if mapping else []
        differences.append({'kind':kind,'caption_ids':ids,'source':source[a:b],
            'reference':target[c:d],'source_context':source[max(0,a-20):b+20]})
    return {'mode':'read_only_candidates','source':str(srt.resolve()),'reference':str(reference.resolve()),
        'cue_count':len(cues),'first_time':cues[0]['time'] if cues else None,
        'last_time':cues[-1]['time'] if cues else None,'difference_count':len(differences),
        'normalization':'ignore punctuation/spacing/case only; numeric notation remains distinct',
        'source_sha256':hashlib.sha256(srt.read_bytes()).hexdigest(),
        'reference_sha256':hashlib.sha256(reference.read_bytes()).hexdigest(),
        'differences':differences}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('srt',type=Path);parser.add_argument('reference',type=Path)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();report=compare(args.srt,args.reference)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({'cue_count':report['cue_count'],'differences':report['difference_count'],'report':str(args.out)},ensure_ascii=False))
