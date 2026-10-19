# -*- coding: utf-8 -*-
"""探针: 运行时枚举 cfg_item_source 中 title 含「挂机」的条目 → 找可做A3回归的道具（含背包数量）"""
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "harness"))
import e2e_login as base  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

ACCOUNT = os.environ.get("QA_ACCOUNT", "4451")
GAME_URL = os.environ.get("GAME_URL", "http://localhost:7456").rstrip("/")
SVR_ID = int(os.environ.get("SVR_ID", "5"))
SVR_NAME = os.environ.get("SVR_NAME", "S5")

JS_HEAD = """
window.__G = () => { for (const [k, v] of System.entries()) { if (v && v.Global && v.Global.uiMgr) return v.Global; } return null; };
window.__SHARE = () => { for (const [k, v] of System.entries()) { if (v && v.ShareRes && v.ShareRes.cfg_sys_jump) return v.ShareRes; } return null; };
window.__ITEM = (id) => { try { return SystemModules.knapsackMgr.getItemCount(id); } catch (e) { return -1; } };
"""

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_context(viewport={"width": 1280, "height": 720}).new_page()
    try:
        page.goto(f"{GAME_URL}/?qa=1", wait_until="domcontentloaded", timeout=60_000)
        base.wait_qa_bridge(page)
        page.wait_for_timeout(5000)
        page.evaluate(f"() => {{ try {{ localStorage.setItem('TMP_ACCOUNT_', '{ACCOUNT}'); }} catch(e) {{}} }}")
        base.force_select_server(page, SVR_ID, SVR_NAME)
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
        page.evaluate(JS_HEAD)
        r = page.evaluate("""() => {
          const S = window.__SHARE();
          const out = { guaji: [], jump10: null };
          const j = S.cfg_sys_jump['10'];
          out.jump10 = j ? { ui_name: j.ui_name, name: j.name } : null;
          for (const iid in S.cfg_item_source) {
            const grp = S.cfg_item_source[iid];
            for (const idx in grp) {
              const e = grp[idx];
              if (e && e.title && String(e.title).includes('挂机')) {
                out.guaji.push({ itemId: Number(iid), idx: Number(idx), title: e.title,
                                 goWin: e.goWin, cnt: window.__ITEM(Number(iid)) });
              }
            }
          }
          return out;
        }""")
        print(json.dumps(r, ensure_ascii=False, indent=1))
    finally:
        browser.close()
