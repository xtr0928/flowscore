# -*- coding: utf-8 -*-
"""fix11 验收：空白处手势（左键拖=平移 / Ctrl拖=框选 / 右键拖=平移 / 空白单击=清空选择）
+ 新快捷键 Ctrl+A/S/E/X/0 + 回归（节点拖动、右键菜单、中键/空格平移）。"""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

IDX = Path(r"D:\XTR-projects\pipeline-orchestrator\index.html")
OUT = Path(r"C:\Users\XXQ0928\AppData\Local\hermes\cache\scratch\idx_browser")
EXP = OUT / 'exports_fix11'; EXP.mkdir(parents=True, exist_ok=True)

results = []
def R(name, ok, detail=''):
    results.append((name, ok, str(detail)[:220]))
    print(('PASS ' if ok else 'FAIL ') + name + (' | ' + str(detail)[:220] if detail else ''))

def blank_point(pg):
    return pg.evaluate("""() => {
      var s=document.getElementById('canvas'); var r=s.getBoundingClientRect();
      var cands=[[r.left+r.width*0.5,r.top+r.height*0.8],[r.left+r.width*0.5,r.top+r.height*0.15],
                 [r.left+r.width*0.08,r.top+r.height*0.92],[r.left+r.width*0.9,r.top+r.height*0.9],
                 [r.left+r.width*0.3,r.top+r.height*0.85]];
      for(var i=0;i<cands.length;i++){
        var x=cands[i][0],y=cands[i][1];
        var el=document.elementFromPoint(x,y);
        if(el&&!(el.closest&&el.closest('.node,.port,g.edge'))) return {x:Math.round(x),y:Math.round(y)};
      }
      return null; }""")

def tf(pg):
    return pg.evaluate("() => { var t=XTR.view.getTransform(); return {x:Math.round(t.x*100)/100,y:Math.round(t.y*100)/100,k:Math.round(t.k*1000)/1000}; }")

def seln(pg):
    return pg.evaluate("() => XTR.view.getSelection().nodes.length")

