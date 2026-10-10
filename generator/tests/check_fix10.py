# -*- coding: utf-8 -*-
"""fix10 验收：会话恢复全链路 + 全应用弹窗可见性 + 存档守卫。
故事线：编辑→刷新(弹窗可见)→恢复→丢弃→守卫(连刷不丢档)→帮助/清空弹窗。"""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

IDX = Path(r"D:\XTR-projects\pipeline-orchestrator\index.html")
OUT = Path(r"C:\Users\XXQ0928\AppData\Local\hermes\cache\scratch\idx_browser")

results = []
def R(name, ok, detail=''):
    results.append((name, ok, str(detail)[:230]))
    print(('PASS ' if ok else 'FAIL ') + name + (' | ' + str(detail)[:230] if detail else ''))

def probe(pg):
    return pg.evaluate("""() => {
      var mr=document.getElementById('modal-root');
      var mask=mr.querySelector('.modal-overlay'); var box=mr.querySelector('.modal');
      var info={dialog:false};
      if(mask&&box){
        var r=mask.getBoundingClientRect(), cs=getComputedStyle(mask);
        var br=box.getBoundingClientRect();
        var btns=[...mr.querySelectorAll('.modal-footer button')].map(b=>({t:b.textContent.trim(), vis:b.getBoundingClientRect().top<innerHeight}));
        var x=mr.querySelector('.modal-x');
        info={dialog:true, pos:cs.position, cover:{l:Math.round(r.left),t:Math.round(r.top),w:Math.round(r.width),h:Math.round(r.height)},
          box:{t:Math.round(br.top),b:Math.round(br.bottom),w:Math.round(br.width)},
          title:(mr.querySelector('.modal-title')||{}).textContent||'', btns:btns,
          xVisible: !!x && x.getBoundingClientRect().width>0 && getComputedStyle(x).display!=='none'};
      }
      var d=XTR.graph.getDocs();
      var ls=null; try{ ls=JSON.parse(localStorage.getItem('xtr.autosave.v1')||'null'); }catch(e){}
      return {domNodes:document.querySelectorAll('.node[data-id]').length,
        nInX: d&&d.layout&&d.layout.nodes['n_in'] ? d.layout.nodes['n_in'].x : null,
        sessionNodes: ls&&ls.pipeline ? (ls.pipeline.nodes||[]).length : null,
        sessionNull: ls ? ls.pipeline===null : null, dialog:info};
    }""")

