# -*- coding: utf-8 -*-
"""v3 失败诊断：System 全局 / SystemModules / __qa.findByName 对 UI 根节点 / 序列化限制"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "harness"))
import e2e_login as base  # noqa: E402
from e2e_fabao import qa, texts, shot, wait_main_city, open_via_qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ACCOUNT = os.environ.get("QA_ACCOUNT", "1353")
GAME_URL = "http://localhost:7456"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1280, "height": 720})
    page = context.new_page()
    try:
        page.add_init_script(f"() => {{ try {{ localStorage.setItem('TMP_ACCOUNT_', '{ACCOUNT}'); }} catch(e) {{}} }}")
        page.goto(f"{GAME_URL}/?qa=1", wait_until="domcontentloaded", timeout=60_000)
        base.wait_qa_bridge(page)
        page.wait_for_timeout(4000)
        base.force_select_server(page, 5, "S5")
        page.reload(wait_until="domcontentloaded", timeout=60_000)
        base.wait_qa_bridge(page)
        page.wait_for_timeout(3000)
        page.wait_for_function("() => window.__qa.findByName('LoginBtn_').length > 0", timeout=60_000)
        page.evaluate("() => window.__qa.findByName('LoginBtn_').forEach(n => window.__qa.clickNode(n))")
        wait_main_city(page)
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)

        diag = {}
        # 1) 全局可用性（全部返回可序列化原语）
        diag["globals"] = qa(page, """() => {
          const out = { hasSystem: typeof System, hasSM: typeof window.SystemModules, hasQa: typeof window.__qa };
          try { out.systemProto = Object.getOwnPropertyNames(System).slice(0, 10); } catch (e) { out.systemErr = String(e); }
          try { out.smKeys = Object.keys(window.SystemModules || {}).slice(0, 40); } catch (e) { out.smErr = String(e); }
          return out;
        }""", {})
        # 2) System.entries() 仅取 key（原语）
        diag["entries"] = qa(page, """() => {
          const out = {};
          try { const it = [...System.entries()]; out.count = it.length; out.first = it.slice(0, 8).map(e => e[0]); }
          catch (e) { out.err = String(e); }
          try { out.hasShareRes = [...System.entries()].some(([k, v]) => /ShareRes/.test(k)); }
          catch (e) { out.err2 = String(e); }
          return out;
        }""", {})
        # 3) ShareRes 直接从 entries 拿 cfg（不返回对象本身）
        diag["shareRes"] = qa(page, """() => {
          try {
            for (const [k, v] of System.entries()) {
              if (/utils\\/ShareRes\\.ts/.test(k) && v && v.ShareRes) {
                return { key: k, baseCount: Object.keys(v.ShareRes.cfg_soul_ring_base || {}).length, poolLv: typeof v.ShareRes.cfg_soul_ring_pool_lv_desc };
              }
            }
            return { found: false };
          } catch (e) { return { err: String(e) }; }
        }""", {})
        # 4) 打开图鉴 → findByName 根节点
        opened = open_via_qa(page, "UISoulRingAtlas")
        page.wait_for_timeout(1500)
        diag["atlas_open"] = opened
        diag["qa_caps"] = qa(page, "() => Object.keys(window.__qa)", [])
        diag["findRoot"] = qa(page, """() => {
          const Q = window.__qa; const out = {};
          for (const nm of ['UISoulRingAtlas', 'Atlas', 'UIAtlas']) {
            try { const r = Q.findByName(nm); out[nm] = r ? r.length : -1; } catch (e) { out[nm] = 'ERR:' + e; }
          }
          try { out.uiActive = Q.uiActive('UISoulRingAtlas'); } catch (e) { out.uiActive = String(e); }
          return out;
        }""", {})
        # 5) dumpUITree 里图鉴相关节点名样本
        tree = texts(page)
        diag["tree_total"] = len(tree)
        names = []
        for e in tree[:400]:
            n = e.get("name")
            if n and n not in names:
                names.append(n)
        diag["tree_names_sample"] = names[:40]
        # 6) 序列化测试：返回包含函数的对象是否报错
        diag["serialize_fn"] = qa(page, """() => {
          try { for (const [k, v] of System.entries()) { if (/Util/.test(k)) return { key: k, hasUtil: !!(v && v.Util) }; } return { none: true };
          } catch (e) { return { err: String(e) }; }
        }""", {})
        diag["serialize_obj_throw"] = None
        try:
            page.evaluate("""() => { for (const [k, v] of System.entries()) { if (/utils\\/Util\\.ts/.test(k)) return { m: v }; } return null; }""")
            diag["serialize_obj_throw"] = "no-throw"
        except Exception as e:  # noqa: BLE001
            diag["serialize_obj_throw"] = f"THROWS: {str(e)[:120]}"
        print(json.dumps(diag, ensure_ascii=False, indent=1))
        shot(page, Path(ROOT / "reports" / "e2e_fabao_v3_latest"), "diag_atlas")
    finally:
        browser.close()
