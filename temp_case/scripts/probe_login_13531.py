"""探针：抓 13531 登录的真实 plat_login 请求 URL + 响应，确认账号/平台/服是否与用户一致。

目的：回答两个问题
1. 为什么没顶号？ -> 看 plat_login 的 sdkAccount / sdkPlatform / serverId 真实值
2. 为什么走注入？ -> 记录选服方式、游戏内实际读到的账号来源
"""
import sys, json, time
sys.path.insert(0, 'harness')
import e2e_login as base
from playwright.sync_api import sync_playwright

ACCOUNT = "13531"
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
                body = resp.text()[:1200]
            except Exception:
                body = ""
            captured.append({"url": u, "status": resp.status, "body": body})

    page.on("response", on_response)

    # 注入账号（与 e2e_login 相同做法）
    page.add_init_script(
        "() => { try { localStorage.setItem('TMP_ACCOUNT_', '%s'); } catch(e) {} }" % ACCOUNT
    )
    page.goto(URL + "/?qa=1", wait_until="domcontentloaded", timeout=60000)
    base.wait_qa_bridge(page)
    page.wait_for_timeout(6000)

    # 读游戏内实际账号来源 + 选服状态
    info = page.evaluate("""() => {
        const out = {};
        try {
            const SM = window.SystemModules;
            // 账号来源
            if (SM.accountMgr) out.accountMgr = SM.accountMgr;
            // 直接读 Account 单例
            const G = window.__GAME__;
            out.__GAME__keys = G ? Object.keys(G).filter(k => /account|plat|login|server/i.test(k)) : null;
        } catch(e) { out.err1 = String(e); }
        try {
            const ls = {};
            for (const k of ['TMP_ACCOUNT_','last_login_server_id','last_login_server_name','selected_server_key']) {
                ls[k] = localStorage.getItem(k);
            }
            out.localStorage = ls;
        } catch(e) { out.err2 = String(e); }
        // 登录界面账号显示文本
        try {
            const qa = window.__qa;
            const p = qa.findByName('Info_PlayerId_');
            if (p.length) {
                const n = qa.resolvePath(p[0]);
                const lb = n.getComponent(cc.Label);
                out.Info_PlayerId_text = lb ? lb.string : '(no label)';
            }
            const s = qa.findByName('Info_SeverId_');
            if (s.length) {
                const n = qa.resolvePath(s[0]);
                const lb = n.getComponent(cc.Label);
                out.Info_SeverId_text = lb ? lb.string : '(no label)';
            }
        } catch(e) { out.err3 = String(e); }
        return out;
    }""")
    print("=== 登录前游戏内状态 ===")
    print(json.dumps(info, ensure_ascii=False, indent=1))

    # 尝试真实 UI 选服
    print("\n=== 尝试真实 UI 选服 ===")
    try:
        opened, open_msg = base.open_server_dialog(page)
        print("打开换区弹窗:", opened, open_msg)
        if opened:
            res = base.scan_and_select_server(page, 5, "s5服")
            print("scan 结果:", json.dumps(res, ensure_ascii=False))
    except Exception as e:
        print("UI选服异常:", e)

    # 点击登录
    print("\n=== 点击登录 ===")
    try:
        page.wait_for_function("() => window.__qa.findByName('LoginBtn_').length > 0", timeout=30000)
        page.evaluate("() => window.__qa.findByName('LoginBtn_').forEach(n => window.__qa.clickNode(n))")
        page.wait_for_timeout(12000)
    except Exception as e:
        print("点击登录异常:", e)

    print("\n=== plat_login 请求捕获 ===")
    if not captured:
        print("未捕获到 plat_login 请求")
    for c in captured:
        print("URL:", c["url"])
        print("status:", c["status"])
        print("body:", c["body"][:1200])
        print("---")

    # 登录后角色状态
    info2 = page.evaluate("""() => {
        const out = {};
        try {
            const SM = window.SystemModules;
            const PM = SM.playerMgr;
            out.playerMgr_keys = PM ? Object.keys(PM).filter(k => /uuid|role|id|name/i.test(k)) : null;
            out.playerUuid = window.__GAME__ ? window.__GAME__.playerUuid : null;
        } catch(e) { out.err = String(e); }
        return out;
    }""")
    print("=== 登录后角色状态 ===")
    print(json.dumps(info2, ensure_ascii=False, indent=1))

    ctx.close()
    browser.close()
