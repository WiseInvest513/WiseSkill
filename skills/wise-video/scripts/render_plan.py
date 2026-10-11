#!/usr/bin/env python3
"""Compile an authored semantic render_spec; no topic-specific scene generation.
Source clock is absolute milliseconds. HTML clock begins at the requested range.
This compiler does not certify the plan's meaning or the acoustic alignment.
"""
import argparse, hashlib, html, json, math, re, shutil, subprocess, sys
from pathlib import Path

from srt_intake import probe_audio

HERE = Path(__file__).resolve().parent
BASE_KINDS = set('card banner product question shell image divider hero note arrow token text scope condition venue equity security tokenized currency negative diagram product-pane outline marker rail cursor'.split())
PROPS = set('x y scale scaleX scaleY rotation rotationX rotationY opacity backgroundColor color borderRadius strokeDashoffset transformOrigin'.split())
ID = re.compile(r'^[A-Za-z_][A-Za-z0-9_-]*$')

class Unsupported(ValueError): pass

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def jdump(path, data): Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
def safe_json(data): return json.dumps(data, ensure_ascii=False).replace('<', '\\u003c')
def esc(s): return html.escape(str(s), quote=True)
def num(x, label):
    if not isinstance(x, (int,float)) or isinstance(x,bool) or not math.isfinite(x): raise ValueError(label+' must be finite number')
    return x

def captions(path):
    if path.suffix.lower()=='.json':
        data=json.loads(path.read_text(encoding='utf-8')); data=data.get('captions',data) if isinstance(data,dict) else data
        out=[]
        for i,c in enumerate(data):
            out.append({'caption_id':c.get('caption_id',c.get('id',i+1)), 'start_ms':c.get('start_ms',c.get('startMs')), 'end_ms':c.get('end_ms',c.get('endMs')), 'text':c['text']})
    else:
        text=path.read_text(encoding='utf-8-sig').replace('\r\n','\n').replace('\r','\n')
        out=[]
        def ms(s):
            h,m,t=re.split(':',s); sec,frac=re.split('[,.]',t); return (int(h)*3600+int(m)*60+int(sec))*1000+int(frac)
        for block in re.split(r'\n[ \t]*\n',text.strip()):
            lines=block.splitlines()
            if len(lines)<3 or not lines[0].strip().isdigit(): raise Unsupported('SRT requires numbered UTF-8 blocks')
            times=re.fullmatch(r'(\d+:\d\d:\d\d[,.]\d{3})\s+-->\s+(\d+:\d\d:\d\d[,.]\d{3})',lines[1].strip())
            if not times: raise Unsupported('SRT timing/settings unsupported: '+lines[1])
            out.append({'caption_id':int(lines[0]),'start_ms':ms(times[1]),'end_ms':ms(times[2]),'text':'\n'.join(lines[2:])})
    seen=set()
    for c in out:
        if c['caption_id'] in seen: raise ValueError('Duplicate caption ID')
        seen.add(c['caption_id'])
        if num(c['start_ms'],'caption start')<0 or num(c['end_ms'],'caption end')<=c['start_ms']: raise ValueError('Invalid caption interval')
        if not isinstance(c['text'],str): raise ValueError('Caption text must be text')
    return out

def local_file(root, value):
    if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:',str(value)) and not re.match(r'^[A-Za-z]:[\\/]',str(value)):
        raise Unsupported('Remote assets unsupported; resolve locally first')
    p=Path(value);p=(root/p).resolve() if not p.is_absolute() else p.resolve()
    if not p.is_file(): raise FileNotFoundError(p)
    return p

def copy_asset(src, out, prefix, ledger):
    digest=sha(src); dest='assets/'+prefix+'-'+digest[:12]+src.suffix.lower()
    shutil.copy2(src,out/dest); ledger.append({'source':str(src),'path':dest,'sha256':digest})
    return dest

def rewrite_media(markup, root, out, prefix, ledger):
    def rep(m):
        src=local_file(root,m[2]); dest=copy_asset(src,out,prefix,ledger)
        return m[1]+dest+m[3]
    return re.sub(r'(\bsrc=["\'])([^"\']+)(["\'])',rep,markup)

