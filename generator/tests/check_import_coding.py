# -*- coding: utf-8 -*-
"""导入验收：把 coding-pipeline.pipeline.json + coding-pipeline.layout.json
用真实 UI 流程（#btn-import + 文件选择器）导入编排器，验证渲染/连线/端口/
属性面板/变量校验/导出回环。
"""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

SCR = Path(r"C:\Users\XXQ0928\AppData\Local\hermes\cache\scratch")
PROJ = Path(r"D:\XTR-projects\pipeline-orchestrator")
IDX = PROJ / 'index.html'
EXP = SCR / 'idx_browser' / 'exports_import'; EXP.mkdir(parents=True, exist_ok=True)
OUT = SCR / 'idx_browser'

results = []
def R(name, ok, detail=''):
    results.append((name, ok, str(detail)[:240]))
    print(('PASS ' if ok else 'FAIL ') + name + (' | ' + str(detail)[:240] if detail else ''))

console_msgs, page_errors, downloads = [], [], []

with sync_playwright() as p:
    b = p.chromium.launch(channel='msedge', args=['--allow-file-access-from-files'])
    pg = b.new_page(viewport={'width': 1600, 'height': 950})
    pg.on('console', lambda m: console_msgs.append((m.type, m.text[:250])))
    pg.on('pageerror', lambda e: page_errors.append(str(e)[:300]))
    pg.on('download', lambda d: downloads.append(d))

    pg.goto(IDX.as_uri())
    pg.wait_for_timeout(2200)
    R('boot: no errors', len(page_errors) == 0, '; '.join(page_errors[:3]))

    # ---- import the coding-pipeline pair ----
    with pg.expect_file_chooser() as fc:
        pg.click('#btn-import')
    fc.value.set_files([str(PROJ / 'samples/coding-pipeline.pipeline.json'),
                        str(PROJ / 'samples/coding-pipeline.layout.json')])
    pg.wait_for_timeout(2600)

    body = pg.evaluate("() => document.body.innerText.replace(/\\s+/g, ' ')")
    R('import: toast success', '导入成功' in body, body[:160])
    R('import: no error dialog', pg.evaluate(
        "() => !document.querySelector('.modal, .dialog') || getComputedStyle(document.querySelector('.modal, .dialog')).display==='none'"))

    st = pg.evaluate("""() => { try { var d=XTR.graph.getDocs(); return {
        ids: d.pipeline.nodes.map(n=>n.id),
        types: d.pipeline.nodes.map(n=>n.type),
        nedges: d.pipeline.edges.length,
        edge0: d.pipeline.edges[0],
        lpos: {p0: d.layout.nodes['n_p0'], end: d.layout.nodes['n_end'], p1b: d.layout.nodes['n_p1b']},
        lcount: Object.keys(d.layout.nodes).length,
        pid: d.pipeline.meta.pipeline_id, lpid: d.layout.meta.pipeline_id,
        tr: XTR.view.getTransform() }; } catch(e){ return 'e:'+e.message; } }""")
    R('import: 9 nodes, right ids', isinstance(st, dict) and st.get('ids') == ['n_req','n_p0','n_p1','n_p1b','n_p2','n_p3a','n_p3b','n_p4','n_end'],
      st.get('ids') if isinstance(st, dict) else st)
    R('import: 13 edges', isinstance(st, dict) and st.get('nedges') == 13, st.get('nedges') if isinstance(st, dict) else '')
    e0 = st.get('edge0', {}) if isinstance(st, dict) else {}
    R('import: edges are string-style', isinstance(e0, dict) and set(e0.keys()) <= {'from','from_port','to','to_port','label'} and e0.get('from_port') == 'text',
      json.dumps(e0, ensure_ascii=False))
    lp = st.get('lpos', {}) if isinstance(st, dict) else {}
    R('import: layout positions kept', lp.get('p0', {}).get('x') == 340 and lp.get('p0', {}).get('y') == 400 and lp.get('end', {}).get('x') == 1740,
      json.dumps(lp, ensure_ascii=False))
    R('import: pipeline_id paired', st.get('pid') == 'coding-pipeline' and st.get('lpid') == 'coding-pipeline', f"{st.get('pid')} / {st.get('lpid')}")

    dom = pg.evaluate("() => ({ n: document.querySelectorAll('.node[data-id]').length, e: document.querySelectorAll('.edge[data-edge-id]').length })")
    R('import: DOM 9 nodes 13 edges', dom.get('n') == 9 and dom.get('e') == 13, dom)
    sb = pg.evaluate("() => (document.getElementById('st-nodes')||{}).textContent + ' / ' + (document.getElementById('st-edges')||{}).textContent")
    R('import: statusbar 9/13', '9' in str(sb) and '13' in str(sb), sb)

    tr = st.get('tr', {}) if isinstance(st, dict) else {}
    R('import: file viewport (camera) applied', abs(tr.get('x', 9)) < 1 and abs(tr.get('y', 0) - 196) < 1.5 and abs(tr.get('k', 0) - 0.53) < 0.02, tr)

    # all 9 nodes on screen
    vis = pg.evaluate("""() => {
      var out=[], W=window.innerWidth, H=window.innerHeight;
      XTR.view.getNodeBBoxes().forEach(function(b){
        var p1=XTR.view.worldToScreen(b.x1,b.y1), p2=XTR.view.worldToScreen(b.x2,b.y2);
        out.push({id:b.id, ok: p1.x>=0 && p1.y>=0 && p2.x<=W && p2.y<=H, x1:Math.round(p1.x), y1:Math.round(p1.y), x2:Math.round(p2.x), y2:Math.round(p2.y)});
      });
      return out; }""")
    bad = [v for v in vis if not v.get('ok')]
    R('import: all 9 nodes on screen', len(vis) == 9 and not bad, json.dumps(bad, ensure_ascii=False) if bad else 'all visible')

    # node card text: provider/model shown
    t_p2 = pg.evaluate("() => { var g=document.querySelector('.node[data-id=\"n_p2\"]'); return g ? g.textContent.replace(/\\s+/g,' ') : ''; }")
    R('card n_p2 shows glm-5.3', 'glm-5.3' in t_p2, t_p2[:150])
    t_p4 = pg.evaluate("() => { var g=document.querySelector('.node[data-id=\"n_p4\"]'); return g ? g.textContent.replace(/\\s+/g,' ') : ''; }")
    R('card n_p4 port labels', '代码审查' in t_p4 and '视觉审查' in t_p4, t_p4[:200])

    pg.screenshot(path=str(OUT / 'v9_import_main.png'))

    # ---- click n_p2 -> inspector ----
    pg.locator('.node[data-id="n_p2"]').first.click(position={'x': 50, 'y': 8}, timeout=4000)
    pg.wait_for_timeout(600)
    ins = pg.evaluate("""() => { var f=document.querySelector('#inspector-form');
      if(!f) return {form:false, text:(document.querySelector('#inspector')||document.body).innerText.slice(0,200)};
      return { form:true,
        text: f.innerText.replace(/\\s+/g,' '),
        inputs: [...f.querySelectorAll('input')].map(i=>i.value),
        selects: [...f.querySelectorAll('select')].map(s=>s.selectedOptions[0]?s.selectedOptions[0].textContent:''),
        tas: [...f.querySelectorAll('textarea')].map(t=>t.value.slice(0,300)) }; }""")
    R('inspector: opened', ins.get('form') is True, ins.get('text', '')[:160])
    R('inspector: 渠道=智谱 GLM', any('智谱' in s for s in ins.get('selects', [])), ins.get('selects'))
    R('inspector: 模型=glm-5.3', any('glm-5.3' in v for v in ins.get('inputs', [])), ins.get('inputs'))
    R('inspector: prompt present', any('文件清单' in t for t in ins.get('tas', [])), [t[:60] for t in ins.get('tas', [])])
    R('inspector: no dangling-var warning', '悬空' not in ins.get('text', ''), ins.get('text', '')[:160])
    pg.screenshot(path=str(OUT / 'v9_import_insp.png'))

    # ---- export round-trip ----
    downloads.clear()
    pg.click('#btn-export-both')
    pg.wait_for_timeout(2500)
    files = []
    for d in downloads:
        fn = d.suggested_filename
        d.save_as(EXP / fn)
        files.append(fn)
    R('export: 2 files', len(files) == 2, files)
    pip_fn = [f for f in files if 'pipeline' in f]
    lay_fn = [f for f in files if 'layout' in f]
    if pip_fn and lay_fn:
        po = json.loads((EXP / pip_fn[0]).read_text(encoding='utf-8'))
        lo = json.loads((EXP / lay_fn[0]).read_text(encoding='utf-8'))
        R('export: 9 nodes 13 string-edges', len(po.get('nodes', [])) == 9 and len(po.get('edges', [])) == 13
          and all('id' not in e and 'from_port' in e for e in po.get('edges', [])), f"n={len(po.get('nodes',[]))} e={len(po.get('edges',[]))}")
        R('export: meta/pipeline_id kept', po.get('meta', {}).get('pipeline_id') == 'coding-pipeline', po.get('meta', {}).get('pipeline_id'))
        e_np3a = [e for e in po.get('edges', []) if e.get('from') == 'n_p3a' and e.get('to') == 'n_p4']
        R('export: n_p3a->n_p4 to_port=review_code', len(e_np3a) == 1 and e_np3a[0].get('to_port') == 'review_code', json.dumps(e_np3a, ensure_ascii=False)[:160])
        e1 = pg.evaluate("(o) => { var r=XTR.validate.checkSchema('pipeline', o); return r.errors.length ? JSON.stringify(r.errors.slice(0,3)) : 'OK' }", po)
        e2 = pg.evaluate("(o) => { var r=XTR.validate.checkSchema('layout', o); return r.errors.length ? JSON.stringify(r.errors.slice(0,3)) : 'OK' }", lo)
        R('export: pipeline passes schema', e1 == 'OK', e1)
        R('export: layout passes schema', e2 == 'OK', e2)

    R('final: no page errors', len(page_errors) == 0, '; '.join(page_errors[:3]))
    print('--- console (last 10 of %d) ---' % len(console_msgs))
    for t_, m in console_msgs[-10:]:
        print(' ', t_, '|', m)
    b.close()

fails = [r for r in results if not r[1]]
print('=' * 52)
print('IMPORT SUMMARY: %d/%d passed' % (len(results) - len(fails), len(results)))
for r in fails:
    print(' FAIL:', r[0], '|', r[2])
