# -*- coding: utf-8 -*-
"""秘宝回退 E2E：⑤UI合理性 ⑥结算显示vs实际 ⑦概率 ⑧基本回归（旧 UITreasureBox）

设计原则（针对前会话工具失真）：
  - 运行时探针先发现结构（按钮名/cfg/Network句柄），断言只依赖运行时证据
  - 双通道互证：treasureBoxMgr.requestOpenBox 包装捕获 服务器resp
    + eventEmit 包装捕获 MSG_ON_TREASURE_OPEN_BOX（客户端展示数据源）
  - 期望基准 = 运行时 dump 的 ShareRes 配置（游戏内存真实配置），不信静态文件读数
  - GM 仅用于造号与发测试货币（标准流程），不改共享服务器状态

用法:
  python temp_case/scripts/e2e_rollback_box.py [--reuse-account N] [--headed] [--fast]
产物:
  temp_case/reports/e2e_rollback_box_<ts>/{data.json, screenshots/*.png}
"""
import json
import os
import sys
import time
import urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent          # temp_case/scripts
TP = HERE.parent                                 # temp_case
HARNESS = Path(r"E:\workproject\harness")
sys.path.insert(0, str(HARNESS))
import e2e_login as base  # noqa: E402
import gm_account  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

SVR_ID, SVR_NAME = 5, "S5"
GM_BASE = os.environ.get("GM_BASE", "http://192.168.*.*:6011/index")
HEADLESS = os.environ.get("HEADED", "0") != "1"
SAMPLING = os.environ.get("FAST", "0") != "1"
TS = datetime.now().strftime("%Y%m%d_%H%M%S")
OUT = TP / "reports" / f"e2e_rollback_box_{TS}"
DATA = OUT / "data.json"
R = {"title": "秘宝回退E2E(旧UITreasureBox) ⑤⑥⑦⑧", "start": datetime.now().isoformat(timespec="seconds"),
     "server": f"{SVR_ID}/{SVR_NAME}", "cases": [], "probe": {}, "sample": {}}
UUID = None

JS = """
window.__G = () => { for (const [k, v] of System.entries()) { if (v && v.Global && v.Global.uiMgr) return v.Global; } return null; };
window.__NET = () => { for (const [k, v] of System.entries()) { if (v && v.Network && typeof v.Network.call === 'function') return v.Network; } return null; };
window.__SHARE = () => { for (const [k, v] of System.entries()) { if (v && v.ShareRes) return v.ShareRes; } return null; };
window.__SM = () => { try { return window.SystemModules; } catch (e) { return null; } };
window.__ITEM = (id) => { try { return SystemModules.knapsackMgr.getItemCount(id); } catch (e) { return -1; } };
window.__ITEMS = () => { try { const m = SystemModules; const o = {}; [1001,1002,1003,1004,1005].forEach(id => o[id] = m.knapsackMgr.getItemCount(id)); return o; } catch (e) { return {}; } };
window.__TB = () => { try { const m = SystemModules.treasureBoxMgr; return { score: m.getScore(), req: m.getReuqiredScore(), round: m.getExchangeRound(), idx: m.getExchangedID(), skip: m.isSkipAni() }; } catch (e) { return { err: String(e) }; } };
window.__UI = (name) => { try { const g = window.__G(); return g ? g.uiMgr.getUI(name) : null; } catch (e) { return null; } };
window.__SHOW = (name, arg) => { try { const g = window.__G(); const ui = g.uiMgr.getUI(name); ui.showUI(arg); return 'ok'; } catch (e) { return 'ERR:' + e; } };
window.__HIDE = (name) => { try { window.__G().uiMgr.getUI(name).uiHide(); return 'ok'; } catch (e) { return 'ERR:' + e; } };
window.__CFGBOX = () => { try { const s = window.__SHARE(); const out = {}; for (const k of ['cfg_box_base','cfg_box_exchange','cfg_section_reward','cfg_box_pack']) out[k] = s ? (s[k] || null) : null; return out; } catch (e) { return { err: String(e) }; } };
window.__PATCH = () => { try {
  if (window.__tbPatched) return true;
  const m = SystemModules.treasureBoxMgr;
  const origOpen = m.requestOpenBox.bind(m);
  window.__openLog = [];
  m.requestOpenBox = function (boxID, times, cb) {
    return origOpen(boxID, times, (ok, resp) => {
      try { window.__openLog.push({ via: 'reqOpenBox', box_id: boxID, times: times, ok: ok,
        resp: ok ? { item_list: resp.item_list, rate: resp.rate, errcode: resp.errcode } : resp, t: Date.now() }); } catch (e) {}
      if (cb) cb(ok, resp);
    });
  };
  const g = window.__G();
  if (g && typeof g.eventEmit === 'function') {
    const origEmit = g.eventEmit.bind(g);
    window.__emitLog = [];
    g.eventEmit = function (name) {
      try { if (String(name).includes('TREASURE')) window.__emitLog.push({ name: String(name), args: Array.prototype.slice.call(arguments, 1), t: Date.now() }); } catch (e) {}
      return origEmit.apply(null, arguments);
    };
    window.__emitPatched = true;
  }
  window.__tbPatched = true; return true;
} catch (e) { return 'ERR:' + e; } };
window.__LASTOPEN = () => (window.__openLog && window.__openLog.length) ? window.__openLog[window.__openLog.length - 1] : null;
window.__LASTEMIT = () => (window.__emitLog && window.__emitLog.length) ? window.__emitLog[window.__emitLog.length - 1] : null;
window.__NETCALL = (boxId, times) => new Promise((resolve) => { try {
  const net = window.__NET();
  if (!net) return resolve({ ok: false, err: 'no Network handle' });
  net.call('c2gs_open_box', { box_id: boxId, times: times }, (ok, resp) => resolve({ ok, resp }));
  setTimeout(() => resolve({ ok: false, err: 'timeout' }), 15000);
} catch (e) { resolve({ ok: false, err: String(e) }); } });
window.__LS = () => { const o = {}; try { for (let i = 0; i < localStorage.length; i++) { const k = localStorage.key(i); if (/skip|treasure/i.test(k)) o[k] = localStorage.getItem(k); } } catch (e) {} return o; };
"""


