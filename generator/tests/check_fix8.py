# -*- coding: utf-8 -*-
"""fix8 acceptance: prompt editor renders/edits; textarea widget for input node."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

IDX = Path(r"D:\XTR-projects\pipeline-orchestrator\index.html")
OUT = Path(r"C:\Users\XXQ0928\AppData\Local\hermes\cache\scratch\idx_browser")

passed, failed = [], []
def R(name, ok, info=''):
    (passed if ok else failed).append((name, info))
    print(('PASS ' if ok else 'FAIL ') + name + ' | ' + str(info)[:200])

with sync_playwright() as p:
    b = p.chromium.launch(channel='msedge')
    pg = b.new_page(viewport={'width': 1366, 'height': 768})
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(IDX.as_uri()); pg.wait_for_timeout(1600)

    pg.evaluate("() => XTR.inspector.show('n_model')")
    pg.wait_for_timeout(400)

    # F1: user-prompt textarea exists, sized, inside panel
    f1 = pg.evaluate("""() => {
      var tas=document.querySelectorAll('#inspector-form textarea.prompt-ta');
      if(!tas.length) return {n:0};
      var ta=tas[tas.length-1];
      var r=ta.getBoundingClientRect();
      var pre=ta.parentNode.querySelector('pre.prompt-hl');
      var pr=pre?pre.getBoundingClientRect():null;
      return {n:tas.length, ta:[Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)],
              val:ta.value.slice(0,40),
              pre:pr?[Math.round(pr.x),Math.round(pr.y),Math.round(pr.width),Math.round(pr.height)]:null,
              preText:pre?pre.innerText.slice(0,40):''};
    }""")
    R('F1a two prompt textareas exist', f1.get('n') == 2, f1.get('n'))
    R('F1b user textarea visible+sized', f1.get('ta') and f1['ta'][3] > 80 and f1['ta'][0] >= 1040, f1.get('ta'))
    R('F1c textarea prefilled', '请把下面的文本整理' in (f1.get('val') or ''), f1.get('val'))
    R('F1d highlight layer confined to field', f1.get('pre') and f1['pre'][2] < 400 and f1['pre'][1] > 100, f1.get('pre'))
    R('F1e highlight text present', '请把下面的文本整理' in (f1.get('preText') or ''), f1.get('preText'))

    # F2: edit user prompt -> config write-through
    pg.evaluate("""() => {
      var tas=document.querySelectorAll('#inspector-form textarea.prompt-ta');
      var ta=tas[tas.length-1];
      ta.focus(); ta.value = ta.value + ' 【改】';
      ta.dispatchEvent(new Event('input', {bubbles:true}));
    }""")
    pg.wait_for_timeout(600)
    f2 = pg.evaluate("""() => { var d=XTR.graph.getDocs(); var n=d.pipeline.nodes.find(function(x){return x.id==='n_model';}); return {tpl:n.config.prompt.template.slice(-10), sys:(n.config.prompt.system||'').slice(-10)}; }""")
    R('F2 edit writes to node config', '【改】' in f2['tpl'], f2)

    pg.locator('#inspector').screenshot(path=str(OUT / 'ins8_model.png'))

    # F3: input node content is now a real textarea
    pg.evaluate("() => XTR.inspector.show('n_in')")
    pg.wait_for_timeout(350)
    f3 = pg.evaluate("""() => {
      var f=document.getElementById('inspector-form');
      var tas=f.querySelectorAll('textarea');
      var first=tas[0];
      var r=first?first.getBoundingClientRect():null;
      return {tag:first?first.tagName:'none', rows:first?first.rows:0, h:r?Math.round(r.height):0};
    }""")
    R('F3a input content is TEXTAREA', f3['tag'] == 'TEXTAREA' and f3['h'] > 80, f3)

    # F4: prompt box scroll/height sanity in model panel (visual)
    pg.evaluate("() => XTR.inspector.show('n_model')")
    pg.wait_for_timeout(300)
    f4 = pg.evaluate("""() => {
      var box=document.querySelector('#inspector-form .prompt-wrap');
      var r=box.getBoundingClientRect();
      return {w:Math.round(r.width), h:Math.round(r.height)};
    }""")
    R('F4 prompt-wrap has height', f4['h'] > 90, f4)

    print('--- page errors (%d) ---' % len(errs))
    for e in errs[:6]: print(' ', e[:220])
    b.close()

print('=' * 50)
print('FIX8 SUMMARY: %d/%d passed' % (len(passed), len(passed) + len(failed)))
for n, i in failed: print(' FAIL:', n, '|', str(i)[:180])
print('FIX8_DONE')
