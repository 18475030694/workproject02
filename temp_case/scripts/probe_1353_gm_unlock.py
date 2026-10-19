# -*- coding: utf-8 -*-
"""
1353 环境准备：登录 → 取 uuid → GM(set_mainline_stage) 解锁法宝(魂环)系统 → 重登验证
产物: reports/e2e_fabao_1353_gm_<ts>/
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
from e2e_fabao import qa, texts, shot, wait_main_city, open_via_qa  # noqa: E402

from playwright.sync_api import sync_playwright  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ACCOUNT = os.environ.get("QA_ACCOUNT", "1353")
SERVER = os.environ.get("SERVER", "s5服")
GAME_URL = (os.environ.get("GAME_URL", "http://localhost:7456")).rstrip("/")
HEADLESS = os.environ.get("HEADED", "0") != "1"
SVR_ID = int(os.environ.get("SVR_ID", "5"))
SVR_NAME = os.environ.get("SVR_NAME", "S5")
GM_HOST = os.environ.get("GM_HOST", "192.168.*.*")
GM_PORT = int(os.environ.get("GM_PORT", "6011"))
STAGE = os.environ.get("GM_STAGE", "30")


def gm_get(cmd, params):
    url = f"http://{GM_HOST}:{GM_PORT}/index/{cmd}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:  # noqa: BLE001
        return f"[ERROR] {e}"


def do_login(page):
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
    return wait_main_city(page)


def run():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / "reports" / f"e2e_fabao_1353_gm_{ts}"
    (out_dir / "screenshots").mkdir(parents=True, exist_ok=True)
    result = {"account": ACCOUNT, "server": SERVER, "ts": ts, "gm": {}, "verify": {}}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()
        try:
            ok = do_login(page)
            print("第一次登录:", "PASS" if ok else "FAIL")
            if not ok:
                raise RuntimeError("登录失败")
            uuid = qa(page, "() => window.__GAME__ && window.__GAME__.playerUuid")
            print("playerUuid =", uuid)
            result["uuid"] = uuid

            # GM: 设置主线关卡（满足 魂环系统 条件 2,19）
            resp = gm_get("set_mainline_stage", {"uuid": uuid, "stage_id": STAGE})
            print(f"GM set_mainline_stage({STAGE}) ->", resp[:200])
            result["gm"]["set_mainline_stage"] = resp[:300]

            # 重登验证
            page.wait_for_timeout(2000)
            ok2 = do_login(page)
            print("重登:", "PASS" if ok2 else "FAIL")
            shot(page, out_dir, "00_relogin")

            for ui in ("UISoulRing", "UISoulRingDrawTabView", "UISoulRingAtlas", "UIGM"):
                ok3 = open_via_qa(page, ui)
                tx = " ".join(str(e.get("text")) for e in texts(page) if e.get("text"))
                print(f"openUI({ui}):", "OK" if ok3 else "FAIL")
                result["verify"][ui] = bool(ok3)
                shot(page, out_dir, f"01_{ui}")
                page.wait_for_timeout(800)
            (out_dir / "report.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
            print("报告:", out_dir / "report.json")
        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    run()