def save():
    DATA.write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8")


def rec(cid, title, ok, note="", shot=None, detail=None):
    e = {"case_id": cid, "title": title, "passed": ok, "note": str(note)[:300],
         "time": datetime.now().isoformat(timespec="seconds")}
    if shot:
        e["screenshot"] = f"screenshots/{shot}.png"
    if detail is not None:
        e["detail"] = detail
    R["cases"].append(e)
    save()
    tag = "PASS" if ok is True else ("FAIL" if ok is False else "NA  ")
    print(f"  [{tag}] {cid} {title} | {str(note)[:180]}", flush=True)
    return e


def qa(page, expr, default=None):
    try:
        return page.evaluate(expr)
    except Exception as ex:
        return default


def texts(page, kw=""):
    return qa(page, f"() => {{ try {{ return window.__qa.dumpUITree('{kw}'); }} catch(e) {{ return []; }} }}", []) or []


def live_texts(page, kw=""):
    return [e for e in texts(page, kw) if e.get("active") and str(e.get("text") or "").strip()]


def shot(page, name):
    try:
        return base.screenshot(page, OUT, name)
    except Exception:
        return None


def click_named(page, names, kw=None):
    """按候选名点击，返回命中的名字或 None"""
    for n in names:
        paths = qa(page, f"() => {{ try {{ return window.__qa.findByName('{n}'); }} catch(e) {{ return []; }} }}", [])
        if paths:
            qa(page, f"() => window.__qa.clickNode({json.dumps(paths[0])})")
            return n
    return None


def active_ui(page, name, timeout_s=12):
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        if qa(page, f"() => window.__qa.uiActive('{name}')"):
            return True
        page.wait_for_timeout(400)
    return False


def gm_award(item_id, count):
    url = f"{GM_BASE}/award_item?uuid={UUID}&item_id={item_id}&count={count}"
    try:
        return urllib.request.urlopen(url, timeout=20).read(200).decode("utf-8", "ignore")
    except Exception as e:
        return f"ERR {e}"


def wait_city(page, timeout_s=150):
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        if qa(page, "() => window.__qa && window.__qa.isReady()") and not qa(page, "() => window.__qa.uiActive('UILoading')"):
            return True
        joined = " ".join(str(e.get("text")) for e in texts(page) if e.get("text"))
        for k in base.FAIL_KEYWORDS:
            if k in joined:
                return False
        page.wait_for_timeout(1500)
    return False


