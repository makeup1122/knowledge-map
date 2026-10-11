#!/usr/bin/env python3
"""Merge route geometry + 历史 text into projects, then re-embed SEED_PROJECTS in index.html.
Re-run after updating /workspace/history-map/route-*-text-v1.json; missing text shows as 说明待补充.
Usage: python3 tools/merge-routes.py [--src /workspace/history-map]"""
import json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = sys.argv[sys.argv.index('--src')+1] if '--src' in sys.argv else '/workspace/history-map'

def rnd(c):
    if isinstance(c, (int, float)): return round(c, 5)
    return [rnd(x) for x in c]

CONF = {
  'fenhe': dict(file='route-fenhe', title='汾河流域（干流与主要支流）', toggle_label='汾河（干流与主要支流）',
    swatch='linear-gradient(90deg,#0d47a1,#1e88e5,#64b5f6)', main_length_km=716,
    facts=['汾河干流全长约 716 km（地理）'],
    intro_note='（注：干流上/中/下游分段长度来源不同，合计约695公里，与干流总长716公里不一致。）',
    style={'seg_fen_upper': ('#0d47a1', 5), 'seg_fen_middle': ('#1e88e5', 5), 'seg_fen_lower': ('#42a5f5', 5)},
    trib=('#4dd0e1', 2.5, 0.85),
    legend=[('干流·上游', '#0d47a1', 5, False), ('干流·中游', '#1e88e5', 5, False), ('干流·下游', '#42a5f5', 5, False), ('主要支流', '#4dd0e1', 2.5, False)]),
  'mingwall-sx': dict(file='route-mingwall-sx', title='山西明长城', toggle_label='明长城（山西段）',
    swatch='linear-gradient(90deg,#e65100,#ab47bc,#fbc02d)',
    style={'outer': ('#e65100', 4), 'inner': ('#ab47bc', 4), 'hebian': ('#fbc02d', 4)},
    legend=[('外长城', '#e65100', 4, False), ('内长城', '#ab47bc', 4, False), ('河边长城', '#fbc02d', 4, False), ('虚线 = 节点连线示意（墙线缺失处）', '#cccccc', 3, True)]),
}

def build(pid, c):
    g = json.load(open(f"{SRC}/{c['file']}-v1.json"))
    t = json.load(open(f"{SRC}/{c['file']}-text-v1.json"))
    tseg = {x['id']: x for x in t.get('segments', [])}
    tseg.update({x['slug']: x for x in t.get('segments', []) if x.get('slug')})
    tnode = {x['id']: x for x in t.get('nodes', [])}
    missing = []
    segs = []
    for s in g['segments']:
        s = dict(s)
        tx = tseg.get(s['id']) or tseg.get(s.get('text_slug') or '')
        if tx and tx.get('desc'):
            s['desc'] = tx['desc']; s['sources'] = tx.get('sources', [])
        else:
            missing.append(f"segment {s['id']} ({s.get('text_slug')})")
        if pid == 'fenhe':
            if s['line'] == '干流':
                s['color'], s['weight'] = c['style'][s['id']]; s['main_stem'] = True
            else:
                s['color'], s['weight'], s['opacity'] = c['trib']
        else:
            s['color'], s['weight'] = c['style'][s['line']]
            s['line'] = {'outer': '外长城', 'inner': '内长城', 'hebian': '河边长城'}[s['line']]
        for k in ('coords', 'schematic_coords'):
            if s.get(k): s[k] = rnd(s[k])
        segs.append(s)
    nodes = []
    for n in g['nodes']:
        n = dict(n)
        tx = tnode.get(n['id'])
        if tx and tx.get('desc'):
            n['desc'] = tx['desc']; n['sources'] = tx.get('sources', [])
        elif not n.get('point_id'):
            missing.append(f"node {n['id']} ({n['title']})")
        elif not tx:
            missing.append(f"node {n['id']} ({n['title']}, linked to point {n['point_id']})")
        if isinstance(n.get('source'), str) and not n.get('sources'):
            n['sources'] = [{'title': 'OSM / 坐标来源', 'url': n['source']}]
        nodes.append(n)
    pr = dict(id=pid, title=c['title'], toggle_label=c['toggle_label'], swatch=c['swatch'],
              intro=t['route'].get('intro', '') + c.get('intro_note', ''), intro_sources=t['route'].get('sources', []),
              nodes=nodes, segments=segs, sources=g.get('sources', []), caveat=g.get('caveat', ''),
              legend=[dict(label=a, color=b, weight=w, dash=d) for a, b, w, d in c['legend']],
              missing_text=missing)
    for k in ('main_length_km', 'facts'):
        if k in c: pr[k] = c[k]
    return pr

def main():
    ap = os.path.join(ROOT, 'all-points-v3.json')
    data = json.load(open(ap))
    projs = [p for p in data.get('projects', []) if p['id'] not in CONF]
    for pid, c in CONF.items():
        pr = build(pid, c); projs.append(pr)
        print(pid, 'missing text:', pr['missing_text'] or 'none')
    data['projects'] = projs
    json.dump(data, open(ap, 'w'), ensure_ascii=False, indent=2)
    ih = os.path.join(ROOT, 'index.html')
    s = open(ih).read()
    line = '    const SEED_PROJECTS = ' + json.dumps(projs, ensure_ascii=False) + ';'
    s, n = re.subn(r'^    const SEED_PROJECTS = .*;$', lambda m: line, s, count=1, flags=re.M)
    assert n == 1, 'SEED_PROJECTS line not found'
    open(ih, 'w').write(s)
    print('embedded', len(projs), 'projects')

main()
