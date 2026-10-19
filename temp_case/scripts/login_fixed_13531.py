"""修正版登录：正确方式登录指定账号 + 指定服。

根因修复：
- add_init_script 在 Cocos 预览环境不执行（已用 console 验证），导致账号/选服注入失效
- 正确方式：goto -> wait_qa_bridge -> evaluate 写 localStorage(账号+选服) -> reload -> 登录

验证：plat_login 请求 sdkAccount==目标账号 && serverId==目标服，且进入主城。
"""
import sys, json, time
sys.path.insert(0, 'harness')
import e2e_login as base
from playwright.sync_api import sync_playwright

ACCOUNT = "13531"
SERVER_ID = 5
SERVER_NAME = "S5"
URL = "http://localhost:7456"

captured = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1280, "height": 720})
    page = ctx.new_page()

    def on_response(resp):
        u = resp.url
        if "plat_login" in u:
            try:
                body = resp.text()[:1500]
            except Exception:
                body = ""
            captured.append({"url": u, "body": body})

    page.on("response", on_response)

    # 1. 打开游戏
    print("[1] 打开游戏")
    page.goto(URL + "/?qa=1", wait_until="domcontentloaded", timeout=60000)
    base.wait_qa_bridge(page)
    page.wait_for_timeout(6000)

    # 2. evaluate 写账号 + 选服 3 键
    print("[2] evaluate 写账号 + 选服")
    page.evaluate("""(cfg) => {
        localStorage.setItem('TMP_ACCOUNT_', cfg.account);
        localStorage.setItem('last_login_server_id', cfg.id);
        localStorage.setItem('last_login_server_name', cfg.name);
        localStorage.setItem('selected_server_key', cfg.id);
    }""", {"account": ACCOUNT, "id": str(SERVER_ID), "name": SERVER_NAME})

    readback = page.evaluate("""() => ({
        acc: localStorage.getItem('TMP_ACCOUNT_'),
        id: localStorage.getItem('last_login_server_id'),
        name: localStorage.getItem('last_login_server_name'),
        sel: localStorage.getItem('selected_server_key'),
    })""")
    print("   写后读回:", json.dumps(readback, ensure_ascii=False))

    # 3. reload 让游戏读取
    print("[3] reload")
    page.reload(wait_until="domcontentloaded", timeout=60000)
    base.wait_qa_bridge(page)
    page.wait_for_timeout(6000)

    ui = page.evaluate("""() => {
        const out = {};
        try {
            const qa = window.__qa;
            const p = qa.findByName('Info_PlayerId_');
            if (p.length) { const n = qa.resolvePath(p[0]); const lb = n.getComponent(cc.Label); out.账号显示 = lb ? lb.string : '(none)'; }
            const s = qa.findByName('Info_SeverId_');
            if (s.length) { const n = qa.resolvePath(s[0]); const lb = n.getComponent(cc.Label); out.服显示 = lb ? lb.string : '(none)'; }
        } catch(e) { out.err = String(e); }
        return out;
    }""")
    print("   reload 后界面:", json.dumps(ui, ensure_ascii=False))

    # 4. 点登录
    print("[4] 点登录")
    page.wait_for_function("() => window.__qa.findByName('LoginBtn_').length > 0", timeout=30000)
    page.evaluate("() => window.__qa.findByName('LoginBtn_').forEach(n => window.__qa.clickNode(n))")

    # 5. 等待 plat_login
    deadline = time.time() + 30
    while time.time() < deadline and not captured:
        page.wait_for_timeout(500)

    print("[5] plat_login 请求:")
    if not captured:
        print("   未捕获")
    for c in captured:
        print("   URL:", c["url"])
        try:
            body = json.loads(c["body"])
            print("   sdkAccount:", body.get("converInfo", {}).get("sdk_uid"))
            print("   platUID:", body.get("platUID"))
            print("   serverId:", body.get("serverId"), "serverName:", body.get("serverName"))
            print("   errcode:", body.get("errcode"))
        except Exception:
            print("   body:", c["body"][:600])

    # 6. 等进主城
    print("[6] 等进主城")
    end = time.time() + 60
    in_city = False
    while time.time() < end:
        if base.is_in_main_city(page):
            in_city = True
            break
        page.wait_for_timeout(1000)
    print("   进主城:", in_city)

    if in_city:
        role = page.evaluate("""() => {
            const out = {};
            try { out.playerUuid = window.__GAME__ ? window.__GAME__.playerUuid : null; } catch(e) {}
            try {
                const SM = window.SystemModules;
                const PM = SM.playerMgr;
                out.playerMgr_keys = PM ? Object.keys(PM).filter(k => /uuid|role|id|name/i.test(k)) : null;
            } catch(e) {}
            return out;
        }""")
        print("   角色:", json.dumps(role, ensure_ascii=False))

    ctx.close()
    browser.close()

print("\n结论: 账号=%s, plat_login 请求里 sdkAccount=%s" % (
    ACCOUNT,
    json.loads(captured[0]["body"]).get("converInfo", {}).get("sdk_uid") if captured else "无",
))