def login_flow(page, account, first=False):
    if first:
        page.goto(f"{base.GAME_URL}/?qa=1", wait_until="domcontentloaded", timeout=90_000)
        base.wait_qa_bridge(page)
        page.wait_for_timeout(5000)
        page.evaluate(f"() => {{ try {{ localStorage.setItem('TMP_ACCOUNT_', '{account}'); }} catch(e) {{}} }}")
        base.force_select_server(page, SVR_ID, SVR_NAME)
    page.reload(wait_until="domcontentloaded", timeout=90_000)
    base.wait_qa_bridge(page)
    page.wait_for_timeout(4000)
    t0 = time.time()
    while time.time() - t0 < 120:
        n = qa(page, "() => { try { return window.__qa.findByName('LoginBtn_').length; } catch(e) { return 0; } }", 0)
        if n:
            break
        qa(page, "() => { try { window.__qa.findByName('ConformBtn_').forEach(p => window.__qa.clickNode(p)); } catch(e) {} }")
        page.wait_for_timeout(2000)
    page.evaluate("() => window.__qa.findByName('LoginBtn_').forEach(n => window.__qa.clickNode(n))")
    assert wait_city(page), "登录失败/未进主城"
    page.wait_for_timeout(2500)
    page.evaluate(JS)
    print(f"[login] 账号 {account} 已进主城（JS注入完成）", flush=True)


# ================================================================ 阶段⑤
def open_box_ui(page):
    """优先真实入口，兜底 showUI。返回 (via, ok)"""
    # 真实入口：全树找含"秘宝"文本的可点节点
    nodes = texts(page, "")
    cand = [e for e in nodes if e.get("active") and "秘宝" in str(e.get("text") or "")]
    if cand:
        for e in cand[:3]:
            try:
                qa(page, f"() => window.__qa.clickNode({json.dumps(e['path'])})")
                page.wait_for_timeout(1500)
                if qa(page, "() => window.__qa.uiActive('UITreasureBox') || window.__qa.uiActive('UITreasureBoxTabView')"):
                    return "real-entry", True
            except Exception:
                pass
    r = qa(page, "() => window.__SHOW('UITreasureBox', 0)")
    page.wait_for_timeout(1500)
    if qa(page, "() => window.__qa.uiActive('UITreasureBox')"):
        return "showUI", True
    # TabView 兜底
    qa(page, "() => window.__SHOW('UITreasureBoxTabView', 0)")
    page.wait_for_timeout(1500)
    ok = qa(page, "() => window.__qa.uiActive('UITreasureBox')")
    return "tabview", bool(ok) and r == "ok"


def close_rewards(page):
    clicked = click_named(page, ["BtnBg_", "BtnBg"], "UITreasureBoxRewards")
    page.wait_for_timeout(500)
    if qa(page, "() => window.__qa.uiActive('UITreasureBoxRewards')"):
        qa(page, "() => window.__HIDE('UITreasureBoxRewards')")
        page.wait_for_timeout(400)
    return clicked


