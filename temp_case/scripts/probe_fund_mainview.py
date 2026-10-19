# -*- coding: utf-8 -*-
"""基金特权入口合并 —— 主界面入口与合并UI确认(2)
1) 登录后关闭剧情对话框(Skip 反复点直到无 UISkip)
2) 拉取真实主界面文本 + 底部按钮节点名
3) 尝试点击文本 含 基金/特权/战令 的可点入口,记录打开的 UI
4) 若发现合并UI(包含 基础/消耗/任务 页签),截图取证并记录
"""
import json, os, sys, time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "harness"))
import e2e_login as base
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
ACCOUNT = os.environ.get("QA_ACCOUNT", "1351")
SVR_ID  = int(os.environ.get("SVR_ID", "5"))
SVR_NAME= os.environ.get("SVR_NAME", "S5")
GAME_URL= os.environ.get("GAME_URL", "http://localhost:7456").rstrip("/")

def qa(page, expr, default=None):
    try: return page.evaluate(expr)
    except Exception: return default

def texts(page):
    out=[]
    for e in (qa(page, "() => { try{return window.__qa.dumpUITree();}catch(e){return [];} }") or []):
        t=str(e.get("text","")); 
        if t: out.append(t)
    seen=set(); r=[]
    for t in out:
        if t not in seen: seen.add(t); r.append(t)
    return r

def shot(page, out, name):
    try: return base.screenshot(page, out, name)
    except Exception: return None

def close_story(page, out, max_s=25):
    """反复点 Skip 直到不再出现 或 超时"""
    t0=time.time()
    clicks=0
    while time.time()-t0<max_s:
        # 检测 Skip 节点
        has_skip = qa(page, "() => window.__qa.findByName('Skip').length") or 0
        if not has_skip:
            # 再看是否有剧情对话框
            tx = texts(page)
            if not any("吃吃" in t or "《惊险》" in t or "我是哪儿" in t for t in tx):
                return clicks
        # 点击 Skip
        qa(page, "() => window.__qa.findByName('Skip').forEach(n => window.__qa.clickNode(n))")
        clicks += 1
        page.wait_for_timeout(900)
    return clicks

def find_bottom_buttons(page):
    """枚举主界面下部的可点按钮(粗略: dumpUITree 中 node 带 Button / 带可点标志, 简化取 text+path)"""
    nodes = qa(page, "() => { try{return window.__qa.dumpUITree();}catch(e){return [];} }") or []
    items=[]
    for n in nodes:
        t=str(n.get("text","")).strip()
        p=n.get("path","")
        if t and len(t)<=12:
            items.append({"text":t,"path":p})
    # 保留含关键词的
    KW={"基","金","特","权","战","令","基","础","消","耗","任","务","一","建","购","领","充","好","礼"}
    keep=[i for i in items if any(k in i["text"] for k in KW)]
    return keep

def click_label(page, label):
    return qa(page, f"() => window.__qa.clickAncestorOfLabel({json.dumps(label)}, 'Button')")

def active_uis(page):
    return qa(page, "() => Object.keys(window.__qa._ui || {})") or []

def run():
    ts=datetime.now().strftime("%Y%m%d_%H%M%S")
    out=ROOT/"reports"/f"e2e_fund_probe2_{ts}"
    (out/"screenshots").mkdir(parents=True, exist_ok=True)
    log={"start":ts,"account":ACCOUNT,"server":SVR_NAME,"steps":[]}
    def rec(tag,note=""): log["steps"].append({"tag":tag,"note":note}); print(f"[{tag}] {note}")

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
            if not ready: raise RuntimeError("login fail")

            clicks=close_story(page,out)
            rec("STORY", f"Skip点击 {clicks} 次")
            page.wait_for_timeout(1500)
            shot(page,out,"main_clean")

            # dump 主界面文本与节点
            main_texts = texts(page)
            (out/"main_texts.json").write_text(json.dumps(main_texts,ensure_ascii=False,indent=1),encoding="utf-8")
            rec("MAIN_TEXTS", f"主界面文本 {len(main_texts)} 条; 样例: {main_texts[:60]}")

            bottom = find_bottom_buttons(page)
            (out/"bottom_buttons.json").write_text(json.dumps(bottom,ensure_ascii=False,indent=1),encoding="utf-8")
            rec("BOTTOM", f"底部/中部关键词按钮 {len(bottom)} 个: {[b['text'] for b in bottom]}")

            # 尝试点击 基金 / 特权 / 战令
            results={}
            for label in ["基金","特权","特权卡","战令","基金特权","特权·基金"]:
                ok=click_label(page,label)
                page.wait_for_timeout(2500)
                uis = active_uis(page)
                tx = texts(page)
                hit_kw = [k for k in ["基础","消耗","任务","炼宝基金","乾坤藏甲","仙友基金","升级基金","进阶基金","一键充值","一键购买","已解锁","未解锁","战令"] if any(k in t for t in tx)]
                results[label] = {"clicked":bool(ok),"active_uis":uis,"kw_hit":hit_kw}
                shot(page,out,f"try_{label}")
                rec(f"TRY_{label}", f"clicked={bool(ok)} active_uis={uis} kw={hit_kw}")
                # 关闭可能打开的popup
                for u in ["UIPrivilegeMain","UIPrivPanel","UIPrivCard","UIFund","UIFundMain","UIFundPanel"]:
                    qa(page, f"() => window.__qa.closeUI('{u}')")
                page.wait_for_timeout(700)
            (out/"entry_try.json").write_text(json.dumps(results,ensure_ascii=False,indent=1),encoding="utf-8")

            # 同时 dump UITree 路径样本(找 UI 名)
            sample = qa(page, "() => { try{return window.__qa.dumpUITree().slice(0,200).map(e=>e.path||e.name).filter(Boolean);}catch(e){return [];} }") or []
            (out/"ui_paths_sample.json").write_text(json.dumps(sample,ensure_ascii=False,indent=1),encoding="utf-8")

        except Exception as e:
            rec("ERR", str(e))
        finally:
            browser.close()

    (out/"report.json").write_text(json.dumps(log,ensure_ascii=False,indent=1),encoding="utf-8")
    print("REPORT:", out)

if __name__=="__main__":
    run()