def rewrite_css(css, root, out, prefix, ledger):
    """Freeze local CSS resources alongside HTML media, including custom fonts."""
    def rep(m):
        value=m[2].strip()
        if value.startswith(('#', 'data:')): return m[0]
        src=local_file(root,value); dest=copy_asset(src,out,prefix,ledger)
        return 'url("'+dest+'")'
    return re.sub(r"url\(\s*(['\"]?)(.*?)\1\s*\)",rep,css,flags=re.I)

def background(path,out,ledger,start,duration):
    if not path: return '', '', ''
    path=path/'index.html' if path.is_dir() else path
    if path.suffix.lower()!='.html':
        src=copy_asset(path,out,'background',ledger)
        return f'<img class="bg" src="{src}" alt="">','',''
    s=path.read_text(encoding='utf-8'); css=re.search(r'<style>(.*?)</style>',s,re.S)
    body=re.search(r'<body>\s*<div[^>]*data-composition-id[^>]*>(.*?)</div>\s*<script>',s,re.S)
    scripts=re.findall(r'<script(?:\s[^>]*)?>(.*?)</script>',s,re.S)
    js='\n'.join(x for x in scripts if x.strip())
    # This adapter supports the approved deterministic draw(t) template contract.
    if not body or not css or 'function draw(t)' not in js or 'const state=' not in js:
        raise Unsupported('HTML background must expose approved draw(t) template contract; arbitrary scripts unsupported')
    pre,tail=js.split('const state=',1)
    load=re.search(r"surface\.addEventListener\('load',upload\);if\(surface\.complete&&surface\.naturalWidth\)upload\(\);",tail)
    if not load: raise Unsupported('Unsupported background readiness contract')
    js=pre+f'window.__backgroundDraw=draw;draw({start/1000});'+load[0]
    ledger.append({'source':str(path),'sha256':sha(path),'role':'background-template'})
    return rewrite_media(body[1],path.parent,out,'background',ledger),rewrite_css(css[1],path.parent,out,'background',ledger),js

def intro(path,at,out,ledger):
    path=path/'index.html' if path.is_dir() else path
    s=path.read_text(encoding='utf-8'); css=re.search(r'<style>(.*?)</style>',s,re.S)
    match=re.search(r'(<div class="intro-copy">.*?)<div class="clip caption"',s,re.S)
    cues=re.search(r'const introCues=(\[.*?\]);for',s,re.S)
    dur=re.search(r'data-duration="([\d.]+)"',s)
    if not all([css,match,cues,dur]): raise Unsupported('Intro template requires intro-copy markup and JSON introCues')
    intro_css=css[1][css[1].find('@font-face'):] if '@font-face' in css[1] else css[1]
    intro_css=rewrite_css(intro_css,path.parent,out,'intro',ledger)
    actions=[]
    for c in json.loads(cues[1]):
        actions.append({'target':c['target'],'op':'fromTo','at_ms':at+c['at']*1000,'duration_ms':c['duration']*1000,'initial':c['from'],'values':c['to'],'ease':c.get('ease','power2.out'),'scene_id':'explicit-intro'})
    ledger.append({'source':str(path),'sha256':sha(path),'role':'explicit-intro-template'})
    return rewrite_media(match[1]+'</div>',path.parent,out,'intro',ledger),intro_css,actions,float(dur[1])*1000