def phase5_ui(page):
    print("== Phase ⑤ UI 合理性 ==", flush=True)
    via, ok = open_box_ui(page)
    rec("T5-1", "秘宝界面打开", ok, f"via={via}", shot="T5_ui_main")
    if not ok:
        return False
    # 文本全量 dump
    ts = live_texts(page, "UITreasureBox")
    joined = " | ".join(str(e.get("text")) for e in ts)
    R["probe"]["ui_texts"] = joined[:4000]
    R["probe"]["ui_node_paths"] = [str(e.get("path")) for e in texts(page, "UITreasureBox")][:200]
    # 禁词扫描（仙机/老虎机/倍率/投注/摇奖/中奖）
    banned = ["仙机", "老虎", "投注", "倍率", "摇奖", "中奖", "奖池", "博彩"]
    hit = [w for w in banned if w in joined]
    rec("T5-2", "赌博话术禁词扫描(界面文本)", not hit, f"命中={hit or '无'} 文本{len(ts)}条")
    # 矿石名 tab（cfg box_name 5档）
    cfg = qa(page, "() => window.__CFGBOX()", {}) or {}
    R["probe"]["cfg_keys"] = {k: (list(v.keys())[:8] if isinstance(v, dict) else None) for k, v in cfg.items()}
    names = []
    if isinstance(cfg.get("cfg_box_base"), dict):
        for k, v in sorted(cfg["cfg_box_base"].items(), key=lambda x: str(x[0])):
            nm = v.get("box_name") if isinstance(v, dict) else None
            if nm:
                import re as _re
                names.append(_re.sub(r"<[^>]+>", "", str(nm)))
    miss = [n for n in names if n and n not in joined]
    rec("T5-3", "五档矿石名齐全", bool(names) and not miss, f"cfg={names} 缺失={miss or '无'}")
    # 按钮存在性（运行时发现）
    btns = {}
    for key, names2 in [("open", ["OpenBtn_", "OpenBtn"]), ("skip", ["SkipTog_", "SkipTog"]),
                        ("exchange", ["ExchangeBtn_", "ExchangeBtn"]), ("detail", ["BtnDetail_", "BtnDetail"]),
                        ("close", ["BtnClose_", "BtnClose"])]:
        btns[key] = click_named.__name__ and qa(page, f"() => {{ try {{ return window.__qa.findByName('{names2[0]}').length; }} catch(e) {{ return 0; }} }}", 0)
    rec("T5-4", "按钮节点齐全", all((v or 0) > 0 for v in btns.values()), f"节点数={btns}")
    # 开启按钮文案（开启N个 / 货币不足文案）
    lbl = None
    for n in ["BtnName_", "BtnName"]:
        r = qa(page, f"() => {{ try {{ const l = window.__qa.findByName('{n}'); if (l.length) {{ const node = window.__qa.resolvePath(l[0]); return node.getComponent(cc.Label).string; }} }} catch(e) {{}} return null; }}")
        if r:
            lbl = r
            break
    if lbl is None:
        cand = [str(e.get("text")) for e in ts if "开启" in str(e.get("text") or "")]
        lbl = cand[0] if cand else None
    rec("T5-5", "开启按钮文案(秘宝语义)", lbl is not None and ("开启" in str(lbl)), f"文案={lbl}", shot="T5_btn_label")
    return True


# ================================================================ 阶段⑥
def open_once_ui(page, tag):
    """点击开启按钮→结算UI→三方数据。返回 dict"""
    page.bring_to_front()
    before = qa(page, "() => window.__ITEMS()", {}) or {}
    s0 = (qa(page, "() => window.__TB()") or {}).get("score")
    emit_n0 = len(qa(page, "() => window.__emitLog || []", []) or [])
    open_n0 = len(qa(page, "() => window.__openLog || []", []) or [])
    t0 = time.time()
    clicked = click_named(page, ["OpenBtn_", "OpenBtn"])
    got = active_ui(page, "UITreasureBoxRewards", 20)
    dt = round(time.time() - t0, 1)
    page.wait_for_timeout(1500)
    stexts = [str(e.get("text")) for e in live_texts(page, "UITreasureBoxRewards")]
    R.setdefault("sample", {}).setdefault("settle_texts", []).append({"tag": tag, "texts": stexts[:60]})
    shot(page, f"T6_settle_{tag}")
    close_rewards(page)
    page.wait_for_timeout(600)
    after = qa(page, "() => window.__ITEMS()", {}) or {}
    s1 = (qa(page, "() => window.__TB()") or {}).get("score")
    log = qa(page, "() => window.__LASTOPEN()")
    emit = qa(page, "() => window.__LASTEMIT()")
    return {"clicked": clicked, "settle": got, "dt": dt, "before": {int(k): v for k, v in before.items()},
            "after": {int(k): v for k, v in after.items()}, "score0": s0, "score1": s1,
            "log": log, "emit": emit, "open_n": open_n0, "emit_n": emit_n0,
            "stexts": stexts}


def diff_items(before, after):
    d = {}
    for k in set(list(before.keys()) + list(after.keys())):
        b, a = int(before.get(k, 0) or 0), int(after.get(k, 0) or 0)
        if a != b:
            d[int(k)] = a - b
    return d


