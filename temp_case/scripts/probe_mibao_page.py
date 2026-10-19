# -*- coding: utf-8 -*-
"""诊断 localhost:7456 页面当前状态"""
import sys
from pathlib import Path
sys.path.insert(0, r"E:\workproject\harness")
import e2e_login as base
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context(viewport={"width": 1280, "height": 720}).new_page()
    pg.goto("http://localhost:7456/?qa=1", wait_until="domcontentloaded", timeout=60_000)
    try:
        base.wait_qa_bridge(pg, timeout_ms=30_000)
        print("qa bridge: OK")
    except Exception as e:
        print("qa bridge: FAIL", e)
    pg.wait_for_timeout(6000)
    for expr, tag in [
        ("() => window.__qa ? window.__qa.isReady() : 'no __qa'", "qaReady"),
        ("() => window.__qa.uiActive('UILoading')", "UILoading"),
        ("() => window.__qa.findByName('LoginBtn_').length", "LoginBtn_ count"),
        ("() => window.__qa.findByName('UIRoot').length", "UIRoot count"),
    ]:
        try:
            print(tag, "=", pg.evaluate(expr))
        except Exception as e:
            print(tag, "ERR", str(e)[:100])
    tx = pg.evaluate("() => { try { return window.__qa.dumpUITree('').slice(0, 40).map(e => (e.path||'') + '|' + (e.text||'')); } catch(e) { return ['ERR:'+e]; } }")
    for t in tx:
        print("  ", t[:120])
    pg.screenshot(path=str(Path(__file__).parent.parent / "reports" / "probe_mibao_page.png"))
    print("shot saved")
    b.close()
