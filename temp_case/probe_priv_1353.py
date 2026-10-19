# -*- coding: utf-8 -*-
"""探针：月卡/终身卡测试前置链路验证
1. 登录 1353 (s5服) -> 2. 读 uuid -> 3. sys87 开放状态
4. GM set_mainline_stage=40 -> 5. sys87 是否翻true + 是否弹 UIPrivCard
6. 截图 + UI 树取证
"""
import json
import sys
import time
import requests
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "harness"))
from e2e_login import (  # noqa: E402
    wait_qa_bridge, screenshot, get_player_session, is_in_main_city,
    heuristic_svr_id,
)

GM_BASE = "http://192.168.*.*:6011/index"
OUT = Path(__file__).resolve().parent / "probe_priv_out"
OUT.mkdir(exist_ok=True)
(OUT / "screenshots").mkdir(exist_ok=True)

ACCOUNT = "1353"
SERVER = "s5服"
URL = "http://localhost:7456/?qa=1"


def gm(cmd, **params):
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    r = requests.get(f"{GM_BASE}/{cmd}?{qs}", timeout=15)
    return r.status_code, r.text[:300]


def main():
    result = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(e.message[:200]))

        print("[1] 打开游戏")
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        wait_qa_bridge(page)
        page.wait_for_timeout(8000)

        print("[2] 注入账号+选服")
        hid = heuristic_svr_id(SERVER)
        page.evaluate(f"() => {{ localStorage.setItem('TMP_ACCOUNT_', '{ACCOUNT}'); }}")
        page.evaluate(f"""() => {{
            localStorage.setItem('last_login_server_id', '{hid}');
            localStorage.setItem('last_login_server_name', '{SERVER}');
            localStorage.setItem('selected_server_key', '{hid}');
        }}""")
        page.reload(wait_until="domcontentloaded", timeout=60000)
        wait_qa_bridge(page)
        page.wait_for_timeout(4000)

        print("[3] 点击登录")
        page.wait_for_function("() => window.__qa.findByName('LoginBtn_').length > 0", timeout=60000)
        page.evaluate("() => window.__qa.findByName('LoginBtn_').forEach(n => window.__qa.clickNode(n))")

        print("[4] 等待进主城")
        deadline = time.time() + 120
        while time.time() < deadline and not is_in_main_city(page):
            page.wait_for_timeout(1000)
        print(f"    in_main_city={is_in_main_city(page)}")
        screenshot(page, OUT, "01_in_main_city")

        # 读 uuid（多路径兜底）
        uuid_info = page.evaluate("""() => {
            const out = {};
            try { out.game_uuid = window.__GAME__ && window.__GAME__.playerUuid; } catch(e){}
            try {
                const PM = window.SystemModules && window.SystemModules.playerMgr;
                if (PM) {
                    for (const k of Object.keys(PM)) {
                        if (/uuid|roleid|role_id/i.test(k) && PM[k]) { out.pm_field = k + '=' + PM[k]; break; }
                    }
                }
            } catch(e){}
            return out;
        }""")
        print(f"[5] uuid_info = {uuid_info}")
        result["uuid_info"] = uuid_info
        uuid = None
        if uuid_info.get("game_uuid"):
            uuid = uuid_info["game_uuid"]
        elif uuid_info.get("pm_field"):
            uuid = uuid_info["pm_field"].split("=")[1]
        if not uuid:
            print("!! 无法获取 uuid，中止")
            result["error"] = "no uuid"
            (OUT / "probe.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            return
        result["uuid"] = uuid

        # sys 状态
        sys_before = page.evaluate("""() => {
            const r = {};
            try { r.sys87 = window.SystemModules.sysOpenMgr.isSysOpen(87); } catch(e){ r.sys87 = 'err:'+e.message; }
            try { r.sys39 = window.SystemModules.sysOpenMgr.isSysOpen(39); } catch(e){ r.sys39 = 'err:'+e.message; }
            try { r.sys88 = window.SystemModules.sysOpenMgr.isSysOpen(88); } catch(e){ r.sys88 = 'err:'+e.message; }
            return r;
        }""")
        print(f"[6] GM前 sys状态 = {sys_before}")
        result["sys_before"] = sys_before

        # 特权卡数据
        cards = page.evaluate("""() => {
            try {
                const mgr = window.SystemModules.privilegeMgr;
                const out = [];
                if (mgr && mgr.cardInfoMap) {
                    for (const [k, v] of mgr.cardInfoMap) out.push({card_id: k, buy_time: v.buy_time, expire_time: v.expire_time, buy_times: v.buy_times, daily_reward_state: v.daily_reward_state});
                }
                return out;
            } catch(e){ return 'err:'+e.message; }
        }""")
        print(f"[7] 特权卡数据 = {cards}")
        result["cards_before"] = cards

        # GM 解锁主线40
        print(f"[8] GM set_mainline_stage uuid={uuid} stage_id=40")
        sc, body = gm("set_mainline_stage", uuid=uuid, stage_id=40)
        print(f"    -> {sc} {body}")
        result["gm_set_stage"] = {"status": sc, "body": body}
        page.wait_for_timeout(6000)

        sys_after = page.evaluate("""() => {
            const r = {};
            try { r.sys87 = window.SystemModules.sysOpenMgr.isSysOpen(87); } catch(e){ r.sys87 = 'err:'+e.message; }
            try { r.sys39 = window.SystemModules.sysOpenMgr.isSysOpen(39); } catch(e){ r.sys39 = 'err:'+e.message; }
            try { r.sys88 = window.SystemModules.sysOpenMgr.isSysOpen(88); } catch(e){ r.sys88 = 'err:'+e.message; }
            return r;
        }""")
        print(f"[9] GM后 sys状态 = {sys_after}")
        result["sys_after"] = sys_after

        # 弹窗检查：UIPrivCard / UIForeverCardOpenAlert
        page.wait_for_timeout(4000)
        ui_state = page.evaluate("""() => {
            const r = {};
            try { r.UIPrivCard = window.__qa.uiActive('UIPrivCard'); } catch(e){ r.UIPrivCard = 'err'; }
            try { r.UIForeverCardOpenAlert = window.__qa.uiActive('UIForeverCardOpenAlert'); } catch(e){ r.UIForeverCardOpenAlert = 'err'; }
            try { r.UIPrivCardOpenAlert = window.__qa.uiActive('UIPrivCardOpenAlert'); } catch(e){ r.UIPrivCardOpenAlert = 'err'; }
            return r;
        }""")
        print(f"[10] 弹窗状态 = {ui_state}")
        result["popup_after_unlock"] = ui_state
        screenshot(page, OUT, "02_after_unlock")

        # 若 UIPrivCard 激活，dump 文本树
        if ui_state.get("UIPrivCard"):
            texts = page.evaluate("() => { try { return window.__qa.dumpUITree('').filter(e=>e.text).map(e=>e.text); } catch(e){ return []; } }")
            print(f"[11] UIPrivCard 文本(前40条) = {texts[:40]}")
            result["uiprivcard_texts"] = texts

        result["page_errors"] = errors
        (OUT / "probe.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n结果已写入 {OUT / 'probe.json'}")
        context.close()
        browser.close()


if __name__ == "__main__":
    main()