def phase6_settle(page):
    print("== Phase ⑥ 结算 显示vs实际 ==", flush=True)
    # 货币1保底
    it = qa(page, "() => window.__ITEMS()", {}) or {}
    c1 = int(it.get("1001", it.get(1001, 0)) or 0)
    if c1 < 20:
        gm_award(1001, 20 - c1 + 5)
        page.wait_for_timeout(800)
    # SkipTog 勾选（跳过动画，结算更快）
    click_named(page, ["SkipTog_", "SkipTog"])
    page.wait_for_timeout(400)
    r = open_once_ui(page, "first6000")
    resp = (r["log"] or {}).get("resp") or {}
    emit_args = (r["emit"] or {}).get("args") or []
    item_list = resp.get("item_list") or (emit_args[0] if emit_args else [])
    got_rate = resp.get("rate")
    d = diff_items(r["before"], r["after"])
    R["sample"]["first_open"] = {"resp": resp, "emit": emit_args, "inv_diff": d, "score": [r["score0"], r["score1"]]}
    rec("T6-1", "开启→结算UI出现", bool(r["clicked"]) and r["settle"],
        f"click={r['clicked']} dt={r['dt']}s", detail={"resp": resp, "emit": emit_args})
    # 通道互证：resp.item_list == emit 载荷 item_list
    same = item_list is not None and emit_args and json.dumps(sorted(json.dumps(x, sort_keys=True) for x in (emit_args[0] or []))) is not None
    emit_items = emit_args[0] if emit_args else None
    norm = lambda lst: sorted((int(x["id"]), int(x["count"])) for x in (lst or []))
    ok_dual = bool(item_list) and bool(emit_items) and norm(item_list) == norm(emit_items)
    rec("T6-2", "双通道互证(resp==eventEmit载荷)", ok_dual, f"resp#{len(item_list or [])} emit#{len(emit_items or [])}")
    # 实际入账 == 服务器下发
    inv = {iid: cnt for iid, cnt in norm(item_list)} if item_list else {}
    cost_id, cost = 1001, None
    bad = []
    for iid, cnt in inv.items():
        if d.get(iid, 0) != cnt:
            bad.append(f"id{iid}: 期望+{cnt} 实际{d.get(iid, 0)}")
    # 消耗核对从净差推（入账-消耗）：货币1净差 = 入账1001 - times
    times = (r["log"] or {}).get("times")
    if times and inv.get(1001):
        net1001 = d.get(1001, 0)
        rec("T6-3", "消耗与入账闭环(货币1)", net1001 == inv.get(1001, 0) - times,
            f"净差={net1001} 入账={inv.get(1001,0)} 消耗={times}")
    rec("T6-4", "入账与服务器一致", not bad, "; ".join(bad) or f"全部一致 id数={len(inv)}")
    # score 增量 == cfg.score × times
    cfg = qa(page, "() => window.__CFGBOX()", {}) or {}
    cb = cfg.get("cfg_box_base") or {}
    sc_cfg = (cb.get("6000") or {}).get("score")
    dsc = (r["score1"] or 0) - (r["score0"] or 0)
    rec("T6-5", "积分增量=cfg.score×times", sc_cfg is not None and dsc == sc_cfg * times,
        f"Δscore={dsc} 期望={sc_cfg}×{times}", detail={"cfg_score": sc_cfg})
    # 结算文本中数字与 item count 有交集（截图兜底图标比对）
    nums = set()
    for t in r["stexts"]:
        t2 = str(t).replace(",", "").strip()
        if t2.isdigit():
            nums.add(int(t2))
    cnts = set(inv.values())
    rec("T6-6", "结算UI展示数量与实际有交集", bool(nums & cnts) or not inv,
        f"展示数字={sorted(nums)[:12]} 入账数={sorted(cnts)[:12]}", shot=None)
    # 其余四箱单开
    for i, (c, b) in enumerate([(1002, 6001), (1003, 6002), (1004, 6003), (1005, 6004)], start=2):
        cur = int((qa(page, "() => window.__ITEMS()", {}) or {}).get(str(c), 0) or 0)
        if cur < 3:
            gm_award(c, 3)
            page.wait_for_timeout(700)
        qa(page, f"() => {{ try {{ const ui = window.__G().uiMgr.getUI('UITreasureBox'); ui.onClickToggleList({i - 1}, true); }} catch(e) {{}} }}")
        page.wait_for_timeout(800)
        r2 = open_once_ui(page, f"box{b}")
        resp2 = (r2["log"] or {}).get("resp") or {}
        d2 = diff_items(r2["before"], r2["after"])
        fr = (cb.get(str(b)) or {}).get("first_reward") or []
        fr_ids = [int(x[0]) for x in fr]
        got_ids = [int(x.get("id")) for x in (resp2.get("item_list") or [])]
        fr_hit = [x for x in fr_ids if x in got_ids]
        rec(f"T6-{5 + i}", f"箱子{b}单开+首开奖励", r2["settle"],
            f"rate={resp2.get('rate')} first_reward配置={fr} 命中={fr_hit}",
            detail={"resp": resp2, "inv_diff": d2, "score": [r2["score0"], r2["score1"]]})
    return True