errs = []
with sync_playwright() as p:
    b = p.chromium.launch(channel='msedge', args=['--allow-file-access-from-files'])
    ctx = b.new_context(viewport={'width': 1600, 'height': 950})
    pg = ctx.new_page()
    pg.on('pageerror', lambda e: errs.append(str(e)[:200]))

    # 1. fresh boot
    pg.goto(IDX.as_uri()); pg.wait_for_timeout(2400)
    s = probe(pg)
    R('F1 初次打开载入示例(3节点,无弹窗)', s['domNodes'] == 3 and not s['dialog']['dialog'], f"nodes={s['domNodes']} dialog={s['dialog']['dialog']}")
    R('F1b 初次打开已自动保存', s['sessionNodes'] == 3 and not s['sessionNull'], s['sessionNodes'])

    # 2. edit: drag n_in +60
    box = pg.evaluate("""() => { var g=document.querySelector('.node[data-id="n_in"]');
      var r=g.getBoundingClientRect(); return {x:r.x+50, y:r.y+8}; }""")
    pg.mouse.move(box['x'], box['y']); pg.mouse.down()
    pg.mouse.move(box['x'] + 60, box['y'], steps=8); pg.mouse.up()
    pg.wait_for_timeout(1800)

    # 3. reload #1 -> dialog VISIBLE
    pg.reload(); pg.wait_for_timeout(2600)
    s = probe(pg)
    d = s['dialog']
    R('F2 刷新后弹出恢复会话(可见)', d['dialog'] and '恢复' in d.get('title', ''), d.get('title'))
    R('F2b 遮罩 fixed 且铺满视口', d.get('pos') == 'fixed' and d['cover']['t'] == 0 and d['cover']['l'] == 0 and d['cover']['w'] >= 1590 and d['cover']['h'] >= 940, d.get('cover'))
    R('F2c 弹窗居中可见', 40 < d['box']['t'] and d['box']['b'] < 910, d.get('box'))
    R('F2d 两个按钮可见', len(d.get('btns', [])) == 2 and all(x['vis'] for x in d['btns']), d.get('btns'))
    R('F2e 不可取消时不显示×', d.get('xVisible') is False, d.get('xVisible'))
    R('F2f 选前画布为空(不自动载入)', s['domNodes'] == 0, s['domNodes'])
    R('F2g 存档未被破坏', s['sessionNodes'] == 3 and s['sessionNull'] is False, f"{s['sessionNodes']}/{s['sessionNull']}")
    pg.screenshot(path=str(OUT / 'fix10_dialog.png'))

    # 4. click 恢复会话
    pg.locator('.modal-footer button:has-text("恢复会话")').click()
    pg.wait_for_timeout(800)
    s = probe(pg)
    R('F3 恢复成功(3节点, n_in x=140)', s['domNodes'] == 3 and s['nInX'] == 140, f"nodes={s['domNodes']} x={s['nInX']}")
    R('F3b 弹窗已关', not s['dialog']['dialog'])
    pg.screenshot(path=str(OUT / 'fix10_restored.png'))

    # 5. reload #2 -> discard
    pg.reload(); pg.wait_for_timeout(2600)
    s = probe(pg)
    R('F4 再次弹出恢复会话', s['dialog']['dialog'], '')
    pg.locator('.modal-footer button:has-text("丢弃")').click()
    pg.wait_for_timeout(1200)
    s = probe(pg)
    R('F4b 丢弃后载入示例(x=80)', s['domNodes'] == 3 and s['nInX'] == 80, f"x={s['nInX']}")

    # 6. guard: reload with dialog open must NOT destroy session
    pg.wait_for_timeout(1400)   # 让示例的自动保存写入
    pg.reload(); pg.wait_for_timeout(2600)        # reload #3 -> dialog
    s0 = probe(pg)
    R('F5 刷新#3 弹出恢复会话', s0['dialog']['dialog'], '')
    pg.reload(); pg.wait_for_timeout(2600)        # reload #4 WITHOUT clicking -> guard
    s = probe(pg)
    R('F5b 连刷守卫：存档未被 null 覆盖', s['sessionNull'] is False and s['sessionNodes'] == 3, f"null={s['sessionNull']} nodes={s['sessionNodes']}")
    R('F5c 连刷后恢复会话仍可弹出', s['dialog']['dialog'] and '恢复' in s['dialog'].get('title', ''), s['dialog'].get('title'))
    pg.locator('.modal-footer button:has-text("恢复会话")').click()
    pg.wait_for_timeout(700)
    R('F5d 恢复后 3 节点', probe(pg)['domNodes'] == 3, '')

    # 7. help modal visible
    pg.locator('#btn-help, button:has-text("帮助")').first.click()
    pg.wait_for_timeout(500)
    s = probe(pg)
    R('F6 帮助弹窗可见', s['dialog']['dialog'] and '帮助' in s['dialog'].get('title', ''), s['dialog'].get('title'))
    pg.screenshot(path=str(OUT / 'fix10_help.png'))
    pg.locator('.modal-footer button:has-text("知道了")').click()
    pg.wait_for_timeout(400)
    R('F6b 帮助可关闭', not probe(pg)['dialog']['dialog'], '')

    # 8. 新建 confirm (cancel path)
    pg.locator('button:has-text("新建")').first.click()
    pg.wait_for_timeout(500)
    s = probe(pg)
    R('F7 清空弹窗可见', s['dialog']['dialog'], s['dialog'].get('title'))
    pg.locator('.modal-footer button:has-text("取消")').first.click()
    pg.wait_for_timeout(400)
    s = probe(pg)
    R('F7b 取消后画布未动(3节点)', s['domNodes'] == 3 and not s['dialog']['dialog'], s['domNodes'])

    R('F8 全程无页面错误', len(errs) == 0, '; '.join(errs[:3]))
    b.close()

fails = [r for r in results if not r[1]]
print('=' * 52)
print('FIX10 SUMMARY: %d/%d passed' % (len(results) - len(fails), len(results)))
for r in fails:
    print(' FAIL:', r[0], '|', r[2])
