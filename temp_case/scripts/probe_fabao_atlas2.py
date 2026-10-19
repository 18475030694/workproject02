# -*- coding: utf-8 -*-
"""图鉴/详情运行时探针 v2：干净环境下按节点结构取证（按钮数/点击item/真实文案/池等级/Util行为）"""
import json, os, sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "harness"))
import e2e_login as base
from e2e_fabao import qa, texts, shot, wait_main_city, open_via_qa
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
ACCOUNT = os.environ.get("QA_ACCOUNT", "1351")
SVR_ID = int(os.environ.get("SVR_ID", "5"))
SVR_NAME = os.environ.get("SVR_NAME", "S5")
GAME_URL = "http://localhost:7456"


def run():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / "reports" / f"e2e_fabao_probe2_{ts}"
    (out_dir / "screenshots").mkdir(parents=True, exist_ok=True)
    errs = []
    result = {"ts": ts}

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

            # 1) Util 模块行为 + pool_level
            probe = qa(page, """() => {
              const out = {};
              try {
                let util = null;
                for (const [k, v] of System.entries()) {
                  try { if (v && v.Util && v.Util.formatLevel) { util = v.Util; out.key = k.slice(-60); break; } } catch (e) {}
                }
                if (util) {
                  out.fmtLevel_50_6001 = util.formatLevel(50, 6001).str;
                  out.fmtLevel_150_6031 = util.formatLevel(150, 6031).str;
                  out.fmtYear_1000 = util.formatYear(1000, 6001).str;
                } else { out.utilFound = false; }
              } catch (e) { out.err = String(e).slice(0, 120); }
              try {
                const M = window.SystemModules;
                out.pool_level = M.soulRingMgr.pool_level;
                out.initial_6001 = M.soulRingMgr.getInitialLevel(6001);
                out.ringMap_6001 = !!M.soulRingMgr.ringMap[6001];
              } catch (e) { out.err2 = String(e).slice(0, 120); }
              return out;
            }""")
            result["probe"] = probe
            print("probe:", json.dumps(probe, ensure_ascii=False))

            # 2) 打开图鉴：统计分类按钮(结构) + 截图
            opened = open_via_qa(page, "UISoulRingAtlas")
            page.wait_for_timeout(1800)
            struct = (qa(page, """() => {
              const Q = window.__qa;
              const roots = Q.findByName('UISoulRingAtlas');
              if (!roots || !roots.length) return {open: false};
              const out = {open: true, togs: [], content: []};
              const walk = (n, d, tag) => {
                if (d > 16) return;
                let kids = [];
                try { kids = (n && n.children) ? Array.from(n.children) : []; } catch (e) { return; }
                for (const c of kids) {
                  try {
                    const nm = c && c.name ? c.name : '';
                    if (nm.indexOf('TogTemp') === 0) {
                      out.togs.push({name: nm, active: c.activeInHierarchy});
                    }
                    if (tag === 'content' && (nm.indexOf('Item') >= 0 || nm.indexOf('item') >= 0)) {
                      out.content.push(nm);
                    }
                    walk(c, d + 1, tag);
                  } catch (e) {}
                }
              };
              try { walk(roots[0], 0, ''); } catch (e) { out.walkErr = String(e).slice(0, 120); }
              return out;
            }""")) or {}
            result["atlas_struct"] = {k: (len(v) if isinstance(v, list) else v) for k, v in struct.items()}
            print("图鉴打开:", opened, "TogTemp按钮数:", len(struct.get("togs", [])))
            shot(page, out_dir, "01_atlas_clean")

            # 3) 点击第一个分类按钮之外，先点图鉴里第一个法宝item按钮（找 Button 节点）
            clicked = qa(page, """() => {
              const Q = window.__qa;
              const roots = Q.findByName('UISoulRingAtlas');
              if (!roots || !roots.length) return {found: false};
              const btns = [];
              const walk = (n, d) => {
                if (d > 18) return;
                let kids = [];
                try { kids = (n && n.children) ? Array.from(n.children) : []; } catch (e) { return; }
                for (const c of kids) {
                  try {
                    if (c.getComponent && c.getComponent('cc.Button') && c.activeInHierarchy) btns.push(c);
                    walk(c, d + 1);
                  } catch (e) {}
                }
              };
              try { walk(roots[0], 0); } catch (e) {}
              // 排除顶部分类按钮（名字含 Tog）后选第一个可点的 item
              const items = btns.filter(b => b.name.indexOf('Tog') < 0);
              const out = {found: items.length, names: items.slice(0, 8).map(b => b.name)};
              if (items.length) { Q.clickNode(items[items.length - 1]); out.clicked = items[items.length - 1].name; }
              return out;
            }""") or {}
            result["atlas_click"] = clicked
            print("点击item:", json.dumps(clicked, ensure_ascii=False)[:200])
            page.wait_for_timeout(2000)
            desc = qa(page, """() => {
              const Q = window.__qa;
              const roots = Q.findByName('UISoulRingAtlasDesc');
              if (!roots || !roots.length) return {open: false};
              const out = {open: true, labels: []};
              const walk = (n, d) => {
                if (d > 16) return;
                let kids = [];
                try { kids = (n && n.children) ? Array.from(n.children) : []; } catch (e) { return; }
                for (const c of kids) {
                  try {
                    const lb = c.getComponent && c.getComponent('cc.Label');
                    const rt = c.getComponent && c.getComponent('cc.RichText');
                    const t = lb ? lb.string : (rt ? rt.string : null);
                    if (t && String(t).trim()) out.labels.push((c.name || '?') + ' = ' + String(t).slice(0, 80));
                    walk(c, d + 1);
                  } catch (e) {}
                }
              };
              try { walk(roots[0], 0); } catch (e) { out.walkErr = String(e).slice(0, 120); }
              return out;
            }""") or {}
            result["atlas_desc"] = desc
            print("详情labels:", len(desc.get("labels", [])))
            for t in (desc.get("labels") or [])[:18]:
                print("  ", t)
            shot(page, out_dir, "02_atlas_desc_real")

            # 4) 关闭详情，点击最后一个分类按钮（仙品/最高档）看锁定提示
            qa(page, "() => { const r = window.__qa.findByName('UISoulRingAtlasDesc'); if (r && r.length) { const b = window.__qa.findByName('BtnBg'); if (b && b.length) window.__qa.clickNode(b[0]); } }")
            page.wait_for_timeout(800)
            tog_click = qa(page, """() => {
              const Q = window.__qa;
              const roots = Q.findByName('UISoulRingAtlas');
              if (!roots || !roots.length) return {found: false};
              const togs = [];
              const walk = (n, d) => {
                if (d > 18) return;
                let kids = [];
                try { kids = (n && n.children) ? Array.from(n.children) : []; } catch (e) { return; }
                for (const c of kids) {
                  try {
                    if (c.name && c.name.indexOf('TogTemp') === 0 && c.activeInHierarchy) togs.push(c);
                    walk(c, d + 1);
                  } catch (e) {}
                }
              };
              try { walk(roots[0], 0); } catch (e) {}
              togs.sort((a, b) => a.name.localeCompare(b.name));
              const out = {count: togs.length, names: togs.map(t => t.name)};
              if (togs.length > 1) { window.__qa.clickNode(togs[togs.length - 1]); out.clicked = togs[togs.length - 1].name; }
              return out;
            }""") or {}
            page.wait_for_timeout(1000)
            tips = [str(e.get("text")) for e in texts(page) if e.get("text") and ("炼宝等级" in str(e.get("text")) or "可查阅" in str(e.get("text")) or "解锁" in str(e.get("text")))]
            result["tog_click"] = tog_click
            result["filter_tips"] = tips
            print("分类按钮:", json.dumps(tog_click, ensure_ascii=False)[:250])
            print("锁定提示:", tips)
            shot(page, out_dir, "03_filter_click")
        except Exception as e:
            result["error"] = str(e)
            raise
        finally:
            result["js_errors_sample"] = errs[-30:]
            (out_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
            browser.close()
    print("报告:", out_dir)
    print("js_errors 总数:", len(errs))
    soul_errs = [e for e in errs if "soul" in e.lower() or "ring" in e.lower() or "索引" in e]
    for e in soul_errs[:8]:
        print("  SOUL_ERR:", e[:180])


if __name__ == "__main__":
    run()