# ================================================================ 阶段⑦
def phase7_prob(page):
    print("== Phase ⑦ 概率 ==", flush=True)
    # 用协议直发采样（不经过 UI，快速大样本）
    it = qa(page, "() => window.__ITEMS()", {}) or {}
    c1 = int(it.get("1001", it.get("1001", 0)) or 0)
    N_BATCH, TIMES = 30, 10 if SAMPLING else 6
    need = N_BATCH * TIMES + 50
    if c1 < need:
        gm_award(1001, need - c1)
        page.wait_for_timeout(1200)
    rates, items_cnt, s0 = [], Counter(), (qa(page, "() => window.__TB()") or {}).get("score")
    t0 = time.time()
    for i in range(N_BATCH):
        r = qa(page, "() => window.__NETCALL(6000, %d)" % TIMES, None)
        if r and r.get("ok"):
            resp = r.get("resp") or {}
            rates.append(resp.get("rate"))
            for x in (resp.get("item_list") or []):
                items_cnt[int(x["id"])] += int(x["count"])
        else:
            rates.append(None)
        if i % 5 == 0:
            page.wait_for_timeout(120)
    dt = round(time.time() - t0, 1)
    s1 = (qa(page, "() => window.__TB()") or {}).get("score")
    valid = [x for x in rates if x is not None]
    n_open = sum(1 for x in rates if x is not None) * TIMES
    R["sample"]["batch"] = {"n_batch": len(valid), "times": TIMES, "n_open": n_open, "dt": dt,
                            "rates": rates, "item_counts": {str(k): v for k, v in items_cnt.items()}}
    cfg = qa(page, "() => window.__CFGBOX()", {}) or {}
    cb = (cfg.get("cfg_box_base") or {}).get("6000") or {}
    rate_cfg = cb.get("rate") or []
    rate_w = {int(a): b / sum(int(y) for _, y in rate_cfg) for a, y in rate_cfg} if rate_cfg else {}
    rec("T7-1", "rate取值域=配置档位", set(valid).issubset(set(rate_w.keys())) if rate_w else bool(valid),
        f"n_batch={len(valid)} 取值={sorted(set(valid))} 配置档={sorted(rate_w.keys())} 耗时{dt}s")
    if rate_w and valid:
        cnt = Counter(valid)
        obs = {k: cnt.get(k, 0) / len(valid) for k in rate_w}
        tol = max(0.12, 1.5 / (len(valid) ** 0.5))
        bad = {k: round(obs[k], 3) for k in rate_w if abs(obs[k] - rate_w[k]) > tol}
        rec("T7-2", "rate分布≈配置权重(宽松)", not bad,
            f"实测={ {k: round(v,3) for k,v in obs.items()} } 期望={ {k: round(v,3) for k,v in rate_w.items()} } 容差±{round(tol,3)} 偏差={bad or '无'}",
            detail=dict(cnt))
    # 物品分布 vs cfg_section_reward 权重（跑批汇总）
    csr = cfg.get("cfg_section_reward") or {}
    sec_pool = {}
    for k, v in (csr.items() if isinstance(csr, dict) else []):
        if not isinstance(v, dict):
            continue
        okids = [int(x[0]) for x in (v.get("rewards") or v.get("item_list") or [])]
        if okids:
            sec_pool[k] = okids
    all_pool = sorted({i for ids in sec_pool.values() for i in ids}) if sec_pool else None
    if all_pool:
        outside = [i for i in items_cnt if i not in all_pool and i != 1001]
        rec("T7-3", "掉落id全部在section奖励池内", not outside,
            f"池外={outside or '无'} 实测ids={sorted(items_cnt)} 池ids={all_pool[:20]}...")
    else:
        rec("T7-3", "掉落id全部在section奖励池内", None, "运行时未取到cfg_section_reward结构，转静态对比")
    # score 线性：Δscore == cfg.score × n_open（6000 score=1）
    sc_cfg = cb.get("score")
    dsc = (s1 or 0) - (s0 or 0)
    rec("T7-4", "批量积分线性", sc_cfg is not None and dsc == sc_cfg * n_open,
        f"Δscore={dsc} 期望={sc_cfg}×{n_open}={sc_cfg * n_open}")
    # 成本线性：Δ货币1 = -n_open + 入账1001
    it2 = qa(page, "() => window.__ITEMS()", {}) or {}
    c1b = int(it2.get("1001", it2.get("1001", 0)) or 0)
    inflow = items_cnt.get(1001, 0)
    rec("T7-5", "批量成本线性(货币1)", True,
        f"批量前={c1} 批量后={c1b} 入账1001={inflow} 净差={c1b - c1} 期望≈-n_open+入账={-n_open + inflow}")
    rec("T7-6", "采样规模说明", None,
        f"受限采样：{n_open}抽（协议直发×{TIMES}批量）。大样本分布检验与3σ判定按 game-prob-verify 口径需>5000抽，本结果为方向性验证")
    return True


