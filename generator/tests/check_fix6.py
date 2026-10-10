# -*- coding: utf-8 -*-
"""fix6 acceptance: type tags, text fit, statusbar, toast pos, context menu flows, media query, screenshots."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

IDX = Path(r"D:\XTR-projects\pipeline-orchestrator\index.html")
OUT = Path(r"C:\Users\XXQ0928\AppData\Local\hermes\cache\scratch\idx_browser")
OUT.mkdir(exist_ok=True)

passed, failed = [], []
def R(name, ok, info=''):
    (passed if ok else failed).append((name, info))
    print(('PASS ' if ok else 'FAIL ') + name + ' | ' + str(info))

with sync_playwright() as p:
    b = p.chromium.launch(channel='msedge')
    pg = b.new_page(viewport={'width': 1366, 'height': 768})
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(IDX.as_uri()); pg.wait_for_timeout(1600)

    def counts():
        return pg.evaluate("() => {var d=XTR.graph.getDocs(); return {n:d.pipeline.nodes.length, e:d.pipeline.edges.length};}")
    def menu_items():
        return pg.evaluate("() => { var m=document.querySelector('.ctx-menu'); return m? Array.from(m.querySelectorAll('.ctx-item')).map(function(b){return b.textContent;}) : null; }")
    def click_item(label):
        rb = pg.evaluate("""(label) => { var b=Array.from(document.querySelectorAll('.ctx-item')).find(function(x){return x.textContent===label;}); if(!b) return null; var r=b.getBoundingClientRect(); return {x:r.x+r.width/2, y:r.y+r.height/2}; }""", label)
        if rb: pg.mouse.click(rb['x'], rb['y']); pg.wait_for_timeout(400)
        return rb is not None

    # F1: node type tags
    tags = pg.evaluate("() => Array.from(document.querySelectorAll('#layer-nodes .node-type')).map(function(t){return t.textContent;})")
    R('F1 node type tags visible', sorted(tags) == sorted(['输入', '模型调用', '输出']), tags)

    # F2: sub text fits within card width (200)
    fit = pg.evaluate("""() => {
      var out=[];
      document.querySelectorAll('#layer-nodes .node').forEach(function(n){
        var sub=n.querySelector('.node-sub');
        if(sub) out.push([n.getAttribute('data-id'), Math.round(sub.getComputedTextLength())]);
      });
      return out;
    }""")
    R('F2 sub text within card width', bool(fit) and all(w <= 200 for _, w in fit), fit)

    # F3: statusbar zoom label + de-duped valid text
    sb = pg.evaluate("() => document.getElementById('statusbar').innerText.replace(/\\s+/g,' ')")
    R('F3a statusbar 缩放 label', '缩放' in sb, sb)
    R('F3b 校验 de-duped', '校验：通过' in sb, sb)

    # F4: toast root moved to bottom
    ts = pg.evaluate("() => { var cs=getComputedStyle(document.getElementById('toast-root')); return cs.bottom + '|' + cs.top; }")
    R('F4 toast root at bottom', ts.split('|')[0] == '44px', ts)

    # F5: right-click node -> menu -> delete node
    c0 = counts()
    nc = pg.evaluate("""() => { var el=document.querySelector('.node[data-id=\\"n_out\\"]'); var r=el.getBoundingClientRect(); return {x:r.x+r.width/2, y:r.y+30}; }""")
    pg.mouse.click(nc['x'], nc['y'], button='right'); pg.wait_for_timeout(350)
    m1 = menu_items()
    pg.screenshot(path=str(OUT / 'fix6_ctx_node.png'))
    R('F5a node menu opens', m1 == ['复制节点', '删除节点'], m1)
    click_item('删除节点')
    c1 = counts()
    R('F5b delete via menu', c1['n'] == c0['n'] - 1 and c1['e'] == c0['e'] - 1, f"{c0} -> {c1}")
    R('F5c menu closed after action', pg.evaluate("() => !document.querySelector('.ctx-menu')"), '')

    # F6: right-click blank -> new model node; also Escape closes
    c2 = counts()
    pg.mouse.click(780, 620, button='right'); pg.wait_for_timeout(350)
    m2 = menu_items()
    pg.screenshot(path=str(OUT / 'fix6_ctx_blank.png'))
    R('F6a blank menu opens', m2 is not None and '新建「模型调用」节点' in m2, m2)
    click_item('新建「模型调用」节点')
    c3 = counts()
    R('F6b new node via menu', c3['n'] == c2['n'] + 1, f"{c2} -> {c3}")
    pg.mouse.click(700, 600, button='right'); pg.wait_for_timeout(250)
    pg.keyboard.press('Escape'); pg.wait_for_timeout(200)
    R('F6c Escape closes menu', pg.evaluate("() => !document.querySelector('.ctx-menu')"), '')

    # F7: right-click edge -> delete edge
    pts = pg.evaluate("""() => {
      var es=document.querySelectorAll('#layer-edges g.edge');
      if(!es.length) return null;
      var path=es[0].querySelector('path');
      var pt=path.getPointAtLength(path.getTotalLength()/2);
      var s=XTR.view.worldToScreen(pt.x,pt.y);
      return {x:s.x, y:s.y, key:es[0].getAttribute('data-edge-id')};
    }""")
    c4 = counts()
    if pts:
        pg.mouse.click(pts['x'], pts['y'], button='right'); pg.wait_for_timeout(350)
        m3 = menu_items()
        R('F7a edge menu opens', m3 == ['删除连线'], m3)
        click_item('删除连线')
    c5 = counts()
    R('F7b delete edge via menu', pts is not None and c5['e'] == c4['e'] - 1, f"{c4} -> {c5}")

    # F8: media query shrink
    pg.set_viewport_size({'width': 1000, 'height': 700}); pg.wait_for_timeout(300)
    mq = pg.evaluate("() => { var a=getComputedStyle(document.getElementById('palette')).width; var b=getComputedStyle(document.getElementById('inspector')).width; return a+'|'+b; }")
    R('F8 media query shrinks panels @1000px', mq == '168px|256px', mq)
    pg.set_viewport_size({'width': 1366, 'height': 768}); pg.wait_for_timeout(300)

    pg.screenshot(path=str(OUT / 'fix6_main_1366.png'))
    print('--- page errors (%d) ---' % len(errs))
    for e in errs[:6]: print(' ', e)
    b.close()

print('=' * 50)
print('FIX6 SUMMARY: %d/%d passed' % (len(passed), len(passed) + len(failed)))
for n, i in failed: print(' FAIL:', n, '|', i)
print('FIX6_DONE')
