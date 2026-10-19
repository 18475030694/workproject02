# -*- coding: utf-8 -*-
"""
1353 GM 原子验证：登录 -> 读 uuid -> GM set_mainline_stage -> 同会话检查 isSysOpen(8/9)
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "harness"))
import e2e_login as base  # noqa: E402
from e2e_fabao import qa, wait_main_city  # noqa: E402

from playwright.sync_api import sync_playwright  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ACCOUNT = os.environ.get("QA_ACCOUNT", "1353")
GAME_URL = (os.environ.get("GAME_URL", "http://localhost:7456")).rstrip("/")
GM_HOST = os.environ.get("GM_HOST", "192.168.*.*")
GM_PORT = int(os.environ.get("GM_PORT", "6011"))


def gm_get(cmd, params):
    url = f"http://{GM_HOST}:{GM_PORT}/index/{cmd}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:  # noqa: BLE001
        return f"[ERROR] {e}"


def state(page):
    return qa(page, """() => {
      const out = {};
      const SM = window.SystemModules;
      try { const s = SM.sysOpenMgr;
        out.is8 = s.isSysOpen(8); out.is9 = s.isSysOpen(9); out.is174 = s.isSysOpen(174);
        out.openMap = s.opendSysMap ? Array.from((s.opendSysMap.keys ? s.opendSysMap.keys() : Object.keys(s.opendSysMap))) : null;
      } catch(e) { out.err = String(e); }
      try { const m = SM.mainLevelMgr; out.mainKeys = Object.keys(m).filter(k => /pass|stage|chapter/i.test(k)); } catch(e) {}
      try { const g = window.__GAME__; out.uuid = g.playerUuid; } catch(e) {}
      return out;
    }""")


def run():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / "reports" / f"e2e_fabao_1353_gm2_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)
    result = {"ts": ts, "steps": []}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()
        try:
            page.add_init_script(f"() => {{ try {{ localStorage.setItem('TMP_ACCOUNT_', '{ACCOUNT}'); }} catch(e) {{}} }}")
            page.goto(f"{GAME_URL}/?qa=1", wait_until="domcontentloaded", timeout=60_000)
            base.wait_qa_bridge(page)
            page.wait_for_timeout(5000)
            base.force_select_server(page, 5, "S5")
            page.reload(wait_until="domcontentloaded", timeout=60_000)
            base.wait_qa_bridge(page)
            page.wait_for_timeout(3000)
            page.wait_for_function("() => window.__qa.findByName('LoginBtn_').length > 0", timeout=60_000)
            page.evaluate("() => window.__qa.findByName('LoginBtn_').forEach(n => window.__qa.clickNode(n))")
            ok = wait_main_city(page)
            print("login:", ok)
            s0 = state(page)
            print("登录后状态:", json.dumps(s0, ensure_ascii=False))
            result["steps"].append({"step": "after_login", "state": s0})
            uuid = s0.get("uuid")
            print("uuid =", uuid)

            # GM 主线通关 40
            resp = gm_get("set_mainline_stage", {"uuid": uuid, "stage_id": 40})
            print("GM set_mainline_stage(40):", resp[:200])
            result["steps"].append({"step": "gm", "uuid": uuid, "resp": resp[:300]})

            page.wait_for_timeout(4000)
            s1 = state(page)
            print("GM后状态:", json.dumps(s1, ensure_ascii=False))
            result["steps"].append({"step": "after_gm", "state": s1})

            (out_dir / "report.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
            print("报告:", out_dir / "report.json")
        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    run()
