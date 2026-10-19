# -*- coding: utf-8 -*-
"""基金特权入口合并 —— 运行时发现探测
登录(1351/S5) → 枚举主界面中与 基金/特权/战令 相关的入口 → 尝试进入 → dump 打开的界面树
用途：确认运行实例中“基金特权入口合并”是否已实现、入口文案/UI名/页签结构。
产物落 reports/e2e_fund_probe_<ts>/
"""
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "harness"))
import e2e_login as base  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ACCOUNT = os.environ.get("QA_ACCOUNT", "1351")
SVR_ID = int(os.environ.get("SVR_ID", "5"))
SVR_NAME = os.environ.get("SVR_NAME", "S5")
GAME_URL = os.environ.get("GAME_URL", "http://localhost:7456").rstrip("/")

# 可能的相关关键词（用于在主界面里找入口 & 找弹出界面）
KW = ["基金", "特权", "战令", "炼宝基金", "乾坤藏甲", "仙友基金", "升级基金", "进阶基金",
      "神话仙友", "武器零件", "灵源", "神器", "法阵", "翅膀", "坐骑",
      "基础", "消耗", "任务", "一键充值", "一键购买", "已解锁", "未解锁"]

# 可能承载合并界面的 UI 名（含当前特权/基金相关 + 通用基金名）
UI_CANDIDATES = ["UIPrivilegeMain", "UIPrivPanel", "UIPrivCard", "UIFund", "UIFundMain",
                 "UIFundPanel", "UIPrivilegeFund", "UIFundPrivilege", "UIChongzhi",
                 "UIRecharge", "UIWarOrder", "UIFirstCharge", "UIYxActWuyiFund",
                 "UIChargeFund", "UIJijin", "UIFundList"]


def qa(page, expr, default=None):
    try:
        return page.evaluate(expr)
    except Exception:
        return default


def texts(page, kw=""):
    return qa(page, f"() => {{ try {{ return window.__qa.dumpUITree('{kw}'); }} catch(e) {{ return []; }} }}", []) or []


def shot(page, out_dir, name):
    try:
        return base.screenshot(page, out_dir, name)
    except Exception:
        return None


def all_texts(page):
    out = []
    for e in texts(page):
        t = str(e.get("text", ""))
        if t:
            out.append(t)
    # 去重保序
    seen = set(); res = []
    for t in out:
        if t not in seen:
            seen.add(t); res.append(t)
    return res


def run():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / "reports" / f"e2e_fund_probe_{ts}"
    (out_dir / "screenshots").mkdir(parents=True, exist_ok=True)
    log = {"start": ts, "account": ACCOUNT, "server": SVR_NAME, "steps": []}

    def rec(tag, note=""):
        log["steps"].append({"tag": tag, "note": note})
        print(f"[{tag}] {note}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(viewport={"width": 1280, "height": 720}).new_page()
        try:
            page.add_init_script(f"() => {{ try {{ localStorage.setItem('TMP_ACCOUNT_', '{ACCOUNT}'); }} catch(e) {{}} }}")
            page.goto(f"{GAME_URL}/?qa=1", wait_until="domcontentloaded", timeout=60_000)
            base.wait_qa_bridge(page)
            page.wait_for_timeout(4000)
            base.force_select_server(page, SVR_ID, SVR_NAME)
            page.reload(wait_until="domcontentloaded", timeout=60_000)
            base.wait_qa_bridge(page)
            page.wait_for_timeout(2500)
            try:
                page.wait_for_function("() => window.__qa.findByName('LoginBtn_').length > 0", timeout=45_000)
                page.evaluate("() => window.__qa.findByName('LoginBtn_').forEach(n => window.__qa.clickNode(n))")
            except Exception:
                # 可能已自动登录
                pass
            t0 = time.time(); ready = False
            while time.time() - t0 < 150:
                if qa(page, "() => window.__qa.isReady()") and not qa(page, "() => window.__qa.uiActive('UILoading')"):
                    ready = True; break
                page.wait_for_timeout(2000)
            rec("LOGIN", f"进主城 ready={ready}")
            if not ready:
                shot(page, out_dir, "login_fail")
                raise RuntimeError("login fail")
            shot(page, out_dir, "main_city")

            # 1) 主界面含关键词的文本样本
            main_texts = all_texts(page)
            hit = [t for t in main_texts if any(k in t for k in KW)]
            (out_dir / "main_hit_texts.json").write_text(json.dumps(hit, ensure_ascii=False, indent=1), encoding="utf-8")
            rec("MAIN_TEXTS", f"命中关键词文本 {len(hit)} 条: {hit[:40]}")
            shot(page, out_dir, "main_hit")

            # 2) 尝试按文本点击含 基金/特权 的入口并 dump
            #    用 clickAncestorOfLabel 找 基金 文本所在可点节点
            clicked = {}
            for label in ["基金", "特权", "战令"]:
                ok = qa(page, f"() => window.__qa.clickAncestorOfLabel({json.dumps(label)}, '')")
                page.wait_for_timeout(2500)
                after = all_texts(page)
                opened_uis = qa(page, "() => window.__qa.dumpUITree('UIPrivilegeMain').length") or 0
                dumps = {}
                for c in UI_CANDIDATES:
                    n = qa(page, f"() => window.__qa.dumpUITree('{c}').length") or 0
                    if n:
                        dumps[c] = n
                clicked[label] = {"clicked": bool(ok), "open_ui_hits": dumps}
                rec(f"TRY_{label}", f"clicked={bool(ok)} openUI树命中={dumps}")
                shot(page, out_dir, f"after_{label}")

            (out_dir / "entry_click.json").write_text(json.dumps(clicked, ensure_ascii=False, indent=1), encoding="utf-8")

            # 3) 直接尝试 openUI 各候选（若某界面能开且含基金关键词，即为合并界面）
            found_ui = {}
            for c in UI_CANDIDATES:
                r = qa(page, f"() => window.__qa.openUI('{c}')")
                page.wait_for_timeout(1800)
                act = qa(page, f"() => window.__qa.uiActive('{c}')")
                tree = all_texts(page)
                fkw = [k for k in KW if any(k in t for t in tree)]
                if act or fkw:
                    found_ui[c] = {"open_ret": bool(r), "uiActive": bool(act), "kw_hit": fkw}
                    shot(page, out_dir, f"openUI_{c}")
                # 关闭，避免叠加
                qa(page, f"() => window.__qa.closeUI('{c}')")
                page.wait_for_timeout(600)
            (out_dir / "openui_probe.json").write_text(json.dumps(found_ui, ensure_ascii=False, indent=1), encoding="utf-8")
            rec("OPENUI", f"可打开且含基金关键词的UI: {list(found_ui.keys())}")

        except Exception as e:
            log["error"] = str(e)
            rec("ERR", str(e))
        finally:
            browser.close()

    (out_dir / "report.json").write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")
    print("REPORT:", out_dir)


if __name__ == "__main__":
    run()
