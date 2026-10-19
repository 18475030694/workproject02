"""探针2：定位账号注入失效时机 + 验证真实UI切换账号路径。

验证：
1. add_init_script 注入 13531 后，游戏启动阶段 TMP_ACCOUNT_ 何时被覆盖成随机号
2. 走真实 UI「切换账号」按钮输入 13531，能否真正登录 13531
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

    # add_init_script 注入 + 一个标记 key
    page.add_init_script(
        "() => { try { localStorage.setItem('TMP_ACCOUNT_', '%s'); localStorage.setItem('__PROBE_MARK__', 'injected'); } catch(e) {} }" % ACCOUNT
    )
    page.goto(URL + "/?qa=1", wait_until="domcontentloaded", timeout=60000)

    # goto 返回后立刻读（游戏脚本可能还没跑）
    early = page.evaluate("() => { return {mark: localStorage.getItem('__PROBE_MARK__'), acc: localStorage.getItem('TMP_ACCOUNT_')}; }")
    print("=== goto 后立即读 localStorage ===")
    print(json.dumps(early, ensure_ascii=False))

    base.wait_qa_bridge(page)
    page.wait_for_timeout(6000)

    late = page.evaluate("() => { return {mark: localStorage.getItem('__PROBE_MARK__'), acc: localStorage.getItem('TMP_ACCOUNT_')}; }")
    print("=== 游戏加载完成后读 localStorage ===")
    print(json.dumps(late, ensure_ascii=False))

    # 读登录界面账号显示
    ui = page.evaluate("""() => {
        const out = {};
        try {
            const qa = window.__qa;
            const p = qa.findByName('Info_PlayerId_');
            if (p.length) { const n = qa.resolvePath(p[0]); const lb = n.getComponent(cc.Label); out.Info_PlayerId = lb ? lb.string : '(none)'; }
            const s = qa.findByName('Info_SeverId_');
            if (s.length) { const n = qa.resolvePath(s[0]); const lb = n.getComponent(cc.Label); out.Info_SeverId = lb ? lb.string : '(none)'; }
        } catch(e) { out.err = String(e); }
        return out;
    }""")
    print("=== 登录界面账号/服显示 ===")
    print(json.dumps(ui, ensure_ascii=False))

    # ===== 真实 UI 切换账号 =====
    print("\n=== 走真实 UI 切换账号 ===")
    change_btn = page.evaluate("() => { try { return window.__qa.findByName('BtnChangeAccount_'); } catch(e){ return []; } }")
    print("切换账号按钮:", change_btn)
    if change_btn:
        page.evaluate("() => window.__qa.clickNode(%s)" % json.dumps(change_btn[0]))
        page.wait_for_timeout(1500)
        # 找 EditBox 输入框（DOM 层）
        dom_inputs = page.evaluate("""() => {
            const inputs = Array.from(document.querySelectorAll('input'));
            return inputs.map((i, idx) => ({idx, id: i.id, name: i.name, type: i.type, visible: i.offsetParent !== null}));
        }""")
        print("DOM input 列表:", json.dumps(dom_inputs, ensure_ascii=False))
        # 尝试输入
        page.evaluate("""(account) => {
            const inputs = document.querySelectorAll('input');
            for (const i of inputs) {
                if (i.type === 'text' || i.type === '' || i.id.indexOf('EditBox') >= 0) {
                    i.focus();
                    i.value = account;
                    i.dispatchEvent(new Event('input', {bubbles: true}));
                    i.dispatchEvent(new Event('change', {bubbles: true}));
                    return i.id || i.type;
                }
            }
            return 'no-input';
        }""", ACCOUNT)
        page.wait_for_timeout(500)
        # 点确认按钮
        confirm_btn = page.evaluate("() => { try { return window.__qa.findByName('BtnIdConfirm_'); } catch(e){ return []; } }")
        print("确认按钮:", confirm_btn)
        if confirm_btn:
            page.evaluate("() => window.__qa.clickNode(%s)" % json.dumps(confirm_btn[0]))
            page.wait_for_timeout(1500)
        # 读回账号显示
        after = page.evaluate("""() => {
            try {
                const qa = window.__qa;
                const p = qa.findByName('Info_PlayerId_');
                if (p.length) { const n = qa.resolvePath(p[0]); const lb = n.getComponent(cc.Label); return {Info_PlayerId: lb ? lb.string : '(none)'}; }
            } catch(e){ return {err: String(e)}; }
            return {Info_PlayerId: '(not found)'};
        }""")
        print("切换后账号显示:", json.dumps(after, ensure_ascii=False))
        # 读 localStorage
        ls_after = page.evaluate("() => ({acc: localStorage.getItem('TMP_ACCOUNT_'), mark: localStorage.getItem('__PROBE_MARK__')})")
        print("切换后 localStorage:", json.dumps(ls_after, ensure_ascii=False))

    # ===== 点击登录 =====
    print("\n=== 点击登录 ===")
    try:
        page.wait_for_function("() => window.__qa.findByName('LoginBtn_').length > 0", timeout=30000)
        page.evaluate("() => window.__qa.findByName('LoginBtn_').forEach(n => window.__qa.clickNode(n))")
        page.wait_for_timeout(12000)
    except Exception as e:
        print("点击登录异常:", e)

    print("\n=== plat_login 请求捕获 ===")
    for c in captured:
        print("URL:", c["url"])
        print("body:", c["body"][:1000])
        print("---")

    ctx.close()
    browser.close()
