# -*- coding: utf-8 -*-
"""探针2：全新账号解锁弹窗流程
1. 随机新号登录 -> 2. 初始 sys 状态 -> 3. GM set_mainline_stage(40)
4. 轮询弹窗队列 90s：记录出现的 UI、自动关闭非目标弹窗、等待 UIPrivCard
5. UIPrivCard 出现时 dump 文本 + 截图
6. 二次登录验证 uuid 稳定性
"""
import json
import random
import sys
import time
import requests
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "harness"))
from e2e_login import wait_qa_bridge, screenshot, is_in_main_city  # noqa: E402

GM_BASE = "http://192.168.*.*:6011/index"
OUT = Path(__file__).resolve().parent / "probe_priv2_out"
OUT.mkdir(exist_ok=True)
(OUT / "screenshots").mkdir(exist_ok=True)

ACCOUNT = str(random.randint(3000, 8999))
SERVER = "s5服"
URL = "http://localhost:7456/?qa=1"

# 关注的弹窗
WATCH_UIS = ["UIPrivCard", "UIForeverCardOpenAlert", "UIPrivCardOpenAlert",
             "UIFirstRecharge", "UIFund", "UIMonthFund", "UIWelfare"]


def gm(cmd, **params):
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    r = requests.get(f"{GM_BASE}/{cmd}?{qs}", timeout=15)
    return r.status_code, r.text[:200]


def login(page, account):
    page.goto(URL, wait_until="domcontentloaded", timeout=60000)
    wait_qa_bridge(page)
    page.wait_for_timeout(8000)
    page.evaluate(f"() => {{ localStorage.setItem('TMP_ACCOUNT_', '{account}'); }}")
    page.evaluate("""() => {
        localStorage.setItem('last_login_server_id', '5');
        localStorage.setItem('last_login_server_name', 's5服');
        localStorage.setItem('selected_server_key', '5');
    }""")
    page.reload(wait_until="domcontentloaded", timeout=60000)
    wait_qa_bridge(page)
    page.wait_for_timeout(4000)
    page.wait_for_function("() => window.__qa.findByName('LoginBtn_').length > 0", timeout=60000)
    page.evaluate("() => window.__qa.findByName('LoginBtn_').forEach(n => window.__qa.clickNode(n))")
    deadline = time.time() + 120
    while time.time() < deadline and not is_in_main_city(page):
        page.wait_for_timeout(1000)
    return is_in_main_city(page)


def get_uuid(page):
    return page.evaluate("() => { try { return window.__GAME__.playerUuid; } catch(e){ return null; } }")


def active_uis(page):
    return page.evaluate(f"""() => {{
        const watch = {json.dumps(WATCH_UIS)};
        const r = {{}};
        for (const n of watch) {{
            try {{ r[n] = window.__qa.uiActive(n); }} catch(e) {{ r[n] = false; }}
        }}
        // 额外记录当前所有可见的带 Alert/Card/Pop 的 UI
        try {{
            r.__active_top = window.__qa.dumpUITree('').length;
        }} catch(e) {{}}
        return r;
    }}""")


def close_top_popup(page):
    """尝试关闭当前弹窗：优先 CloseBg/BtnClose 类按钮"""
    return page.evaluate("""() => {
        try {
            const qa = window.__qa;
            for (const bn of ['CloseBg', 'BtnClose', 'CloseBtn', 'btnClose', 'NdClose']) {
                const paths = qa.findByName(bn);
                if (paths && paths.length) {
                    qa.clickNode(paths[paths.length - 1]);
                    return bn;
                }
            }
            return null;
        } catch(e) { return null; }
    }""")


def main():
    result = {"account": ACCOUNT}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(e.message[:200]))

        print(f"[1] 新账号 {ACCOUNT} 登录")
        ok = login(page, ACCOUNT)
        print(f"    in_main_city={ok}")
        screenshot(page, OUT, "01_fresh_login")
        uuid = get_uuid(page)
        print(f"[2] uuid={uuid}")
        result["uuid_1st"] = uuid

        sys_before = page.evaluate("""() => {
            const r = {};
            for (const id of [39, 87, 88, 97, 142]) {
                try { r['sys'+id] = window.SystemModules.sysOpenMgr.isSysOpen(id); } catch(e){ r['sys'+id] = 'err'; }
            }
            return r;
        }""")
        print(f"[3] 初始sys = {sys_before}")
        result["sys_before"] = sys_before

        print(f"[4] GM set_mainline_stage(40)")
        sc, body = gm("set_mainline_stage", uuid=uuid, stage_id=40)
        print(f"    -> {sc} {body}")
        result["gm"] = body

        # 轮询弹窗队列
        print("[5] 轮询弹窗队列（最长120s）...")
        seen = []
        deadline = time.time() + 120
        priv_seen = False
        while time.time() < deadline:
            st = active_uis(page)
            for name in WATCH_UIS:
                if st.get(name) and name not in [s["name"] for s in seen]:
                    seen.append({"name": name, "t": round(time.time() - (deadline - 120), 1)})
                    print(f"    + 弹窗出现: {name} @t={seen[-1]['t']}s")
                    if name == "UIPrivCard":
                        priv_seen = True
                        texts = page.evaluate("() => window.__qa.dumpUITree('').filter(e=>e.text).map(e=>({n:e.name,t:e.text}))")
                        result["uiprivcard_texts"] = texts
                        screenshot(page, OUT, "02_UIPrivCard_popup")
            if priv_seen:
                break
            # 关闭非目标弹窗推进队列
            any_active = [n for n in WATCH_UIS if st.get(n)]
            if not any_active:
                closed = close_top_popup(page)
                if closed:
                    page.wait_for_timeout(800)
            page.wait_for_timeout(1500)

        result["popup_sequence"] = seen
        print(f"[6] 弹窗序列 = {seen}")
        print(f"    UIPrivCard出现 = {priv_seen}")
        if not priv_seen:
            screenshot(page, OUT, "03_no_privcard")

        # 二次登录 uuid 稳定性
        print("[7] 二次登录验证 uuid 稳定性")
        page.close()
        page2 = context.new_page()
        ok2 = login(page2, ACCOUNT)
        uuid2 = get_uuid(page2)
        print(f"    in_main_city={ok2}, uuid2={uuid2}, 稳定={uuid == uuid2}")
        result["uuid_2nd"] = uuid2
        result["uuid_stable"] = (uuid == uuid2)
        # 重登后是否有弹窗
        page2.wait_for_timeout(5000)
        st2 = active_uis(page2)
        result["popup_after_relogin"] = {k: v for k, v in st2.items() if isinstance(v, bool)}
        print(f"[8] 重登后弹窗 = {result['popup_after_relogin']}")
        screenshot(page2, OUT, "04_after_relogin")

        # 重登后 sys 状态是否持久
        sys_persist = page2.evaluate("""() => {
            const r = {};
            for (const id of [87, 88]) {
                try { r['sys'+id] = window.SystemModules.sysOpenMgr.isSysOpen(id); } catch(e){ r['sys'+id] = 'err'; }
            }
            return r;
        }""")
        print(f"[9] 重登后 sys = {sys_persist}")
        result["sys_after_relogin"] = sys_persist

        result["page_errors"] = errors
        (OUT / "probe.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n结果已写入 {OUT / 'probe.json'}")
        context.close()
        browser.close()


if __name__ == "__main__":
    main()
