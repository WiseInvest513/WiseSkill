#!/usr/bin/env python3
"""Build a six-second synthetic runtime fixture; never uses a historical episode."""
import argparse
import json
import math
from pathlib import Path
import struct
import subprocess
import sys
import wave


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skill-root', type=Path, default=Path(__file__).resolve().parents[1] / 'skills/wise-video')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--gsap', type=Path)
    args = parser.parse_args()
    skill, out = args.skill_root.resolve(), args.out.resolve()
    gsap = args.gsap or skill / 'assets/background/assets/gsap.min.js'
    if out.exists():
        parser.error('Use a new output directory; existing work is never overwritten')
    if not gsap.is_file():
        parser.error('Prepare GSAP with npm ci and npm run prepare-assets first')
    out.mkdir(parents=True)
    captions = [{'caption_id': 1, 'start_ms': 0, 'end_ms': 3000, 'text': '运行验证：圆点从起点向终点移动。'},
                {'caption_id': 2, 'start_ms': 3000, 'end_ms': 6000, 'text': '这是合成样例，不是本期内容或声音。'}]
    objects = [dict(id='heading', kind='text', text='运行环境验证 / SYNTHETIC TEST', x=300,y=220,w=1320,h=100),
               dict(id='start',kind='text',text='起点',x=430,y=650,w=200,h=80),
               dict(id='end',kind='text',text='终点',x=1290,y=650,w=200,h=80),
               dict(id='route',kind='rail',text='',x=530,y=530,w=860,h=8),
               dict(id='dot',kind='token',text='',x=490,y=490,w=88,h=88)]
    plan = {'version':1,'scope_caption_ids':[1,2], 'entities':[], 'render_css':'.object{opacity:1}.rail{background:#aa8750;border:0}.token{background:#203d51;border:7px solid #c8a26a;border-radius:50%}.text{font-size:44px;color:#203d51;font-weight:650}.caption{font-size:32px}',
            'render_spec':{'scenes':[{'id':'transfer','start_ms':0,'end_ms':6000,'objects':objects,
            'actions':[{'target':'dot','op':'fromTo','at_ms':500,'duration_ms':2200,'initial':{'x':0},'values':{'x':860},'ease':'power2.inOut'},
                       {'target':'end','op':'fromTo','at_ms':2700,'duration_ms':350,'initial':{'color':'#203d51'},'values':{'color':'#aa8750'},'ease':'none'}]}]}}
    for name,data in [('plan.json',plan),('captions.json',captions),('asset-index.json',[])]:
        (out/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    # Short pulses at 0/3 seconds let reviewers distinguish a real audio stream from a silent mux.
    rate = 48000
    with wave.open(str(out/'synthetic-test.wav'),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate)
        samples=[]
        for i in range(rate*6):
            t=i/rate;on=(0.15<=t<0.35 or 3.15<=t<3.35)
            samples.append(struct.pack('<h',int(3500*math.sin(2*math.pi*440*t)) if on else 0))
        w.writeframes(b''.join(samples))
    cmd=[sys.executable,str(skill/'scripts/render_plan.py'),'--plan',str(out/'plan.json'),'--captions',str(out/'captions.json'),'--asset-index',str(out/'asset-index.json'),'--asset-root',str(out),'--source-start-ms','0','--duration-ms','6000','--background',str(skill/'assets/background'),'--gsap',str(gsap),'--audio',str(out/'synthetic-test.wav'),'--audio-offset-ms','0','--out',str(out/'composition')]
    subprocess.run(cmd,check=True)
    (out/'README.txt').write_text('Synthetic 6-second runtime fixture. Not an approved production. Audio pulses at 0.15 and 3.15 seconds. Inspect frames, font glyphs, backdrop and motion; no claim of artistic or semantic production approval.\n',encoding='utf-8')
    print('Created '+str(out))


if __name__=='__main__':
    main()