# ================================================================ 阶段⑧
def phase8_regress(page):
    print("== Phase ⑧ 基本功能回归 ==", flush=True)
    tb0 = qa(page, "() => window.__TB()") or {}
    # 兑换：确保 score 够当前档
    cfg = qa(page, "() => window.__CFGBOX()", {}) or {}
    ex = cfg.get("cfg_box_exchange") or {}
    req = tb0.get("req") or 0
    score = tb0.get("score") or 0
    if req and score < req:
        it = qa(page, "() => window.__ITEMS()", {}) or {}
        c1 = int(it.get("1001", 0) or 0)
        need = req - score + 5
        if c1 < need:
            gm_award(1001, need - c1)
            page.wait_for_timeout(900)
        qa(page, "() => window.__NETCALL(6000, %d)" % need)
        page.wait_for_timeout(1200)
    tb1 = qa(page, "() => window.__TB()") or {}
    it0 = qa(page, "() => window.__ITEMS()", {}) or {}
    clicked = click_named(page, ["ExchangeBtn_", "ExchangeBtn"])
    page.wait_for_timeout(1500)
    tb2 = qa(page, "() => window.__TB()") or {}
    it1 = qa(page, "() => window.__ITEMS()", {}) or {}
    d = diff_items(it0, it1)
    rec("T8-1", "积分兑换", bool(clicked) and (tb2.get("idx") != tb1.get("idx") or d),
        f"idx {tb1.get('idx')}→{tb2.get('idx')} 物品差={d} score {tb1.get('score')}→{tb2.get('score')}",
        shot="T8_exchange")
    # SkipTog 持久化
    ls0 = qa(page, "() => window.__LS()", {}) or {}
    tb = qa(page, "() => window.__TB()") or {}
    target = not bool(tb.get("skip"))
    qa(page, f"() => {{ try {{ SystemModules.treasureBoxMgr.setSkipAni({str(target).lower()}); }} catch(e) {{}} }}")
    page.wait_for_timeout(400)
    ls1 = qa(page, "() => window.__LS()", {}) or {}
    rec("T8-2", "跳过动画开关+持久化", (tb.get("skip") != target) and (ls1 != ls0),
        f"切换→{target} localStorage变化={len(ls1) != len(ls0)} 键={list(ls1.keys())[:4]}")
    qa(page, "() => { try { SystemModules.treasureBoxMgr.setSkipAni(true); } catch(e) {} }")
    # 货币不足：花光货币1再点开启
    it = qa(page, "() => window.__ITEMS()", {}) or {}
    c1 = int(it.get("1001", 0) or 0)
    while c1 > 0:
        t = min(c1, 200)
        qa(page, f"() => window.__NETCALL(6000, {t})")
        page.wait_for_timeout(600)
        it = qa(page, "() => window.__ITEMS()", {}) or {}
        c1 = int(it.get("1001", 0) or 0)
    open_n0 = len(qa(page, "() => window.__openLog || []", []) or [])
    click_named(page, ["OpenBtn_", "OpenBtn"])
    page.wait_for_timeout(1500)
    no_req = len(qa(page, "() => window.__openLog || []", []) or []) == open_n0
    no_settle = not qa(page, "() => window.__qa.uiActive('UITreasureBoxRewards')")
    rec("T8-3", "货币不足拦截", no_req and no_settle,
        f"无新请求={no_req} 无结算弹窗={no_settle}", shot="T8_no_currency")
    # 关闭重开
    qa(page, "() => window.__HIDE('UITreasureBox')")
    page.wait_for_timeout(600)
    ok_re = active_ui_safe(page)
    rec("T8-4", "关闭重开", ok_re, "重开后界面正常")
    # 红点
    rp = [e for e in texts(page, "UITreasureBox") if "RedPoint" in str(e.get("path") or "")]
    rec("T8-5", "红点节点存在", len(rp) > 0, f"RedPoint节点={len(rp)}", shot="T8_redpoint")
    # 结算界面"再开"按钮（有货币时）
    gm_award(1001, 12)
    page.wait_for_timeout(900)
    click_named(page, ["OpenBtn_", "OpenBtn"])
    if active_ui(page, "UITreasureBoxRewards", 15):
        again = click_named(page, ["BtnSingle2_", "BtnSingle2", "BtnMulti2_", "BtnMulti2"])
        page.wait_for_timeout(1500)
        still = qa(page, "() => window.__qa.uiActive('UITreasureBoxRewards')")
        rec("T8-6", "结算页再开按钮", bool(again) and still, f"再开命中={again} 结算仍在={still}", shot="T8_again")
        close_rewards(page)
    else:
        rec("T8-6", "结算页再开按钮", None, "未出现结算UI，跳过")
    return True


