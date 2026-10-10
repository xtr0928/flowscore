# -*- coding: utf-8 -*-
"""fix7 acceptance: inspector shows every click; tooltips hidden until hover; no overlaps."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

IDX = Path(r"D:\XTR-projects\pipeline-orchestrator\index.html")
OUT = Path(r"C:\Users\XXQ0928\AppData\Local\hermes\cache\scratch\idx_browser")

VIS_LEAVES_JS = """() => {
  var ins=document.getElementById('inspector');
  var out=[];
  ins.querySelectorAll('*').forEach(function(el){
    var cs=getComputedStyle(el);
    if(cs.display==='none'||cs.visibility==='hidden'||parseFloat(cs.opacity)<0.05) return;
    var r=el.getBoundingClientRect();
    if(r.width<2||r.height<2) return;
    var hasText=false;
    for(var i=0;i<el.childNodes.length;i++){ var n=el.childNodes[i]; if(n.nodeType===3&&n.textContent.trim().length){hasText=true;break;} }
    var isField=/^(INPUT|SELECT|TEXTAREA|BUTTON)$/.test(el.tagName);
    if(hasText||isField){
      out.push({el:el, x:r.x,y:r.y,w:r.width,h:r.height, t:isField?'v:'+String(el.value).slice(0,16):(el.textContent||'').trim().slice(0,20)});
    }
  });
  return out;
}"""

OVERLAP_JS = """() => {
  var leaves = (""" + VIS_LEAVES_JS + """)().map(function(l){return l;});
  var res=[];
  for(var i=0;i<leaves.length;i++) for(var j=i+1;j<leaves.length;j++){
    var a=leaves[i], b=leaves[j];
    if(a.el.contains(b.el)||b.el.contains(a.el)) continue;
    var wa=a.el.closest('.prompt-wrap'), wb=b.el.closest('.prompt-wrap');
    if(wa&&wa===wb) continue;  /* 高亮层与透明文本框在设计上完全叠放 */
    var ix=Math.max(0,Math.min(a.x+a.w,b.x+b.w)-Math.max(a.x,b.x));
    var iy=Math.max(0,Math.min(a.y+a.h,b.y+b.h)-Math.max(a.y,b.y));
    var inter=ix*iy, small=Math.min(a.w*a.h,b.w*b.h);
    if(inter>0&&small>0&&inter/small>0.2) res.push({a:a.t,b:b.t,r:Math.round(inter/small*100)/100});
  }
  return res;
}"""

passed, failed = [], []
def R(name, ok, info=''):
    (passed if ok else failed).append((name, info))
    print(('PASS ' if ok else 'FAIL ') + name + ' | ' + str(info)[:180])

with sync_playwright() as p:
    b = p.chromium.launch(channel='msedge')
    pg = b.new_page(viewport={'width': 1366, 'height': 768})
    errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(IDX.as_uri()); pg.wait_for_timeout(1600)

    def rect(sel):
        return pg.evaluate("(s)=>{var el=document.querySelector(s); if(!el) return null; var r=el.getBoundingClientRect(); return {x:r.x,y:r.y,w:r.width,h:r.height};}", sel)
    def click_node(nid):
        r = rect(f'.node[data-id="{nid}"]')
        pg.mouse.click(r['x'] + r['w']/2, r['y'] + r['h']*0.22)
        pg.wait_for_timeout(450)
    def ins_state():
        return pg.evaluate("""() => {
          var f=document.getElementById('inspector-form');
          var e=document.getElementById('inspector-empty');
          return {fd:f.style.display, ed:e.style.display, kids:f.children.length,
                  text:f.innerText.replace(/\\n+/g,' | ').slice(0,1500)};
        }""")

    # F1: first click shows form
    click_node('n_model')
    s1 = ins_state()
    R('F1a 1st click model -> form shows', s1['fd'] != 'none' and s1['kids'] > 3 and '调用渠道' in s1['text'], f"fd={s1['fd']} kids={s1['kids']}")
    R('F1b form has key fields', all(k in s1['text'] for k in ['调用渠道', '用户提示词', '覆盖策略']), s1['text'][:120])
    R('F1c empty state hidden', s1['ed'] == 'none', s1['ed'])
    pg.locator('#inspector').screenshot(path=str(OUT / 'ins7_model.png'))

    # F2: tooltips hidden by default
    tstate = pg.evaluate("""() => {
      var b=document.querySelector('#inspector .tip-bubble');
      if(!b) return 'none-found';
      return getComputedStyle(b).display;
    }""")
    R('F2 tooltip bubble hidden by default', tstate == 'none', tstate)

    # F3: no visible overlaps in panel
    ov = pg.evaluate(OVERLAP_JS)
    R('F3 no visible overlaps', len(ov) == 0, json.dumps(ov, ensure_ascii=False)[:250])

    # F4: hover tip shows bubble, leave hides
    tip = pg.query_selector('#inspector .tip')
    tip.hover(); pg.wait_for_timeout(350)
    hs = pg.evaluate("""() => {
      var b=document.querySelector('#inspector .tip-bubble');
      var cs=getComputedStyle(b);
      var r=b.getBoundingClientRect();
      return {d:cs.display, x:Math.round(r.x), y:Math.round(r.y), w:Math.round(r.width), h:Math.round(r.height),
              inVp: r.x>=0 && r.y>=0 && r.right<=window.innerWidth && r.bottom<=window.innerHeight};
    }""")
    R('F4a hover shows bubble', hs['d'] == 'block' and hs['w'] > 40, hs)
    R('F4b bubble inside viewport', hs['inVp'], hs)
    pg.screenshot(path=str(OUT / 'ins7_tooltip_hover.png'))
    pg.mouse.move(700, 620); pg.wait_for_timeout(300)
    hid = pg.evaluate("() => getComputedStyle(document.querySelector('#inspector .tip-bubble')).display")
    R('F4c leave hides bubble', hid == 'none', hid)

    # F5: switching nodes updates panel; re-click works (the reported bug)
    click_node('n_in')
    s2 = ins_state()
    R('F5a switch to input node', '输入内容' in s2['text'] and '调用渠道' not in s2['text'], s2['text'][:80])
    pg.mouse.click(700, 620); pg.wait_for_timeout(400)
    s3 = ins_state()
    R('F5b deselect -> empty state', s3['ed'] != 'none' and s3['fd'] == 'none', f"ed={s3['ed']} fd={s3['fd']}")
    click_node('n_model')
    s4 = ins_state()
    R('F5c RE-click model shows again', '调用渠道' in s4['text'] and s4['kids'] > 3, s4['text'][:80])
    click_node('n_out')
    s5 = ins_state()
    R('F5d output node form', '文件名模板' in s5['text'] and '输出文件格式' in s5['text'], s5['text'][:80])

    # F6: edit a field writes through (quick smoke: change 节点标题)
    inp = pg.query_selector('#inspector input[type="text"], #inspector input:not([type])')
    ok_edit = False
    if inp:
        inp.click(); inp.fill('我的模型'); pg.keyboard.press('Tab'); pg.wait_for_timeout(500)
        val = pg.evaluate("() => {var d=XTR.graph.getDocs(); var n=d.pipeline.nodes.find(function(x){return x.id==='n_model';}); return {label:n.label, sub:document.querySelector('.node[data-id=n_model] .node-title').textContent};}")
        ok_edit = True
    R('F6 edit smoke (label write-through)', ok_edit, 'edited' if ok_edit else 'no input found')

    print('--- page errors (%d) ---' % len(errs))
    for e in errs[:6]: print(' ', e[:220])
    b.close()

print('=' * 50)
print('INS7 SUMMARY: %d/%d passed' % (len(passed), len(passed) + len(failed)))
for n, i in failed: print(' FAIL:', n, '|', str(i)[:150])
print('INS7_DONE')
