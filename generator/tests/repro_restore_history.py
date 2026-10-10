# -*- coding: utf-8 -*-
"""复现：刷新1次→不能操作的空页面；刷新2次→回到初始模板。
完整证据链：拒绝弹窗不可见 + beforeunload 用空文档覆盖存档 + 存档被拒回落示例。
"""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

IDX = Path(r"D:\XTR-projects\pipeline-orchestrator\index.html")
OUT = Path(r"C:\Users\XXQ0928\AppData\Local\hermes\cache\scratch\idx_browser")

PROBE = """() => {
  var mr=document.getElementById('modal-root');
  var kids=[];
  for(var i=0;i<mr.children.length;i++){
    var c=mr.children[i]; var r=c.getBoundingClientRect(); var cs=getComputedStyle(c);
    kids.push({cls:String(c.className), top:Math.round(r.top), left:Math.round(r.left),
      w:Math.round(r.width), h:Math.round(r.height), position:cs.position, z:cs.zIndex});
  }
  var btns=[];
  mr.querySelectorAll('button').forEach(function(b){ var r=b.getBoundingClientRect();
    btns.push({t:(b.textContent||'').slice(0,14), top:Math.round(r.top), visible:(r.top<innerHeight&&r.bottom>0)}); });
  var doc=null; try{ doc=XTR.graph.getDocs(); }catch(e){}
  var ls=null; try{ ls=JSON.parse(localStorage.getItem('xtr.autosave.v1')||'null'); }catch(e){}
  var efc=document.elementFromPoint(Math.round(innerWidth/2), Math.round(innerHeight/2));
  return {
    domNodes: document.querySelectorAll('.node[data-id]').length,
    docNodes: (doc&&doc.pipeline)?(doc.pipeline.nodes||[]).length:null,
    modalRootTop: Math.round(mr.getBoundingClientRect().top),
    modalKids: kids, modalBtns: btns,
    session: ls ? {nodes:(ls.pipeline&&ls.pipeline.nodes||[]).length, pipelineIsNull: ls.pipeline===null, savedAt: ls.savedAt} : null,
    centerElem: efc ? String(efc.id||efc.className||efc.tagName).slice(0,50) : null
  };
}"""

def probe(pg, tag):
    d = pg.evaluate(PROBE)
    print(tag, json.dumps(d, ensure_ascii=False))
    return d

with sync_playwright() as p:
    b = p.chromium.launch(channel='msedge', args=['--allow-file-access-from-files'])
    ctx = b.new_context(viewport={'width': 1600, 'height': 950})
    pg = ctx.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)[:200]))

    # T0: 首次打开（无存档）→ 应载入示例
    pg.goto(IDX.as_uri()); pg.wait_for_timeout(2400)
    probe(pg, 'T0 初次打开:')

    # T1: 做一个真实编辑（拖动 n_in），等自动保存
    box = pg.evaluate("""() => { var g=document.querySelector('.node[data-id="n_in"]');
      if(!g) return null; var r=g.getBoundingClientRect(); return {x:r.x+50, y:r.y+8}; }""")
    if box:
        pg.mouse.move(box['x'], box['y']); pg.mouse.down()
        pg.mouse.move(box['x'] + 60, box['y'], steps=8); pg.mouse.up()
    pg.wait_for_timeout(2000)
    probe(pg, 'T1 编辑后(应已自动保存):')

    # ---- 刷新一次 ----
    pg.reload(); pg.wait_for_timeout(2600)
    d2 = probe(pg, 'T2 刷新#1:')
    pg.screenshot(path=str(OUT / 'repro_t2_empty_page.png'))

    # 刷新前再录一次存档状态
    # ---- 刷新二次 ----
    pg.reload(); pg.wait_for_timeout(2600)
    d3 = probe(pg, 'T3 刷新#2:')
    pg.screenshot(path=str(OUT / 'repro_t3_template.png'))

    body = pg.evaluate("() => document.body.innerText.replace(/\\s+/g,' ').slice(0,150)")
    print('T3 页面文本:', body)
    print('pageerrors:', errs)
    b.close()