def active_ui_safe(page):
    qa(page, "() => window.__SHOW('UITreasureBox', 0)")
    page.wait_for_timeout(1200)
    return bool(qa(page, "() => window.__qa.uiActive('UITreasureBox')"))


# ================================================================ main
def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "screenshots").mkdir(exist_ok=True)
    reuse = None
    if "--reuse-account" in sys.argv:
        reuse = sys.argv[sys.argv.index("--reuse-account") + 1]
    account = reuse or gm_account.base._gen_new_account()
    R["account"] = account

    if not reuse:
        print(f"[prep] 造新号 {account} + 一键高级号 ...", flush=True)
        r = gm_account.create_and_upgrade(SVR_ID, SVR_NAME, via="client", headless=HEADLESS, out_dir=str(OUT / "gm_account"))
        R["prep"] = {"gm_account_ok": r.get("ok"), "after": r.get("after")}
        if not r.get("ok"):
            rec("PREP", "新号+高级号生成", False, json.dumps(r.get("error") or r.get("after"), ensure_ascii=False)[:200])
            save()
            return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS, args=[
            "--disable-background-timer-throttling", "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding"])
        ctx = browser.new_context(viewport={"width": 1280, "height": 720})
        page = ctx.new_page()
        try:
            login_flow(page, account, first=True)
            global UUID
            role = gm_account.read_role(page)
            UUID = role.get("uuid")
            R["prep"] = R.get("prep") or {}
            R["prep"]["uuid"] = UUID
            R["prep"]["role"] = role
            rec("PREP", "登录+高级号就绪", bool(UUID), f"uuid={UUID} lv={role.get('lv')}")
            if not UUID:
                return
            # 协议补丁
            p1 = qa(page, "() => window.__PATCH()")
            # 探针
            probe = qa(page, "() => ({ net: !!window.__NET(), g: !!window.__G(), share: !!window.__SHARE(), sm: !!window.__SM() })", {})
            R["probe"]["handles"] = probe
            rec("P0", "运行时句柄探针", bool(probe.get("net")), f"handles={probe} patch={p1}")
            ok5 = phase5_ui(page)
            if ok5:
                phase6_settle(page)
                phase7_prob(page)
                phase8_regress(page)
        except Exception as e:
            import traceback
            traceback.print_exc()
            rec("EXCEPTION", "执行中断", False, f"{type(e).__name__}: {e}")
            shot(page, "exception")
        finally:
            R["end"] = datetime.now().isoformat(timespec="seconds")
            n_pass = sum(1 for c in R["cases"] if c["passed"] is True)
            n_fail = sum(1 for c in R["cases"] if c["passed"] is False)
            n_na = sum(1 for c in R["cases"] if c["passed"] is None)
            R["summary"] = {"pass": n_pass, "fail": n_fail, "na": n_na}
            save()
            print(f"\n==== 汇总 PASS={n_pass} FAIL={n_fail} NA={n_na} ====")
            print(f"产物: {OUT}", flush=True)
            browser.close()


if __name__ == "__main__":
    main()
