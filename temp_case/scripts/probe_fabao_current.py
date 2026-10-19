# -*- coding: utf-8 -*-
"""运行时代码版本探针：验证客户端实际加载的 Util.formatLevel / formatYear 行为 + 图鉴详情表现"""
import json, os, sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "harness"))
import e2e_login as base
from e2e_fabao import qa, texts, shot, wait_main_city, open_via_qa, ui_open
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
ACCOUNT = os.environ.get("QA_ACCOUNT", "1351")
SVR_ID = int(os.environ.get("SVR_ID", "5"))
SVR_NAME = os.environ.get("SVR_NAME", "S5")
GAME_URL = "http://localhost:7456"


def run():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / "reports" / f"e2e_fabao_current_probe_{ts}"
    (out_dir / "screenshots").mkdir(parents=True, exist_ok=True)
    errs = []
    result = {"ts": ts, "info": {}}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=os.environ.get("HEADED", "0") != "1")
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()
        page.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errs.append(f"pageerror: {e}"))
        try:
            page.add_init_script(f"() => {{ try {{ localStorage.setItem('TMP_ACCOUNT_', '{ACCOUNT}'); }} catch(e) {{}} }}")
            page.goto(f"{GAME_URL}/?qa=1", wait_until="domcontentloaded", timeout=60_000)
            base.wait_qa_bridge(page)
            page.wait_for_timeout(4000)
            base.force_select_server(page, SVR_ID, SVR_NAME)
            page.reload(wait_until="domcontentloaded", timeout=60_000)
            base.wait_qa_bridge(page)
            page.wait_for_timeout(3000)
            page.wait_for_function("() => window.__qa.findByName('LoginBtn_').length > 0", timeout=60_000)
            page.evaluate("() => window.__qa.findByName('LoginBtn_').forEach(n => window.__qa.clickNode(n))")
            ok = wait_main_city(page)
            print("登录:", "PASS" if ok else "FAIL")
            if not ok:
                raise RuntimeError("登录失败")

            # 1) 运行时直接调用 Util.formatLevel / formatYear
            probe = qa(page, """() => {
              const out = {};
              try {
                let utilMod = null;
                for (const [k, v] of System.entries()) {
                  if (/utils\\/Util\\.ts/.test(k) && v && v.Util) { utilMod = v.Util; out.utilKey = k; break; }
                }
                if (!utilMod) { out.utilFound = false; return out; }
                out.utilFound = true;
                out.fmtLevel_50 = utilMod.formatLevel(50, 6001).str;
                out.fmtLevel_150 = utilMod.formatLevel(150, 6031).str;
                out.fmtYear_1000 = utilMod.formatYear(1000, 6001).str;
                out.fmtYear_500000 = utilMod.formatYear(500000, 6001).str;
              } catch (e) { out.err = String(e); }
              try {
                const M = window.SystemModules;
                out.pool_level = M.soulRingMgr.pool_level;
                out.calcFinal_num = M.soulRingMgr.calcRingFinalLV(6001);
                out.initial_6001 = M.soulRingMgr.getInitialLevel(6001);
              } catch (e) { out.err2 = String(e); }
              return out;
            }""")
            result["info"]["probe"] = probe
            print("probe:", json.dumps(probe, ensure_ascii=False))

            # 2) 打开图鉴 → 点第一项 → 看详情 InitYear/Year/特性文本
            opened = open_via_qa(page, "UISoulRingAtlas")
            print("图鉴打开:", opened)
            page.wait_for_timeout(1500)
            clicked = qa(page, """() => {
              const Q = window.__qa;
              const items = Q.findByName('item');
              const tgt = (items && items.length ? items : Q.findByName('RingAtlasItem'));
              if (!tgt || !tgt.length) return {found: false};
              const n = tgt[0];
              const wp = n.worldPosition;
              Q.clickNode(n);
              return {found: true, clicked: n.name, x: wp.x, y: wp.y};
            }""")
            print("点击图鉴项:", clicked)
            page.wait_for_timeout(1500)
            desc = qa(page, """() => {
              const Q = window.__qa;
              const out = {texts: []};
              const roots = Q.findByName('UISoulRingAtlasDesc');
              if (!roots || !roots.length) return {open: false};
              out.open = true;
              const walk = (n, d) => {
                if (d > 14) return;
                for (const c of n.children) {
                  const lb = c.getComponent && c.getComponent('cc.Label');
                  const rt = c.getComponent && c.getComponent('cc.RichText');
                  const t = lb ? lb.string : (rt ? rt.string : null);
                  if (t) out.texts.push((c.name || '?') + ' = ' + String(t).slice(0, 70));
                  walk(c, d + 1);
                }
              };
              walk(roots[0], 0);
              return out;
            }""")
            result["info"]["atlas_desc"] = desc
            for t in (desc.get("texts") or [])[:20]:
                print("  ", t)
            shot(page, out_dir, "01_atlas_desc")
        except Exception as e:
            result["error"] = str(e)
            raise
        finally:
            result["js_errors_sample"] = errs[-25:]
            (out_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
            browser.close()
    print("报告:", out_dir)
    print("js_errors:", len(errs))
    for e in errs[-10:]:
        print("  ERR:", e[:160])


if __name__ == "__main__":
    run()
