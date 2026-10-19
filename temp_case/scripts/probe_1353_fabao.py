# -*- coding: utf-8 -*-
"""
1353 账号环境探针：登录 → 取角色 uuid → 查法宝(魂环)系统开启状态 → 尝试打开法宝界面
产物: reports/e2e_fabao_1353_probe_<ts>/
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "harness"))
import e2e_login as base  # noqa: E402
from e2e_fabao import qa, texts, shot, wait_main_city, open_via_qa, ui_open  # noqa: E402

from playwright.sync_api import sync_playwright  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ACCOUNT = os.environ.get("QA_ACCOUNT", "1353")
SERVER = os.environ.get("SERVER", "s5服")
GAME_URL = (os.environ.get("GAME_URL", "http://localhost:7456")).rstrip("/")
HEADLESS = os.environ.get("HEADED", "0") != "1"
SVR_ID = int(os.environ.get("SVR_ID", "5"))
SVR_NAME = os.environ.get("SVR_NAME", "S5")


def run():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / "reports" / f"e2e_fabao_1353_probe_{ts}"
    (out_dir / "screenshots").mkdir(parents=True, exist_ok=True)
    result = {"account": ACCOUNT, "server": SERVER, "ts": ts, "info": {}}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()
        try:
            page.add_init_script(f"() => {{ try {{ localStorage.setItem('TMP_ACCOUNT_', '{ACCOUNT}'); }} catch(e) {{}} }}")
            page.goto(f"{GAME_URL}/?qa=1", wait_until="domcontentloaded", timeout=60_000)
            base.wait_qa_bridge(page)
            page.wait_for_timeout(5000)
            base.force_select_server(page, SVR_ID, SVR_NAME)
            page.reload(wait_until="domcontentloaded", timeout=60_000)
            base.wait_qa_bridge(page)
            page.wait_for_timeout(3000)
            page.wait_for_function("() => window.__qa.findByName('LoginBtn_').length > 0", timeout=60_000)
            page.evaluate("() => window.__qa.findByName('LoginBtn_').forEach(n => window.__qa.clickNode(n))")
            ok = wait_main_city(page)
            print("登录:", "PASS" if ok else "FAIL")
            shot(page, out_dir, "00_main_city")
            if not ok:
                raise RuntimeError("登录失败")

            # 1) playerMgr 全字段 dump（找 uuid/roleid）
            pm = qa(page, """() => {
              const PM = window.SystemModules && window.SystemModules.playerMgr;
              if (!PM) return null;
              const out = {};
              for (const k of Object.keys(PM)) {
                try { const v = PM[k]; if (v !== null && typeof v !== 'function') out[k] = String(v).slice(0, 60); } catch(e) {}
              }
              return out;
            }""")
            result["info"]["playerMgr"] = pm
            print("playerMgr 字段:", json.dumps(pm, ensure_ascii=False)[:600])

            # 2) 系统开启管理器（找 8=魂环/法宝 的开启状态）
            sysinfo = qa(page, """() => {
              const SM = window.SystemModules; if (!SM) return null;
              const out = { mods: Object.keys(SM).slice(0, 200) };
              for (const name of Object.keys(SM)) {
                try {
                  const m = SM[name];
                  if (/open|sys/i.test(name) && m && typeof m === 'object') {
                    for (const k of Object.keys(m)) {
                      if (/isOpen|openList|sysOpen|openMap/i.test(k)) {
                        try { out[name + '.' + k] = JSON.stringify(m[k]).slice(0, 400); } catch(e) {}
                      }
                    }
                  }
                } catch(e) {}
              }
              return out;
            }""")
            result["info"]["system_modules"] = sysinfo
            (out_dir / "system_modules.json").write_text(
                json.dumps(sysinfo, ensure_ascii=False, indent=1), encoding="utf-8")
            print("SystemModules 数量:", len((sysinfo or {}).get("mods", [])))

            # 3) 尝试打开法宝主界面
            for ui in ("UISoulRing", "UISoulRingDrawTabView", "UISoulRingAtlas"):
                ok = open_via_qa(page, ui)
                tx = texts(page)
                all_text = " ".join(str(e.get("text")) for e in tx if e.get("text"))
                print(f"openUI({ui}):", "OK" if ok else "FAIL",
                      "| 文案样本:", all_text[:120])
                shot(page, out_dir, f"01_open_{ui}")
                result["info"][f"open_{ui}"] = {"ok": bool(ok), "text": all_text[:400]}
                page.wait_for_timeout(800)
            (out_dir / "report.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
            print("报告:", out_dir / "report.json")
        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    run()
