# -*- coding: utf-8 -*-
"""v4 repro/verify: card texts, node select+delete (key+button), undo (key+button), connect drag."""
import json, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

SCR = Path(r"C:\Users\XXQ0928\AppData\Local\hermes\cache\scratch")
PROJ = Path(r"D:\XTR-projects\pipeline-orchestrator")
IDX = PROJ / 'index.html'
OUT = SCR / 'idx_browser'; OUT.mkdir(exist_ok=True)

results = []
def R(name, ok, detail=''):
    results.append((name, ok, str(detail)[:260]))
    print(('PASS ' if ok else 'FAIL ') + name + (' | ' + str(detail)[:260] if detail else ''))

page_errors, console_msgs = [], []
def counts(pg):
    return pg.evaluate("() => { var d=XTR.graph.getDocs(); return {n:d.pipeline.nodes.length, e:d.pipeline.edges.length}; }")
def sel(pg):
    return pg.evaluate("() => { var s=XTR.view.getSelection(); return s.nodes.join(',')+'|'+s.edges.join(','); }")
def center(pg, selector):
    return pg.evaluate("""(s) => { var el=document.querySelector(s); if(!el) return null;
      var r=el.getBoundingClientRect(); return {x:r.x+r.width/2, y:r.y+r.height/2, w:r.width, h:r.height}; }""", selector)

with sync_playwright() as p:
    b = p.chromium.launch(channel='msedge')
    pg = b.new_page(viewport={'width': 1600, 'height': 950})
    pg.on('pageerror', lambda e: page_errors.append(str(e)[:300]))
    pg.on('console', lambda m: console_msgs.append((m.type, m.text[:200])))
    pg.goto(IDX.as_uri()); pg.wait_for_timeout(2200)

    # ---- T1: card texts on canvas ----
    cards = pg.evaluate("""() => Array.from(document.querySelectorAll('.node[data-id]')).map(g => ({
      id: g.getAttribute('data-id'),
      title: (g.querySelector('.node-title')||{}).textContent || '',
      sub: (g.querySelector('.node-sub')||{}).textContent || '',
      tip: (g.querySelector('title')||{}).textContent || '' }))""")
    R('T1 card texts dump', True, json.dumps(cards, ensure_ascii=False))

    # ---- T2: click n_out -> selected? ----
    c = center(pg, '.node[data-id="n_out"]')
    pg.mouse.click(c['x'], c['y']); pg.wait_for_timeout(350)
    R('T2 click selects n_out', sel(pg).startswith('n_out'), 'sel=' + sel(pg))
    cls = pg.evaluate("() => document.querySelector('.node[data-id=\\'n_out\\']').getAttribute('class')")
    R('T2b selected class on card', 'selected' in (cls or ''), cls)

    # ---- T3: keyboard Delete ----
    before = counts(pg)
    pg.keyboard.press('Delete'); pg.wait_for_timeout(450)
    after = counts(pg)
    R('T3 key Delete removes node+edge', after['n'] == before['n'] - 1 and after['e'] == before['e'] - 1,
      f"{before} -> {after}")

    # ---- T4: keyboard undo restores ----
    pg.keyboard.press('Control+z'); pg.wait_for_timeout(450)
    back = counts(pg)
    R('T4 Ctrl+Z restores', back == before, f"{after} -> {back} (want {before})")

    # ---- T5: toolbar delete button ----
    c = center(pg, '.node[data-id="n_out"]')
    pg.mouse.click(c['x'], c['y']); pg.wait_for_timeout(300)
    pg.click('#btn-delete'); pg.wait_for_timeout(450)
    after2 = counts(pg)
    R('T5 button delete works', after2 == after, f"{after2} (want {after})")

    # ---- T6: toolbar undo button (known-broken pre-fix) ----
    pg.click('#btn-undo'); pg.wait_for_timeout(450)
    back2 = counts(pg)
    R('T6 button undo works', back2 == before, f"{back2} (want {before})")
    if back2 != before:
        pg.keyboard.press('Control+z'); pg.wait_for_timeout(400)

    # ---- T7: connect by dragging from output port to input port ----
    e0 = counts(pg)
    po = center(pg, '.node[data-id="n_in"] .port.out')
    pi = center(pg, '.node[data-id="n_out"] .port.in')
    R('T7 port elements found', bool(po and pi), f"out={po} in={pi}")
    if po and pi:
        pg.mouse.move(po['x'], po['y']); pg.wait_for_timeout(120)
        pg.mouse.down(); pg.wait_for_timeout(120)
        mid = {'x': (po['x'] + pi['x']) / 2, 'y': min(po['y'], pi['y']) - 60}
        pg.mouse.move(mid['x'], mid['y'], steps=8); pg.wait_for_timeout(150)
        tmp = pg.evaluate("() => document.querySelectorAll('.temp-link').length")
        pg.mouse.move(pi['x'], pi['y'], steps=8); pg.wait_for_timeout(200)
        pg.mouse.up(); pg.wait_for_timeout(450)
        e1 = counts(pg)
        toast = pg.evaluate("() => document.body.innerText")
        R('T7b temp link drawn during drag', tmp > 0, f'temp elems={tmp}')
        R('T7c edge created by drag', e1['e'] == e0['e'] + 1, f"{e0} -> {e1}")
        R('T7d toast 已创建连线', '已创建连线' in toast, [s for s in ['已创建连线','不兼容','已存在','循环','没有输入端口'] if s in toast])

    # ---- T8: inspector dump for n_model ----
    c = center(pg, '.node[data-id="n_model"]')
    pg.mouse.click(c['x'], c['y']); pg.wait_for_timeout(400)
    ins = pg.evaluate("() => { var el=document.getElementById('inspector'); return el ? el.innerText.replace(/\\n+/g,' | ').slice(0,600) : 'no-inspector'; }")
    R('T8 inspector dump', True, ins)

    pg.screenshot(path=str(OUT / 'v4_after.png'))
    print('--- page errors (%d) ---' % len(page_errors))
    for e in page_errors[:8]: print(' ', e)
    print('--- console (%d, last 10) ---' % len(console_msgs))
    for t_, m in console_msgs[-10:]: print(' ', t_, '|', m)
    b.close()

fails = [r for r in results if not r[1]]
print('=' * 50)
print('V4 SUMMARY: %d/%d passed' % (len(results) - len(fails), len(results)))
for r in fails: print(' FAIL:', r[0], '|', r[2])
print('V4_DONE')
