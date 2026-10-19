# -*- coding: utf-8 -*-
"""临时探针：dump背包结构（只读，不改项目）"""
import sys, io, os, json, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
ROOT = r'E:\workproject'
sys.path.insert(0, os.path.join(ROOT, 'harness'))
import e2e_login as base
from playwright.sync_api import sync_playwright

JS = """
window.__G = () => { for (const [k, v] of System.entries()) { if (v && v.Global && v.Global.uiMgr) return v.Global; } return null; };
"""

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1280, "height": 720})
    page = ctx.new_page()
    try:
        page.goto("http://localhost:7456/?qa=1", wait_until="domcontentloaded", timeout=60_000)
        base.wait_qa_bridge(page)
        page.wait_for_timeout(5000)
        page.evaluate("() => { try { localStorage.setItem('TMP_ACCOUNT_', '4451'); } catch(e) {} }")
        base.force_select_server(page, 5, "S5")
        page.reload(wait_until="domcontentloaded", timeout=60_000)
        base.wait_qa_bridge(page)
        page.wait_for_timeout(3000)
        page.wait_for_function("() => window.__qa.findByName('LoginBtn_').length > 0", timeout=90_000)
        page.evaluate("() => window.__qa.findByName('LoginBtn_').forEach(n => window.__qa.clickNode(n))")
        t0 = time.time()
        while time.time() - t0 < 150:
            if page.evaluate("() => window.__qa && window.__qa.isReady()") and \
               not page.evaluate("() => window.__qa.uiActive('UILoading')"):
                break
            page.wait_for_timeout(2000)
        page.wait_for_timeout(3000)
        page.evaluate(JS)

        print('uiActive UIBag:', page.evaluate("() => window.__qa.uiActive('UIBag')"))
        r = page.evaluate("() => { try { window.__G().uiMgr.getUI('UIBag').showUI(); return true; } catch(e){ return 'ERR:'+e; } }")
        print('open UIBag:', r)
        page.wait_for_timeout(2500)
        print('uiActive UIBag:', page.evaluate("() => window.__qa.uiActive('UIBag')"))

        # 全场景文本中找已知道具名
        ents = page.evaluate("() => window.__qa.dumpUITree('')") or []
        names = ['灵力', '凡灵召符', '武器零件', '炼宝玉佩', '战车突击']
        for nm in names:
            hits = [e for e in ents if str(e.get('text') or '') == nm]
            print(f'text {nm}: {len(hits)} hits', (hits[0] if hits else '') )

        # findByName 探查
        for nm in ['UIBag', 'UIItemWithName', 'ItemName', 'NameTxt']:
            ps = page.evaluate(f"() => window.__qa.findByName('{nm}')") or []
            print(f'findByName {nm}: {len(ps)}', ps[:3])

        # dump UIBag 路径样例
        ents2 = page.evaluate("() => window.__qa.dumpUITree('UIBag')") or []
        print('UIBag filter entries:', len(ents2))
        for e in ents2[:40]:
            print('  ', e.get('name'), '|', str(e.get('text') or '')[:24], '|', str(e.get('path'))[:110])
    finally:
        browser.close()
