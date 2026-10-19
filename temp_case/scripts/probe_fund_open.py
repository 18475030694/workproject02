# -*- coding: utf-8 -*-
"""点击 基金/特权卡 入口并 dump 打开界面
- 用 dumpUITree 找到含 基金/特权卡 文本的节点,click 其 parent(可点祖先)
- 同时尝试通过 text 'Skip' 关闭剧情
"""
import json, os, sys, time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "harness"))
import e2e_login as base
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parent.parent
ACCOUNT=os.environ.get("QA_ACCOUNT","1351")
SVR_ID=int(os.environ.get("SVR_ID","5"))
SVR_NAME=os.environ.get("SVR_NAME","S5")
GAME_URL=os.environ.get("GAME_URL","http://localhost:7456").rstrip("/")

def qa(page,e,default=None):
    try: return page.evaluate(e)
    except Exception: return default

def shot(page,out,n):
    try: return base.screenshot(page,out,n)
    except Exception: return None

def find_nodes_with_text(page, text):
    """返回 dumpUITree 中 text 含 text 的节点(原始结构)"""
    return qa(page, f"""() => {{
        try {{
            const tree = window.__qa.dumpUITree();
            return tree.filter(e => (e.text||'').includes({json.dumps(text)}));
        }} catch(e) {{ return []; }}
    }}""") or []

def click_text_parent(page, text, attempts=3):
    """点含 text 的节点的最远祖先(找 path 的根/parent)"""
    for k in range(attempts):
        nodes = find_nodes_with_text(page, text)
        if not nodes: 
            page.wait_for_timeout(700); continue
        # 用第一个匹配,点其 path
        n = nodes[0]
        path = n.get("path") or n.get("name")
        if path:
            ok = qa(page, f"() => {{ try {{ window.__qa.clickNode({json.dumps(path)}); return true; }} catch(e) {{ return false; }} }}")
            if ok: return path, len(nodes)
        # 退化: clickAncestorOfLabel
        ok2 = qa(page, f"() => window.__qa.clickAncestorOfLabel({json.dumps(text)}, '')")
        if ok2: return f"ancestor:{text}", len(nodes)
        page.wait_for_timeout(500)
    return None, 0

def active_uis(page):
    return qa(page, "() => Object.keys(window.__qa._ui || {})") or []

def all_texts(page):
    out=[]
    for e in (qa(page,"() => { try{return window.__qa.dumpUITree();}catch(e){return [];} }") or []):
        t=str(e.get("text","")); 
        if t: out.append(t)
    seen=set(); r=[]
    for t in out:
        if t not in seen: seen.add(t); r.append(t)
    return r

def run():
    ts=datetime.now().strftime("%Y%m%d_%H%M%S")
    out=ROOT/"reports"/f"e2e_fund_open_{ts}"
    (out/"screenshots").mkdir(parents=True, exist_ok=True)
    log={"start":ts,"account":ACCOUNT,"server":SVR_NAME,"openings":{}}
    def rec(t,n): print(f"[{t}] {n}")

    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_context(viewport={"width":1280,"height":720}).new_page()
        try:
            page.add_init_script(f"() => {{ try{{localStorage.setItem('TMP_ACCOUNT_','{ACCOUNT}');}}catch(e){{}} }}")
            page.goto(f"{GAME_URL}/?qa=1", wait_until="domcontentloaded", timeout=60_000)
            base.wait_qa_bridge(page); page.wait_for_timeout(4000)
            base.force_select_server(page, SVR_ID, SVR_NAME)
            page.reload(wait_until="domcontentloaded", timeout=60_000)
            base.wait_qa_bridge(page); page.wait_for_timeout(2500)
            try:
                page.wait_for_function("() => window.__qa.findByName('LoginBtn_').length>0", timeout=45_000)
                page.evaluate("() => window.__qa.findByName('LoginBtn_').forEach(n => window.__qa.clickNode(n))")
            except Exception: pass
            t0=time.time(); ready=False
            while time.time()-t0<150:
                if qa(page,"() => window.__qa.isReady()") and not qa(page,"() => window.__qa.uiActive('UILoading')"):
                    ready=True; break
                page.wait_for_timeout(2000)
            rec("LOGIN", f"ready={ready}")
            page.wait_for_timeout(2000)

            # 尝试按文本点 Skip(多次)
            for _ in range(8):
                # 找含 Skip 文本的节点并点
                nodes = find_nodes_with_text(page, "Skip")
                if nodes:
                    path = nodes[0].get("path") or nodes[0].get("name")
                    qa(page, f"() => {{ try{{window.__qa.clickNode({json.dumps(path)});}}catch(e){{}} }}")
                    page.wait_for_timeout(600)
                else:
                    break
            shot(page,out,"after_skip")

            # 点击 基金
            for label, key in [("基金","fund"),("特权卡","priv"),("战令","warorder")]:
                # 先关掉任何已开
                for u in ["UIPrivilegeMain","UIPrivPanel","UIPrivCard","UIFund","UIFundMain","UIFundPanel","UIPrivilegeFund"]:
                    qa(page, f"() => window.__qa.closeUI('{u}')")
                page.wait_for_timeout(800)
                path, hits = click_text_parent(page, label)
                page.wait_for_timeout(2800)
                shot(page,out,f"open_{key}")
                uis = active_uis(page)
                tx = all_texts(page)
                # 写树
                tree = qa(page, "() => { try{return window.__qa.dumpUITree();}catch(e){return [];} }") or []
                (out/f"tree_{key}.json").write_text(json.dumps(tree,ensure_ascii=False,indent=1)[:200000],encoding="utf-8")  # cap size
                kw = [k for k in ["基础","消耗","任务","炼宝基金","乾坤藏甲","仙友基金","升级基金","进阶基金","一键充值","一键购买","已解锁","未解锁","战令","武器零件","灵源","神器","法阵","翅膀","坐骑","神话仙友"] if any(k in t for t in tx)]
                log["openings"][key] = {"label":label,"clicked_path":path,"hits":hits,"active_uis":uis,"kw_hit":kw,"texts_sample":tx[:80]}
                rec(label, f"path={path} hits={hits} uis={uis} kw={kw}")
                (out/f"opening_{key}.json").write_text(json.dumps(log["openings"][key],ensure_ascii=False,indent=1),encoding="utf-8")
        except Exception as e:
            rec("ERR", str(e))
        finally:
            browser.close()
    (out/"report.json").write_text(json.dumps(log,ensure_ascii=False,indent=1),encoding="utf-8")
    print("REPORT:", out)

if __name__=="__main__":
    run()
