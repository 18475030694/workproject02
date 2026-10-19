"""探针3：验证正确的登录方式。

方案A：游戏加载后 evaluate 设置 TMP_ACCOUNT_ -> reload -> 读账号是否生效
方案B：真实 UI 点切换账号 -> 点击 EditBox 获得焦点 -> input 输入 -> 确认
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
            captured.append({"url": u, "body": body})

    page.on("response", on_response)

    # 打开游戏（不注入账号）
    page.goto(URL + "/?qa=1", wait_until="domcontentloaded", timeout=60000)
    base.wait_qa_bridge(page)
    page.wait_for_timeout(6000)

    print("=== 方案A：evaluate 设 TMP_ACCOUNT_ 后 reload ===")
    page.evaluate("() => { localStorage.setItem('TMP_ACCOUNT_', '%s'); }" % ACCOUNT)
    # 读回确认
    print("evaluate 后 TMP_ACCOUNT_ =", page.evaluate("() => localStorage.getItem('TMP_ACCOUNT_')"))
    page.reload(wait_until="domcontentloaded", timeout=60000)
    base.wait_qa_bridge(page)
    page.wait_for_timeout(6000)

    info = page.evaluate("""() => {
        const out = { ls: localStorage.getItem('TMP_ACCOUNT_') };
        try {
            const qa = window.__qa;
            const p = qa.findByName('Info_PlayerId_');
            if (p.length) { const n = qa.resolvePath(p[0]); const lb = n.getComponent(cc.Label); out.Info_PlayerId = lb ? lb.string : '(none)'; }
            const s = qa.findByName('Info_SeverId_');
            if (s.length) { const n = qa.resolvePath(s[0]); const lb = n.getComponent(cc.Label); out.Info_SeverId = lb ? lb.string : '(none)'; }
        } catch(e) { out.err = String(e); }
        return out;
    }""")
    print("reload 后:", json.dumps(info, ensure_ascii=False))

    # ===== 方案B：真实 UI 切换账号 =====
    print("\n=== 方案B：真实 UI 点切换账号 -> 点 EditBox -> 输入 ===")
    change_btn = page.evaluate("() => { try { return window.__qa.findByName('BtnChangeAccount_'); } catch(e){ return []; } }")
    if change_btn:
        page.evaluate("() => window.__qa.clickNode(%s)" % json.dumps(change_btn[0]))
        page.wait_for_timeout(1500)
        # 点击 EditBox 节点获得焦点
        editbox_node = page.evaluate("() => { try { return window.__qa.findByName('EditBox_'); } catch(e){ return []; } }")
        print("EditBox 节点:", editbox_node)
        if editbox_node:
            page.evaluate("() => window.__qa.clickNode(%s)" % json.dumps(editbox_node[0]))
            page.wait_for_timeout(1000)
        # 现在看 DOM input 是否可见
        dom_inputs = page.evaluate("""() => {
            return Array.from(document.querySelectorAll('input')).map((i, idx) => ({idx, id: i.id, type: i.type, visible: i.offsetParent !== null, value: i.value}));
        }""")
        print("点击 EditBox 后 DOM input:", json.dumps(dom_inputs, ensure_ascii=False))
        # 尝试键盘输入（focus 后 input 应该激活）
        try:
            page.keyboard.type(ACCOUNT, delay=50)
            page.wait_for_timeout(1000)
        except Exception as e:
            print("键盘输入异常:", e)
        # 读回 EditBox 的 string 和 DOM input value
        after_type = page.evaluate("""() => {
            const out = {};
            const inputs = document.querySelectorAll('input');
            for (const i of inputs) { if (i.id.indexOf('EditBox') >= 0) out.dom_value = i.value; }
            return out;
        }""")
        print("输入后 DOM:", json.dumps(after_type, ensure_ascii=False))
        # 点确认
        confirm_btn = page.evaluate("() => { try { return window.__qa.findByName('BtnIdConfirm_'); } catch(e){ return []; } }")
        if confirm_btn:
            page.evaluate("() => window.__qa.clickNode(%s)" % json.dumps(confirm_btn[0]))
            page.wait_for_timeout(1500)
        final = page.evaluate("""() => {
            const out = { ls: localStorage.getItem('TMP_ACCOUNT_') };
            try {
                const qa = window.__qa;
                const p = qa.findByName('Info_PlayerId_');
                if (p.length) { const n = qa.resolvePath(p[0]); const lb = n.getComponent(cc.Label); out.Info_PlayerId = lb ? lb.string : '(none)'; }
            } catch(e) { out.err = String(e); }
            return out;
        }""")
        print("切换后最终状态:", json.dumps(final, ensure_ascii=False))

    # ===== 点登录 =====
    print("\n=== 点登录 ===")
    try:
        page.wait_for_function("() => window.__qa.findByName('LoginBtn_').length > 0", timeout=30000)
        page.evaluate("() => window.__qa.findByName('LoginBtn_').forEach(n => window.__qa.clickNode(n))")
        page.wait_for_timeout(12000)
    except Exception as e:
        print("点登录异常:", e)

    print("\n=== plat_login 请求 ===")
    for c in captured:
        print("URL:", c["url"])
        print("body:", c["body"][:900])
        print("---")

    ctx.close()
    browser.close()