# A single paused timeline drives a deterministic absolute source clock. Property
# tracks retain source history, so starting midway through a scene loses no state.
RUNTIME = r'''
const cues=__CUES__; const introCues=__INTRO_CUES__; const sourceStart=__START__, sourceDuration=__DURATION__;
const groups=new Map();
for(const local of [...cues,...introCues]){const c={...local,at_ms:local.at_ms+sourceStart};if(!groups.has(c.target))groups.set(c.target,[]);groups.get(c.target).push(c);}
const tracks=[];
const sample=(events,t,base)=>{let v=base;for(const e of events){if(t<e.at)break;const p=e.dur?Math.max(0,Math.min(1,(t-e.at)/e.dur)):1;v=e.key==='transformOrigin'?e.to:gsap.utils.interpolate(e.from,e.to,e.ease(p));}return v;};
for(const [id,actions] of groups){
 const node=document.getElementById(id);if(!node)throw new Error('Missing target '+id);
 const byProp={};actions.sort((a,b)=>a.at_ms-b.at_ms);
 for(const c of actions){
  const initial=c.initial||{}, values=c.values||{};
  for(const key of new Set([...Object.keys(initial),...Object.keys(values)])){
   if(!byProp[key])byProp[key]={base:gsap.getProperty(node,key),events:[]};
   const tr=byProp[key], from=key in initial?initial[key]:sample(tr.events,c.at_ms,tr.base);
   if(typeof gsap.parseEase(c.ease||'power2.inOut')!=='function')throw new Error('Unsupported easing '+c.ease);
   tr.events.push({key,at:c.at_ms,dur:c.duration_ms,from,to:key in values?values[key]:from,ease:gsap.parseEase(c.ease||'power2.inOut')});
  }
 }
 tracks.push({node,byProp});
}
function paint(t){
 for(const {node,byProp} of tracks){const values={};for(const [key,tr] of Object.entries(byProp))values[key]=sample(tr.events,t,tr.base);gsap.set(node,values);}
 if(window.__backgroundDraw)window.__backgroundDraw(t/1000);
}
const clock={t:sourceStart};const tl=gsap.timeline({paused:true});
tl.to(clock,{t:sourceStart+sourceDuration,duration:sourceDuration/1000,ease:'none',onUpdate:()=>paint(clock.t)},0);
paint(sourceStart);window.__timelines=window.__timelines||{};window.__timelines['srt-video']=tl;
window.__renderPlan={sourceStartMs:sourceStart,durationMs:sourceDuration,cues};
'''