errs = []
with sync_playwright() as p:
    b = p.chromium.launch(channel='msedge', args=['--allow-file-access-from-files'])
    pg = b.new_context(viewport={'width': 1600, 'height': 950}).new_page()
    pg.on('pageerror', lambda e: errs.append(str(e)[:200]))
    pg.goto(IDX.as_uri()); pg.wait_for_timeout(2300)

    # T1 空白左键拖拽 = 平移（整体移动）
    bl = blank_point(pg)
    t0 = tf(pg)
    r0 = pg.evaluate("() => { var g=document.querySelector('.node[data-id=\"n_in\"]'); var r=g.getBoundingClientRect(); return {x:Math.round(r.x),y:Math.round(r.y)}; }")
    pg.mouse.move(bl['x'], bl['y']); pg.mouse.down()
    pg.mouse.move(bl['x'] + 120, bl['y'] + 60, steps=12); pg.mouse.up()
    pg.wait_for_timeout(250)
    t1 = tf(pg)
    r1 = pg.evaluate("() => { var g=document.querySelector('.node[data-id=\"n_in\"]'); var r=g.getBoundingClientRect(); return {x:Math.round(r.x),y:Math.round(r.y)}; }")
    R('T1 空白拖拽=平移 (Δ120,60)', abs(t1['x'] - t0['x'] - 120) < 3 and abs(t1['y'] - t0['y'] - 60) < 3, f"{t0}->{t1}")
    R('T1b 节点同步整体移动', abs(r1['x'] - r0['x'] - 120) < 3 and abs(r1['y'] - r0['y'] - 60) < 3, f"{r0}->{r1}")
    R('T1c 无框选残留', pg.evaluate("() => document.querySelectorAll('.sel-box').length") == 0)
    pg.screenshot(path=str(OUT / 'fix11_pan.png'))

    # T2 选中节点后，空白单击=清空选择
    pg.locator('.node[data-id="n_in"]').first.click(position={'x': 50, 'y': 8})
    pg.wait_for_timeout(250)
    R('T2 点击节点可选中', seln(pg) == 1, seln(pg))
    bl = blank_point(pg)
    pg.mouse.move(bl['x'], bl['y']); pg.mouse.down(); pg.mouse.up()
    pg.wait_for_timeout(250)
    R('T2b 空白单击清空选择', seln(pg) == 0, seln(pg))

    # T3 Ctrl+空白拖拽 = 框选（框住全部 3 节点）
    pg.evaluate("() => XTR.view.fitToContent()")
    pg.wait_for_timeout(200)
    corners = pg.evaluate("""() => {
      var s=document.getElementById('canvas'); var r=s.getBoundingClientRect();
      var a=XTR.view.worldToScreen(-120,110), b=XTR.view.worldToScreen(1080,500);
      return {a:{x:Math.max(r.left+6,a.x),y:Math.max(r.top+6,a.y)}, b:{x:Math.min(r.right-6,b.x),y:Math.min(r.bottom-6,b.y)}}; }""")
    ta = tf(pg)
    pg.keyboard.down('Control')
    pg.mouse.move(corners['a']['x'], corners['a']['y']); pg.mouse.down()
    pg.mouse.move(corners['b']['x'], corners['b']['y'], steps=14)
    mid = pg.evaluate("() => document.querySelectorAll('.sel-box').length")
    pg.screenshot(path=str(OUT / 'fix11_box.png'))
    pg.mouse.up(); pg.keyboard.up('Control')
    pg.wait_for_timeout(300)
    tb = tf(pg)
    R('T3 Ctrl拖拽出现框选矩形', mid >= 1, f'sel-box={mid}')
    R('T3b 框选选中 3 节点', seln(pg) == 3, seln(pg))
    R('T3c 框选不移动画布', abs(tb['x'] - ta['x']) < 0.5 and abs(tb['y'] - ta['y']) < 0.5, f"{ta}->{tb}")
    R('T3d 框选矩形已清理', pg.evaluate("() => document.querySelectorAll('.sel-box').length") == 0)

    # T4 中键拖拽=平移
    bl = blank_point(pg); t0 = tf(pg)
    pg.mouse.move(bl['x'], bl['y']); pg.mouse.down(button='middle')
    pg.mouse.move(bl['x'] + 80, bl['y'] - 40, steps=8); pg.mouse.up(button='middle')
    pg.wait_for_timeout(200); t1 = tf(pg)
    R('T4 中键拖拽=平移 (Δ80,-40)', abs(t1['x'] - t0['x'] - 80) < 3 and abs(t1['y'] - t0['y'] + 40) < 3, f"{t0}->{t1}")

    # T5 空格+左键拖拽=平移
    bl = blank_point(pg); t0 = tf(pg)
    pg.keyboard.down(' ')
    pg.mouse.move(bl['x'], bl['y']); pg.mouse.down()
    pg.mouse.move(bl['x'] - 60, bl['y'] + 30, steps=8); pg.mouse.up()
    pg.keyboard.up(' ')
    pg.wait_for_timeout(200); t1 = tf(pg)
    R('T5 空格+拖拽=平移 (Δ-60,30)', abs(t1['x'] - t0['x'] + 60) < 3 and abs(t1['y'] - t0['y'] - 30) < 3, f"{t0}->{t1}")

    # T6 空白右键拖拽=平移，且不弹菜单
    bl = blank_point(pg); t0 = tf(pg)
    pg.mouse.move(bl['x'], bl['y']); pg.mouse.down(button='right')
    pg.mouse.move(bl['x'] + 70, bl['y'] + 50, steps=10); pg.mouse.up(button='right')
    pg.wait_for_timeout(400); t1 = tf(pg)
    R('T6 右键拖拽=平移 (Δ70,50)', abs(t1['x'] - t0['x'] - 70) < 4 and abs(t1['y'] - t0['y'] - 50) < 4, f"{t0}->{t1}")
    R('T6b 拖拽后不弹菜单', pg.evaluate("() => !!document.querySelector('.ctx-menu')") is False)

    # T7 空白右键单击（无拖动）→ 菜单照常
    bl = blank_point(pg)
    pg.mouse.click(bl['x'], bl['y'], button='right'); pg.wait_for_timeout(350)
    menu = pg.evaluate("() => { var m=document.querySelector('.ctx-menu'); return m? m.innerText.replace(/\\s+/g,' '):''; }")
    R('T7 右键单击弹菜单(含适应画布)', '适应画布' in menu, menu[:80])
    pg.screenshot(path=str(OUT / 'fix11_ctx.png'))
    pg.keyboard.press('Escape'); pg.wait_for_timeout(200)
    R('T7b Esc 关闭菜单', pg.evaluate("() => !!document.querySelector('.ctx-menu')") is False)

    # T8 节点右键菜单仍有
    nb = pg.evaluate("() => { var g=document.querySelector('.node[data-id=\"n_model\"]'); var r=g.getBoundingClientRect(); return {x:r.x+r.width/2,y:r.y+10}; }")
    pg.mouse.click(nb['x'], nb['y'], button='right'); pg.wait_for_timeout(350)
    menu2 = pg.evaluate("() => { var m=document.querySelector('.ctx-menu'); return m? m.innerText.replace(/\\s+/g,' '):''; }")
    R('T8 节点右键菜单(含删除节点)', '删除节点' in menu2, menu2[:80])
    pg.keyboard.press('Escape'); pg.wait_for_timeout(200)

    # T9 节点左键拖拽仍可移动（回归）
    pg.locator('.node[data-id="n_model"]').first.click(position={'x': 50, 'y': 8})
    pg.wait_for_timeout(200)
    nb = pg.evaluate("() => { var g=document.querySelector('.node[data-id=\"n_model\"]'); var r=g.getBoundingClientRect(); return {x:r.x+50,y:r.y+8}; }")
    pg.mouse.move(nb['x'], nb['y']); pg.mouse.down()
    pg.mouse.move(nb['x'] + 40, nb['y'], steps=6); pg.mouse.up()
    pg.wait_for_timeout(300)
    nx = pg.evaluate("() => XTR.graph.getDocs().layout.nodes['n_model'].x")
    R('T9 节点拖动仍正常 (400->440)', nx == 440, nx)

    # T10 快捷键：Ctrl+0 / Ctrl+A / Ctrl+S / Ctrl+E / Ctrl+X(+undo)
    bl = blank_point(pg)
    pg.mouse.move(bl['x'], bl['y']); pg.mouse.wheel(0, -300)
    pg.wait_for_timeout(250)
    k0 = tf(pg)['k']
    pg.keyboard.press('Control+0'); pg.wait_for_timeout(250)
    R('T10 Ctrl+0 缩放复位 100%', abs(tf(pg)['k'] - 1) < 0.001 and k0 != 1, f"k {k0}->{tf(pg)['k']}")

    pg.keyboard.press('Control+a'); pg.wait_for_timeout(250)
    R('T10b Ctrl+A 全选 3 节点', seln(pg) == 3, seln(pg))

    pg.keyboard.press('Control+s'); pg.wait_for_timeout(400)
    R('T10c Ctrl+S 手动保存提示', '已手动保存' in pg.evaluate("() => document.body.innerText"), '')

    try:
        with pg.expect_download(timeout=6000) as dl:
            pg.keyboard.press('Control+e')
        fn = dl.value.suggested_filename
        dl.value.save_as(EXP / fn)
        R('T10d Ctrl+E 导出管线', 'pipeline' in fn, fn)
    except Exception as ex:
        R('T10d Ctrl+E 导出管线', False, str(ex)[:120])

    pg.keyboard.press('Control+a'); pg.wait_for_timeout(150)
    pg.keyboard.press('Control+x'); pg.wait_for_timeout(400)
    cut = pg.evaluate("() => document.querySelectorAll('.node[data-id]').length")
    pg.keyboard.press('Control+z'); pg.wait_for_timeout(400)
    und = pg.evaluate("() => document.querySelectorAll('.node[data-id]').length")
    R('T10e Ctrl+X 剪切(3->0) 且 Ctrl+Z 可恢复', cut == 0 and und == 3, f"cut={cut} undo={und}")

    R('T11 全程无页面错误', len(errs) == 0, '; '.join(errs[:3]))
    b.close()

fails = [r for r in results if not r[1]]
print('=' * 52)
print('FIX11 SUMMARY: %d/%d passed' % (len(results) - len(fails), len(results)))
for r in fails:
    print(' FAIL:', r[0], '|', r[2])
