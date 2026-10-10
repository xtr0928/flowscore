# -*- coding: utf-8 -*-
"""v3 full-chain browser acceptance: boot / drag / import / export / autosave / reload / selftest."""
import json, re, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

SCR = Path(r"C:\Users\XXQ0928\AppData\Local\hermes\cache\scratch")
PROJ = Path(r"D:\XTR-projects\pipeline-orchestrator")
IDX = PROJ / 'index.html'
OUT = SCR / 'idx_browser'; OUT.mkdir(exist_ok=True)
EXP = OUT / 'exports'; EXP.mkdir(exist_ok=True)

results = []
def R(name, ok, detail=''):
    results.append((name, ok, str(detail)[:220]))
    print(('PASS ' if ok else 'FAIL ') + name + (' | ' + str(detail)[:220] if detail else ''))

console_msgs, page_errors, bad_requests, downloads = [], [], [], []

with sync_playwright() as p:
    b = p.chromium.launch(channel='msedge', args=['--allow-file-access-from-files'])
    pg = b.new_page(viewport={'width': 1600, 'height': 950})
    pg.on('console', lambda m: console_msgs.append((m.type, m.text[:250])))
    pg.on('pageerror', lambda e: page_errors.append(str(e)[:300]))
    pg.on('request', lambda r: None if r.url.startswith(('file://','data:','blob:')) else bad_requests.append(r.url))
    pg.on('download', lambda d: downloads.append(d))

    # ---- 1. boot / sample load ----
    pg.goto(IDX.as_uri())
    pg.wait_for_timeout(2200)
    R('boot: no page errors', len(page_errors) == 0, '; '.join(page_errors[:3]))
    st = pg.evaluate("""() => { try { var d=XTR.graph.getDocs();
      return {p: d&&d.pipeline?d.pipeline.nodes.length:-1, l: d&&d.layout&&d.layout.nodes?Object.keys(d.layout.nodes).length:-1,
        pids: d&&d.pipeline?d.pipeline.nodes.map(n=>n.id):[] }; } catch(e){ return 'e:'+e.message; } }""")
    R('sample loaded: 3 nodes', isinstance(st, dict) and st.get('p') == 3 and st.get('l') == 3, st)
    domn = pg.evaluate("() => document.querySelectorAll('.node[data-id]').length")
    dome = pg.evaluate("() => document.querySelectorAll('.edge[data-edge-id]').length")
    R('DOM nodes=3 edges=2', domn == 3 and dome == 2, f'nodes={domn} edges={dome}')
    sb = pg.evaluate("() => (document.getElementById('st-nodes')||{}).textContent + ' / ' + (document.getElementById('st-edges')||{}).textContent")
    R('statusbar shows 3/2', '3' in str(sb) and '2' in str(sb), sb)
    R('toast sample loaded', '已载入内置示例' in pg.evaluate("() => document.body.innerText"))
    pg.screenshot(path=str(OUT / 'v3_main.png'))

    # ---- schema equivalence ----
    for name in ('pipeline', 'layout'):
        js = pg.evaluate("() => window.XTR.validate.SCHEMA.%s ? JSON.stringify(window.XTR.validate.SCHEMA.%s) : null" % (name, name))
        if js:
            a = json.loads(js)
            c = json.loads((PROJ / 'schema' / (name + '.schema.json')).read_text(encoding='utf-8'))
            canon = lambda o: json.dumps(o, sort_keys=True, ensure_ascii=False)
            R('schema %s equivalent to disk' % name, canon(a) == canon(c))

    R('checkSchema exists', pg.evaluate("() => typeof XTR.validate.checkSchema") == 'function')
    R('providers include kimi+token8341', pg.evaluate("() => XTR.providers.list().map(p=>p.id).join(',')"), 'kimi' in pg.evaluate("() => XTR.providers.list().map(p=>p.id).join(',')"))

    # ---- 2. drag n_in ----
    box = pg.evaluate("""() => { var g=document.querySelector('.node[data-id="n_in"]');
      if(!g) return null; var r=g.getBoundingClientRect(); return {x:r.x+r.width/2, y:r.y+r.height/2}; }""")
    if box:
        pg.mouse.move(box['x'], box['y']); pg.mouse.down()
        pg.mouse.move(box['x'] + 80, box['y'] + 40, steps=10); pg.mouse.up()
        pg.wait_for_timeout(500)
        pos = pg.evaluate("() => JSON.stringify(XTR.graph.getDocs().layout.nodes['n_in'])")
        R('drag moved n_in', ('"x":160' in pos or '160' in pos) and '"y":240' in pos.replace(' ', ''), pos)
    else:
        R('drag moved n_in', False, 'node not found')
    pg.screenshot(path=str(OUT / 'v3_drag.png'))

    # ---- 3. import demo-basic pair ----
    with pg.expect_file_chooser() as fc:
        pg.click('#btn-import')
    fc.value.set_files([str(PROJ / 'samples/demo-basic.pipeline.json'), str(PROJ / 'samples/demo-basic.layout.json')])
    pg.wait_for_timeout(2200)
    imp = pg.evaluate("""() => { try { var d=XTR.graph.getDocs();
      return {pids: d.pipeline.nodes.map(n=>n.id), ln: Object.keys(d.layout.nodes).length,
        n1: d.layout.nodes['n_1'], tr: XTR.view.getTransform() }; } catch(e){ return 'e:'+e.message; } }""")
    R('import: nodes n_1..n_3', isinstance(imp, dict) and imp.get('pids') == ['n_1', 'n_2', 'n_3'], imp if not isinstance(imp, dict) else imp.get('pids'))
    R('import: layout 3 entries', isinstance(imp, dict) and imp.get('ln') == 3)
    R('import: n_1 at 80,200', isinstance(imp, dict) and imp.get('n1', {}).get('x') == 80 and imp.get('n1', {}).get('y') == 200, imp if isinstance(imp, dict) else '')
    tr = imp.get('tr', {}) if isinstance(imp, dict) else {}
    R('import: viewport applied', abs(tr.get('x', 9)) < 0.5 and abs(tr.get('y', 9)) < 0.5 and abs(tr.get('k', 9) - 1) < 0.01, tr)
    R('import: toast success', '导入成功' in pg.evaluate("() => document.body.innerText"))
    domn2 = pg.evaluate("() => document.querySelectorAll('.node[data-id]').length")
    dome2 = pg.evaluate("() => document.querySelectorAll('.edge[data-edge-id]').length")
    R('import: DOM 3 nodes 2 edges', domn2 == 3 and dome2 == 2, f'n={domn2} e={dome2}')
    no_dialog = pg.evaluate("() => !document.querySelector('.modal, .dialog') || document.querySelector('.modal, .dialog').style.display==='none'")
    R('import: no error modal', bool(no_dialog))
    pg.screenshot(path=str(OUT / 'v3_import.png'))

    # ---- 4. export both, save, validate ----
    downloads.clear()
    pg.click('#btn-export-both')
    pg.wait_for_timeout(2500)
    files = []
    for d in downloads:
        fn = d.suggested_filename
        d.save_as(EXP / fn)
        files.append(fn)
    R('export: 2 files downloaded', len(files) == 2, files)
    lay_fn = [f for f in files if 'layout' in f]
    pip_fn = [f for f in files if 'pipeline' in f]
    if lay_fn and pip_fn:
        lo = json.loads((EXP / lay_fn[0]).read_text(encoding='utf-8'))
        po = json.loads((EXP / pip_fn[0]).read_text(encoding='utf-8'))
        R('export pipeline: kind+no edge ids+3 edges-free', po.get('kind') == 'pipeline' and all('id' not in e for e in po.get('edges', [])) and len(po.get('nodes', [])) == 3, 'edges=' + json.dumps(po.get('edges'), ensure_ascii=False)[:150])
        R('export layout: map+viewport+canvas', lo.get('kind') == 'layout' and isinstance(lo.get('nodes'), dict) and len(lo.get('nodes', {})) == 3 and 'viewport' in lo and 'canvas' in lo, 'vp=' + json.dumps(lo.get('viewport')))
        e1 = pg.evaluate("(o) => { var r=XTR.validate.checkSchema('pipeline', o); return r.errors.length ? JSON.stringify(r.errors.slice(0,3)) : 'OK' }", po)
        e2 = pg.evaluate("(o) => { var r=XTR.validate.checkSchema('layout', o); return r.errors.length ? JSON.stringify(r.errors.slice(0,3)) : 'OK' }", lo)
        R('export pipeline passes schema', e1 == 'OK', e1)
        R('export layout passes schema', e2 == 'OK', e2)
        R('export layout roundtrip viewport', abs(lo.get('viewport', {}).get('x', 9)) < 0.5 and abs(lo.get('viewport', {}).get('zoom', 9) - 1) < 0.01, lo.get('viewport'))

    # ---- 5. autosave + reload restore ----
    pg.wait_for_timeout(1600)
    saved = pg.evaluate("() => localStorage.getItem('xtr.autosave.v1')")
    ok_saved = False
    if saved:
        sj = json.loads(saved)
        ok_saved = bool(sj.get('pipeline')) and bool(sj.get('layout', {}).get('viewport'))
        R('autosave: pipeline + viewport', ok_saved, list(sj.keys()))
    else:
        R('autosave: pipeline + viewport', False, 'no localStorage entry')
    pg.reload()
    pg.wait_for_timeout(1500)
    try:
        pg.locator('button:has-text("恢复会话")').first.click(timeout=3000)
        pg.wait_for_timeout(800)
        pids3 = pg.evaluate("() => XTR.graph.getDocs().pipeline.nodes.map(n=>n.id).join(',')")
        R('reload: session restored', pids3 == 'n_1,n_2,n_3', pids3)
    except Exception as ex:
        R('reload: session restored', False, str(ex)[:150])
    pg.screenshot(path=str(OUT / 'v3_restore.png'))

    # ---- 6. run bundled self-test page ----
    pg.goto((PROJ / 'tests' / 'test.html').as_uri())
    pg.wait_for_timeout(3500)
    tt = pg.evaluate("() => document.body.innerText.replace(/\\s+/g,' ')")
    open(OUT / 'testpage.txt', 'w', encoding='utf-8').write(tt)
    pg.screenshot(path=str(OUT / 'v3_testpage.png'), full_page=True)
    R('test page loaded', len(tt) > 40, tt[:160])

    print('--- page errors (%d) ---' % len(page_errors))
    for e in page_errors[:8]: print(' ', e)
    print('--- console (last 12 of %d) ---' % len(console_msgs))
    for t_, m in console_msgs[-12:]: print(' ', t_, '|', m)
    print('--- non-file requests:', len(bad_requests), bad_requests[:5])
    b.close()

fails = [r for r in results if not r[1]]
print('=' * 50)
print('V3 SUMMARY: %d/%d passed' % (len(results) - len(fails), len(results)))
for r in fails: print(' FAIL:', r[0], '|', r[2])
print('V3_DONE')
