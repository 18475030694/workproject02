import json, sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "harness"))
from e2e_login import wait_qa_bridge, screenshot, is_in_main_city

URL = "http://localhost:7456/?qa=1"

def login(page, acc):
    page.goto(URL, wait_until="domcontentloaded", timeout=60000)
    wait_qa_bridge(page); page.wait_for_timeout(8000)
    page.evaluate(f"() => {{ localStorage.setItem('TMP_ACCOUNT_', '{acc}'); }}")
    page.evaluate("""() => { localStorage.setItem('last_login_server_id','5'); localStorage.setItem('last_login_server_name','s5服'); localStorage.setItem('selected_server_key','5'); }""")
    page.reload(wait_until="domcontentloaded", timeout=60000)
    wait_qa_bridge(page); page.wait_for_timeout(4000)
    page.wait_for_function("() => window.__qa.findByName('LoginBtn_').length > 0", timeout=60000)
    page.evaluate("() => window.__qa.findByName('LoginBtn_').forEach(n => window.__qa.clickNode(n))")
    while not is_in_main_city(page): page.wait_for_timeout(1000)

def main():
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        c = b.new_context(viewport={"width":1280,"height":720})
        page = c.new_page()
        login(page, "4282")
        print("uuid", page.evaluate("() => window.__GAME__.playerUuid"))
        # 检查 card 2 状态
        st = page.evaluate("""() => { 
            const i = window.SystemModules.privilegeMgr.cardInfoMap.get(2);
            return {buy_time: i.buy_time, expire_time: i.expire_time, daily_reward_state: i.daily_reward_state};
        }""")
        print("card2", st)
        # 清空队列
        page.evaluate("""() => { 
            const q = window.Global.uiMgr.uiQueue;
            if (q && q.queueList) q.queueList = [];
        }""")
        print("queue before", page.evaluate("() => window.Global.uiMgr.uiQueue.queueList.map(x=>x.ui_name)"))
        # 触发
        res = page.evaluate("""() => { 
            try { window.SystemModules.privilegeMgr.onNewSysOpen(87); return 'ok'; } catch(e){ return 'err:'+e.message; }
        }""")
        print("trigger result", res)
        time.sleep(2)
        print("queue after", page.evaluate("() => window.Global.uiMgr.uiQueue.queueList.map(x=>x.ui_name)"))
        print("UIPrivCard active", page.evaluate("() => window.__qa.uiActive('UIPrivCard')"))
        screenshot(page, Path('E:/workproject/temp_case/probe_onnewsysopen_out'), 'result')
        b.close()

if __name__ == '__main__':
    main()