def compile_plan(args):
    for key in ['source_start_ms','duration_ms']: num(getattr(args,key),key)
    start=args.source_start_ms;end=start+args.duration_ms
    if start<0 or args.duration_ms<=0: raise ValueError('Range must have nonnegative start and positive duration')
    if bool(args.intro_template)!=(args.intro_at_ms is not None): raise ValueError('Intro requires both --intro-template and --intro-at-ms')
    if args.audio and args.audio_offset_ms is None: raise ValueError('--audio requires explicit --audio-offset-ms; 0 means source/audio clocks match')
    if args.audio_offset_ms is not None and not args.audio: raise ValueError('--audio-offset-ms requires --audio')
    p=json.loads(args.plan.read_text(encoding='utf-8'));spec=p['render_spec'];caps=captions(args.captions)
    selected=[c for c in caps if c['start_ms']<end and c['end_ms']>start]
    if not selected: raise ValueError('No captions intersect requested range')
    scope=set(p.get('scope_caption_ids',[]))
    if scope and any(c['caption_id'] not in scope for c in selected): raise ValueError('Requested caption outside authored plan scope')
    out=args.out.resolve()
    if out.exists() and any(out.iterdir()): raise ValueError('Output must be empty; preserve prior versions')
    out.mkdir(parents=True,exist_ok=True);(out/'assets').mkdir(exist_ok=True)
    ledger=[];asset_data=json.loads(args.asset_index.read_text(encoding='utf-8'));asset_data=asset_data.get('assets',asset_data) if isinstance(asset_data,dict) else asset_data
    idx={a['asset_id']:a for a in asset_data};em={e['id']:e for e in p.get('entities',[])};asset_paths={}
    def resolve_aid(aid):
        if aid in asset_paths:return asset_paths[aid]
        if aid not in idx:raise ValueError('Unresolved asset ID '+aid)
        item=idx[aid];src=local_file(args.asset_root,item['path'])
        if item.get('sha256') and sha(src)!=item['sha256']:raise ValueError('Asset hash mismatch '+aid)
        if not ID.fullmatch(aid):raise ValueError('Invalid asset ID '+aid)
        dest='assets/'+aid+src.suffix.lower();shutil.copy2(src,out/dest);ledger.append({'asset_id':aid,'source':str(src),'path':dest,'sha256':sha(src)})
        asset_paths[aid]=dest;return dest
    gsap=args.gsap
    if not gsap or not gsap.is_file():raise ValueError('Local GSAP not found; pass --gsap')
    shutil.copy2(gsap,out/'assets/gsap.min.js');ledger.append({'source':str(gsap),'path':'assets/gsap.min.js','sha256':sha(gsap)})
    bg,bgcss,bgjs=background(args.background,out,ledger,start,args.duration_ms)
    if not args.background and spec.get('background_asset_id'):bg=f'<img class="bg" src="{resolve_aid(spec["background_asset_id"])}" alt="">'
    css=(HERE/'style-vocabulary.css').read_text(encoding='utf-8')+bgcss+p.get('render_css','');body=[bg];allcues=[];introcues=[];ids=set();intro_slot=None
    if args.intro_template:
        mark,icss,icues,idur=intro(args.intro_template,args.intro_at_ms,out,ledger);css+=icss
        intro_slot=(args.intro_at_ms,args.intro_at_ms+idur)
        if intro_slot[0]<end and intro_slot[1]>start:
            intro_scene=next((s['id'] for s in spec['scenes'] if not s.get('objects') and abs(s['start_ms']-intro_slot[0])<2 and abs(s['end_ms']-intro_slot[1])<2),'explicit-intro')
            st=max(start,intro_slot[0]);en=min(end,intro_slot[1]);body.append(f'<section class="clip scene" id="{intro_scene}" data-start="{(st-start)/1000}" data-duration="{(en-st)/1000}" data-track-index="2">{mark}</section>');introcues.extend(dict(c,scene_id=intro_scene,at_ms=round(c['at_ms']-start),duration_ms=round(c['duration_ms'])) for c in icues)
            ids.update(re.findall(r'\bid="([^"]+)"',mark))
    custom_classes=set(re.findall(r'\.([A-Za-z_][A-Za-z0-9_-]*)',p.get('render_css','')))
    for scene in spec['scenes']:
        sid=scene['id'];ss=num(scene['start_ms'],'scene start');se=num(scene['end_ms'],'scene end')
        if not ID.fullmatch(sid) or se<=ss:raise ValueError('Invalid scene')
        if se<=start or ss>=end:continue
        if not scene.get('objects'):
            if intro_slot and abs(ss-intro_slot[0])<2 and abs(se-intro_slot[1])<2:continue
            raise Unsupported('Empty scene '+sid+' requires an explicitly supplied matching intro or authored objects')
        content=f'<div class="title">{esc(scene.get("title",""))}</div>';objectids=set()
        for o in scene['objects']:
            unsupported=set(o)-{'id','kind','x','y','w','h','text','entity_id','src','svg','role'}
            if unsupported:raise Unsupported('Unsupported object fields '+str(unsupported))
            if not ID.fullmatch(o['id']):raise ValueError('Invalid object ID')
            oid=sid+'-'+o['id']
            if oid in ids:raise ValueError('Duplicate DOM ID '+oid)
            ids.add(oid);objectids.add(o['id'])
            if o['kind'] not in BASE_KINDS|custom_classes:raise Unsupported('Unsupported object kind '+o['kind']+'; provide render_css')
            for k in ['x','y','w','h']:num(o[k],k)
            if o['w']<=0 or o['h']<=0:raise ValueError('Object size must be positive')
            media=''
            if o.get('entity_id'):
                ent=em[o['entity_id']]
                if not ent.get('asset_id'):raise ValueError('Entity asset unresolved '+o['entity_id'])
                media=f'<img src="{resolve_aid(ent["asset_id"])}" alt="{esc(ent["name"])}">'
            if 'src' in o:
                if media:raise ValueError('Both entity and src on '+oid)
                media=f'<img src="{copy_asset(local_file(args.asset_root,o["src"]),out,"object",ledger)}" alt="">'
            svg=o.get('svg','')
            if re.search(r'<script|\bon\w+\s*=|(?:href|src)\s*=',svg,re.I):raise Unsupported('SVG scripting/external references unsupported')
            content+=f'<div id="{oid}" class="object {esc(o["kind"])}" style="left:{o["x"]}px;top:{o["y"]}px;width:{o["w"]}px;height:{o["h"]}px">{media}{svg}<div class="label">{esc(o.get("text",""))}</div></div>'
        st=max(start,ss);en=min(end,se);body.append(f'<section class="clip scene" id="{sid}" data-start="{(st-start)/1000}" data-duration="{(en-st)/1000}" data-track-index="1">{content}</section>')
        for c in scene['actions']:
            if c['target'] not in objectids:raise ValueError('Unknown target '+c['target'])
            if c['op'] not in ['to','fromTo']:raise Unsupported('Unsupported action '+c['op'])
            if not ss<=num(c['at_ms'],'action time')<se or num(c['duration_ms'],'duration')<0:raise ValueError('Invalid action time')
            props=set(c.get('initial',{}))|set(c.get('values',{}))
            if props-PROPS:raise Unsupported('Unsupported action properties '+str(props-PROPS))
            if c['op']=='fromTo' and not c.get('initial'):raise ValueError('fromTo needs initial state')
            allcues.append(dict(c,target=sid+'-'+c['target'],scene_id=sid,at_ms=c['at_ms']-start))
    localcaps=[]
    for c in selected:
        st=max(start,c['start_ms']);en=min(end,c['end_ms']);lc=dict(c,source_start_ms=c['start_ms'],source_end_ms=c['end_ms'],start_ms=st-start,end_ms=en-start);localcaps.append(lc)
        body.append(f'<div class="clip caption" id="caption-{esc(c["caption_id"])}" data-start="{(st-start)/1000}" data-duration="{(en-st)/1000}" data-track-index="8" data-layout-allow-caption-zone>{esc(c["text"])}</div>')
    audio_info={'status':'silent_srt_only'}
    if args.audio:
        media_start=start+args.audio_offset_ms
        if media_start<0:raise ValueError('Audio media start cannot be negative')
        audio_duration=probe_audio(args.audio,args.ffprobe)['duration_ms']
        if audio_duration is None:raise ValueError('Audio duration unavailable; cannot verify range coverage')
        if media_start+args.duration_ms>audio_duration+50:raise ValueError('Audio does not cover requested range at confirmed offset')
        src=copy_asset(args.audio,out,'voice',ledger)
        body.append(f'<audio id="voice" src="{src}" data-start="0" data-duration="{args.duration_ms/1000}" data-media-start="{media_start/1000}" data-track-index="10" data-volume="1"></audio>')
        audio_info={'status':'offset_explicit','offset_ms':args.audio_offset_ms,'media_start_ms':media_start,'acoustic_alignment_verified':False}
    js=RUNTIME.replace('__CUES__',safe_json(allcues)).replace('__INTRO_CUES__',safe_json(introcues)).replace('__START__',str(start)).replace('__DURATION__',str(args.duration_ms))
    if bgjs:js='(()=>{'+bgjs+'})();\n'+js
    doc=f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><script src="assets/gsap.min.js"></script><style>{css}</style></head><body><div id="main" data-composition-id="srt-video" data-width="1920" data-height="1080" data-duration="{args.duration_ms/1000}" data-fps="30">'+''.join(body)+'</div><script>'+js+'</script></body></html>'
    (out/'index.html').write_text(doc, encoding='utf-8');jdump(out/'hyperframes.json',{'name':'srt-video','version':'1.0.0'})
    jdump(out/'captions.local.json',localcaps);jdump(out/'cue_sheet.json',{'plan_sha256':sha(args.plan),'time_basis':'composition local milliseconds','source_start_ms':start,'duration_ms':args.duration_ms,'cues':allcues,'intro_cues':introcues})
    provenance={'compiler_sha256':sha(__file__),'plan_sha256':sha(args.plan),'captions_sha256':sha(args.captions),'source_captions_sha256':sha(args.source_srt or args.captions),'html_sha256':sha(out/'index.html'),'source_start_ms':start,'duration_ms':args.duration_ms,'audio':audio_info,'assets':ledger,'caption_count':len(selected),'semantic_review':'required separately; compilation is not semantic approval'}
    jdump(out/'provenance.json',provenance);print(json.dumps({'out':str(out),'captions':len(selected),'actions':len(allcues),'audio':audio_info},ensure_ascii=False))

def parser():
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ['plan','captions','asset-index','asset-root','out']:p.add_argument('--'+arg,type=Path,required=True)
    for arg in ['background','audio','intro-template','gsap','source-srt']:p.add_argument('--'+arg,type=Path)
    p.add_argument('--source-start-ms',type=int,required=True);p.add_argument('--duration-ms',type=int,required=True)
    p.add_argument('--audio-offset-ms',type=int);p.add_argument('--intro-at-ms',type=int)
    p.add_argument('--ffprobe',help='path to ffprobe; otherwise searches PATH')
    return p
if __name__=='__main__':
    try:compile_plan(parser().parse_args())
    except (ValueError,KeyError,FileNotFoundError,subprocess.CalledProcessError) as e: print('ERROR: '+str(e),file=sys.stderr);sys.exit(2)
