# -*- coding: utf-8 -*-
"""点 WarOrder_/PrivCard_ 根节点打开入口,dump 打开的 UI
确认 基金入口 → 打开的界面 (是否含 基础/消耗/任务 页签 + 各种基金 banner)
确认 特权卡入口 → 打开的界面 (是否独立、不含基金内容)
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

def qa(page,e,d=None):
    try: return page.evaluate(e)
    except Exception: return d

def shot(page,out,n):
    try: return base.screenshot(page,out,n)
    except Exception: return None

def click_path(page, path):
    return qa(page, f"() => {{ try{{window.__qa.clickNode({json.dumps(path)}); return true;}}catch(e){{return false;}} }}")

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

def close_all(page):
    for u in ["UIPrivilegeMain","UIPrivPanel","UIPrivCard","UIFund","UIFundMain","UIFundPanel","UIPrivilegeFund","UIWarOrder","UIYxActWuyiFund","UIFirstCharge","UIFirstChargeNewFundItem"]:
        qa(page, f"() => window.__qa.closeUI('{u}')")
    page.wait_for_timeout(700)

def run():
    ts=datetime.now().strftime("%Y%m%d_%H%M%S")
    out=ROOT/"reports"/f"e2e_fund_open2_{ts}"
    (out/"screenshots").mkdir(parents=True, exist_ok=True)
    log={"start":ts,"account":ACCOUNT,"server":SVR_NAME,"results":{}}

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
            print(f"[LOGIN] ready={ready}")
            page.wait_for_timeout(2000)

            # 关剧情
            for _ in range(6):
                qa(page, "() => { try{const n=window.__qa.dumpUITree().find(e=>e.text==='Skip'||e.text==='skip'||e.text==='跳过'); if(n) window.__qa.clickNode(n.path||n.name);}catch(e){} }")
                page.wait_for_timeout(500)

            WARORDER = "UIRootCamera/MainViewDown/UIMainView_Middle/SafeArea/TopLeft_/Layout/Group/LeftBtnLayout_/WarOrder_"
            PRIVOFRD = "UIRootCamera/MainViewDown/UIMainView_Middle/SafeArea/TopLeft_/Layout/Group/LeftBtnLayout_/PrivCard_"

            # 点 WarOrder_ (基金)
            close_all(page)
            ok = click_path(page, WARORDER)
            page.wait_for_timeout(3000)
            shot(page,out,"open_fund_warorder")
            uis1 = active_uis(page)
            tx1 = all_texts(page)
            tree1 = qa(page,"() => { try{return window.__qa.dumpUITree();}catch(e){return [];} }") or []
            # 检测页签与基金关键词
            tabs1 = [t for t in tx1 if t in ["基础","消耗","任务","基础类","消耗类","任务类","全部"]]
            funds1 = [k for k in ["炼宝基金","乾坤藏甲","仙友基金","升级基金","进阶基金","神话仙友","武器零件","灵源","神器","法阵","翅膀","坐骑","战令"] if any(k in t for t in tx1)]
            log["results"]["fund_entry"] = {"path":WARORDER,"clicked":ok,"active_uis":uis1,"tabs":tabs1,"fund_kw":funds1,"texts_count":len(tx1),"texts_sample":tx1[:120]}
            print(f"[FUND] clicked={ok} uis={uis1} tabs={tabs1} funds={funds1}")
            (out/"tree_fund.json").write_text(json.dumps(tree1,ensure_ascii=False,indent=1)[:300000],encoding="utf-8")

            # 关
            close_all(page); page.wait_for_timeout(1000)

            # 点 PrivCard_ (特权)
            ok2 = click_path(page, PRIVOFRD)
            page.wait_for_timeout(3000)
            shot(page,out,"open_priv")
            uis2 = active_uis(page)
            tx2 = all_texts(page)
            tree2 = qa(page,"() => { try{return window.__qa.dumpUITree();}catch(e){return [];} }") or []
            tabs2 = [t for t in tx2 if t in ["基础","消耗","任务","基础类","消耗类","任务类"]]
            funds2 = [k for k in ["炼宝基金","乾坤藏甲","仙友基金","升级基金","进阶基金","战令"] if any(k in t for t in tx2)]
            has_priv = any("特权" in t or "永久" in t or "月卡" in t or "季卡" in t or "年卡" in t or "特权卡" in t for t in tx2)
            log["results"]["priv_entry"] = {"path":PRIVOFRD,"clicked":ok2,"active_uis":uis2,"tabs":tabs2,"fund_kw":funds2,"has_priv_text":has_priv,"texts_count":len(tx2),"texts_sample":tx2[:120]}
            print(f"[PRIV] clicked={ok2} uis={uis2} tabs={tabs2} funds={funds2} has_priv={has_priv}")
            (out/"tree_priv.json").write_text(json.dumps(tree2,ensure_ascii=False,indent=1)[:300000],encoding="utf-8")
        except Exception as e:
            log["error"]=str(e); print(f"[ERR] {e}")
        finally:
            browser.close()
    (out/"report.json").write_text(json.dumps(log,ensure_ascii=False,indent=1),encoding="utf-8")
    print("REPORT:", out)

if __name__=="__main__":
    run()
