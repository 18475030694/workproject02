# -*- coding: utf-8 -*-
"""三大礼包弹窗 · 「三、修改涉及的回归测试清单」运行时 E2E

对象：
  id29 每日特惠  (AUTO_OPEN 13, UIComIntegrationTabView)  通关70关开启时弹一次
  id50 超值特惠  (AUTO_OPEN 14, UIBestGift)               通关30关开启, 每次重登弹一次
  30001 富甲礼包 (AUTO_OPEN 15, UIYxActLimitTimeGift)     活动开启时弹一次(LocalStorage 记录)

用例域（用户清单）：新手剧情/引导不遮挡、界面打开效果、不同情况(遮挡/在线/重登)打开、
跳转与关闭、活动结束关闭消失、道具可购买/领取与实际获得(knapsackMgr 入账实证)。

证据纪律：断言只依赖运行时证据(uiActive/节点/入账/GM回执)，静态推演仅写 note。
S5 共享环境纪律：30001 起止各记录一次原状并还原(P0→R0)；set_mainline_stage 仅作用于本测试新号。

用法:
  python temp_case/scripts/e2e_gift_popup.py [--headed]
产物:
  temp_case/reports/e2e_gift_popup_<ts>/{data.json, screenshots/*.png} + e2e_gift_popup_summary_<ts>.md
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
TP = HERE.parent
HARNESS = Path(r"E:\workproject\harness")
sys.path.insert(0, str(HARNESS))
import e2e_login as base  # noqa: E402
import gm_account  # noqa: E402
import gm_yxact  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

SVR_ID, SVR_NAME = 5, "S5"
GM_BASE = os.environ.get("GM_BASE", "http://192.168.*.*:6011/index")
ACT = 30001  # 富甲礼包活动组
TS = datetime.now().strftime("%Y%m%d_%H%M%S")
OUT = TP / "reports" / f"e2e_gift_popup_{TS}"
DATA = OUT / "data.json"
R = {"title": "三大礼包弹窗回归E2E(三、修改涉及的回归测试清单)", "start": datetime.now().isoformat(timespec="seconds"),
     "server": f"{SVR_ID}/{SVR_NAME}", "account": None, "uuid": None, "cases": [], "probe": {}}
UUID = None

JS = """
window.__G = () => { for (const [k, v] of System.entries()) { if (v && v.Global && v.Global.uiMgr) return v.Global; } return null; };
window.__SM = () => { try { return window.SystemModules; } catch (e) { return null; } };
window.__SHARE = () => { for (const [k, v] of System.entries()) { if (v && v.ShareRes) return v.ShareRes; } return null; };
window.__MAIN = () => { try { return window.__G().uiMgr.isMainInTop(); } catch (e) { return null; } };
window.__HIDE = (name) => { try { window.__G().uiMgr.getUI(name).uiHide(); return 'ok'; } catch (e) { return 'ERR:' + e; } };
window.__SHOW = (name, arg) => { try { const g = window.__G(); const ui = g.uiMgr.getUI(name); ui.showUI(arg); return 'ok'; } catch (e) { return 'ERR:' + e; } };
window.__AO = () => { try { const m = SystemModules.autoOpenMgr;
  return { list: (m.openList || []).map(x => x.id), showing: !!m.isShowing, hasCheck: !!m.hasCheck }; } catch (e) { return { err: String(e) }; } };
window.__ML = () => { try { const m = SystemModules.mainLevelMgr; const o = {};
  for (const k in m) { if (typeof m[k] === 'number' && /pass|stage|chapter|main/i.test(k)) o[k] = m[k]; } return o; } catch (e) { return { err: String(e) }; } };
window.__BG = () => { try { const m = SystemModules.bestGiftMgr;
  return { open: m.isOpen ? !!m.isOpen() : null, gift: m.gift_info || null }; } catch (e) { return { err: String(e) }; } };
window.__SYSOPEN = (ids) => { try { const m = SystemModules.sysOpenMgr; const o = {};
  ids.forEach(id => { try { o[id] = m.isSysOpen ? !!m.isSysOpen(id) : null; } catch (e) { o[id] = 'ERR'; } }); return o; } catch (e) { return { err: String(e) }; } };
window.__YX = () => { try { const m = SystemModules.yxActMgr; const d = m.actData || m.act_data || {};
  return { ids: Object.keys(d).map(Number), has30001: !!d[30001] }; } catch (e) { return { err: String(e) }; } };
window.__LT = () => { try { const m = SystemModules.yxActLimitTimeGift; const o = { keys: Object.keys(m).slice(0, 50) };
  try { o.giftInfo = m.gift_info || m.actData || null; } catch (e) {} return o; } catch (e) { return { err: String(e) }; } };
window.__LSK = (re) => { const o = {}; try { const uuid = (window.__G() || {}).playerUuid;
  for (let i = 0; i < localStorage.length; i++) { const k = localStorage.key(i);
    if (new RegExp(re).test(k)) o[k] = localStorage.getItem(k); } o.__uuid = uuid; } catch (e) {} return o; };
window.__ITEMC = (ids) => { try { const o = {}; ids.forEach(id => o[id] = SystemModules.knapsackMgr.getItemCount(id)); return o; } catch (e) { return { err: String(e) }; } };
window.__CFG = (names) => { try { const s = window.__SHARE(); const o = {};
  names.forEach(n => { const c = s ? s[n] : null;
    o[n] = c ? (Object.keys(c).length <= 12 ? c : { __len: Object.keys(c).length, sample: Object.keys(c).slice(0, 6) }) : null; }); return o; } catch (e) { return { err: String(e) }; } };
window.__CFGONE = (cfgName, key) => { try { const s = window.__SHARE(); const c = s[cfgName] || {}; return c[key] !== undefined ? c[key] : null; } catch (e) { return null; } };
window.__CHARGE_BUY = (cfgName, key) => { try { const s = window.__SHARE(); const c = (s[cfgName] || {})[key];
  if (!c) return null; return { id: c.id, notify_key: c.notify_key, pack_id: c.pack_id, name: c.name }; } catch (e) { return null; } };
window.__PACK_REWARDS = (cfgName, key) => { try { const s = window.__SHARE(); const c = (s[cfgName] || {})[key] || {};
  const out = []; const pool = c.rewards || c.reward || c.reward_list || [];
  if (Array.isArray(pool)) pool.forEach(r => { if (Array.isArray(r)) out.push({ id: r[0], num: r[1] });
    else if (r && r.id !== undefined) out.push({ id: r.id, num: r.num || r.count || 1 }); });
  return out; } catch (e) { return []; } };
"""


def save():
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8")


def rec(cid, title, ok, note="", shot=None, detail=None):
    e = {"case_id": cid, "title": title, "passed": ok, "note": str(note)[:400],
         "time": datetime.now().isoformat(timespec="seconds")}
    if shot:
        e["screenshot"] = f"screenshots/{shot}.png"
    if detail is not None:
        e["detail"] = detail
    R["cases"].append(e)
    save()
    tag = "PASS" if ok is True else ("FAIL" if ok is False else "NA  ")
    print(f"  [{tag}] {cid} {title} | {str(note)[:200]}", flush=True)
    return e


def qa(page, expr, default=None):
    try:
        return page.evaluate(expr)
    except Exception:
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


def click_named(page, names):
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


def inactive_ui(page, name, settle_s=8):
    """settle_s 秒内始终不出现才算『不弹』"""
    t0 = time.time()
    while time.time() - t0 < settle_s:
        if qa(page, f"() => window.__qa.uiActive('{name}')"):
            return False
        page.wait_for_timeout(500)
    return True


def gm(cmd, **params):
    url = f"{GM_BASE}/{cmd}" + ("?" + urllib.parse.urlencode(params) if params else "")
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            return {"status": resp.status, "body": resp.read().decode("utf-8", "ignore")[:200]}
    except Exception as e:  # noqa: BLE001
        return {"status": -1, "err": str(e)}


def wait_city(page, timeout_s=180):
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


def inject_js(page):
    page.evaluate(JS)
    page.evaluate("() => { try { window.__qa; } catch(e) {} }")


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
    inject_js(page)
    print(f"[login] 账号 {account} 已进主城（JS注入完成）", flush=True)


def close_popup(page, ui_name, btn_names=("BtnClose_", "BtnClose", "CloseBtn_", "CloseBtn", "BtnBg_", "BtnBg")):
    clicked = click_named(page, list(btn_names))
    page.wait_for_timeout(600)
    if qa(page, f"() => window.__qa.uiActive('{ui_name}')"):
        r = qa(page, f"() => window.__HIDE('{ui_name}')")
        page.wait_for_timeout(500)
        return f"hide:{r}" if not clicked else f"btn:{clicked}+hide"
    return f"btn:{clicked}" if clicked else "none"


def item_delta(page, ids, before):
    after = qa(page, f"() => window.__ITEMC({json.dumps(ids)})", {}) or {}
    delta = {}
    for k, v in after.items():
        b = before.get(k, 0)
        if isinstance(v, int) and isinstance(b, int) and v != b:
            delta[k] = {"before": b, "after": v}
    return delta, after


def gm_recharge(notify_key):
    return gm("recharge_notifykey", uuid=UUID, notify_key=notify_key)


# ================================================================ 用例
def p0_probe(page):
    print("== P0 环境探针 ==", flush=True)
    R["probe"]["ml_fields"] = qa(page, "() => window.__ML()", {})
    R["probe"]["ao"] = qa(page, "() => window.__AO()", {})
    R["probe"]["bg"] = qa(page, "() => window.__BG()", {})
    R["probe"]["sysopen_29_50"] = qa(page, "() => window.__SYSOPEN([29,50])", {})
    R["probe"]["yxact"] = qa(page, "() => window.__YX()", {})
    R["probe"]["lt"] = qa(page, "() => window.__LT()", {})
    R["probe"]["ls_gift"] = qa(page, "() => window.__LSK('yxact_limit_time_gift_new_act')", {})
    R["probe"]["cfg"] = qa(page, "() => window.__CFG(['cfg_auto_open','cfg_charge_best_gift_pack','cfg_charge_daily_gift_pack','cfg_charge_yxact_limit_time_gift','cfg_best_gift_pack'])", {})
    save()
    yx = R["probe"]["yxact"] or {}
    R["probe"]["act30001_original_open"] = bool(yx.get("has30001")) if "err" not in yx else None
    rec("P0", "环境探针+记录30001原状", True,
        f"sysopen={R['probe']['sysopen_29_50']} yx30001={yx.get('has30001')} "
        f"ml={R['probe']['ml_fields']} bg={str(R['probe']['bg'])[:120]}")


def t1_cold_start(page):
    print("== T1 新号冷启动(新手剧情/引导) ==", flush=True)
    shot(page, "T1_cold_main")
    guide_like = []
    for name in ("UIGuide", "UIGuideTalk", "UIMainLineTalk", "UIMainTalk", "UINewBee"):
        if qa(page, f"() => window.__qa.uiActive('{name}')"):
            guide_like.append(name)
    joined = " ".join(str(e.get("text")) for e in live_texts(page)[:400])
    ok = (not qa(page, "() => window.__qa.uiActive('UIBestGift')")) and \
         (not qa(page, "() => window.__qa.uiActive('UIYxActLimitTimeGift')")) and \
         (not qa(page, "() => window.__qa.uiActive('UIComIntegrationTabView')"))
    rec("T1", "冷启动无三目标弹窗遮挡(引导期)", ok,
        f"guideUI={guide_like or '未捕获(记录性)'} 文本样例={joined[:100]}", detail={"guide_like": guide_like})


def b_group(page):
    print("== B组 id50 超值特惠(30关/每次重登) ==", flush=True)
    # T2 stage29 → 重登 → 不弹
    r29 = gm("set_mainline_stage", uuid=UUID, stage_id=29)
    page.wait_for_timeout(2000)
    login_flow(page, R["account"])
    page.wait_for_timeout(6000)  # firstCheck 1.8s + 队列消化
    no_pop = inactive_ui(page, "UIBestGift", settle_s=8)
    rec("T2", "29关重登: 超值特惠不弹", no_pop,
        f"gm={r29.get('body', r29)} sysopen50={(qa(page, '() => window.__SYSOPEN([50])', {}) or {})}",
        shot="T2_no_popup_29")
    # T3 在线跨30 → 弹
    r30 = gm("set_mainline_stage", uuid=UUID, stage_id=30)
    popped = active_ui(page, "UIBestGift", timeout_s=15)
    ao = qa(page, "() => window.__AO()", {})
    shot(page, "T3_popup_30")
    rec("T3", "在线跨30关: 超值特惠自动弹出", popped,
        f"gm={r30.get('body', r30)} ao={ao}", shot=None if popped else "T3_popup_30")
    if not popped:
        return
    # T5 界面内容+关闭
    ts = live_texts(page, "UIBestGift")
    joined = " | ".join(str(e.get("text")) for e in ts)
    R["probe"]["bestgift_texts"] = joined[:2500]
    shot(page, "T5_bestgift_ui")
    how = close_popup(page, "UIBestGift")
    closed = not qa(page, "() => window.__qa.uiActive('UIBestGift')")
    rec("T5", "超值特惠界面可关闭(回主城)", closed and qa(page, "() => window.__MAIN()") is True,
        f"close={how} 文本样例={joined[:120]}", detail={"texts": joined[:1200]})
    # T6 购买+实际获得 (giftConf 数据驱动)
    bg = qa(page, "() => window.__BG()", {}) or {}
    gift = bg.get("gift") or {}
    gconf_id = gift.get("id") or gift.get("gift_id")
    chg = qa(page, f"() => window.__CHARGE_BUY('cfg_charge_best_gift_pack', '{gconf_id}')") if gconf_id else None
    pack_id = (chg or {}).get("pack_id") or gift.get("pack_id")
    rewards = qa(page, f"() => window.__PACK_REWARDS('cfg_best_gift_pack', '{pack_id}')", []) or [] if pack_id else []
    ids = [r["id"] for r in rewards if r.get("id") is not None]
    before = qa(page, f"() => window.__ITEMC({json.dumps(ids)})", {}) or {} if ids else {}
    nk = (chg or {}).get("notify_key")
    if nk:
        rp = gm_recharge(nk)
        page.wait_for_timeout(3500)
        delta, _ = item_delta(page, ids, before)
        tjoin = " ".join(str(e.get("text")) for e in live_texts(page, "UIBestGift"))
        state_changed = any(w in tjoin for w in ("已购", "已领取", "已购买")) if tjoin else False
        shot(page, "T6_bestgift_after_buy")
        rec("T6", "超值特惠购买+实际获得", bool(delta) or state_changed,
            f"notify_key={nk} gm={rp.get('body', rp)} 入账Δ={delta or '无'} 文案含已购={state_changed}",
            detail={"rewards": rewards, "before": before, "delta": delta})
        # 购买后关闭重开界面再验证状态
        login_flow(page, R["account"])
        page.wait_for_timeout(5000)
        if qa(page, "() => window.__qa.uiActive('UIBestGift')"):
            close_popup(page, "UIBestGift")
    else:
        rec("T6", "超值特惠购买+实际获得", None, f"gift_conf未取到(id={gconf_id}) GM跳过")
    # T4 重登再弹(每次重登弹一次)
    if not nk:  # 无购买分支时 T4 已在上方重登过，这里补登一次保证口径一致
        login_flow(page, R["account"])
        page.wait_for_timeout(6000)
    popped2 = active_ui(page, "UIBestGift", timeout_s=12)
    shot(page, "T4_relogin_popup")
    rec("T4", "重登后超值特惠再次弹出(每次重登)", popped2, "", shot=None if popped2 else "T4_relogin_popup")
    if popped2:
        close_popup(page, "UIBestGift")


def c_group(page):
    print("== C组 id29 每日特惠(70关/仅一次) ==", flush=True)
    # T7 stage69 → 重登 → 不弹(13 不入队)
    gm("set_mainline_stage", uuid=UUID, stage_id=69)
    page.wait_for_timeout(2000)
    login_flow(page, R["account"])
    page.wait_for_timeout(6000)
    no_pop = inactive_ui(page, "UIComIntegrationTabView", settle_s=8)
    ao = qa(page, "() => window.__AO()", {})
    rec("T7", "69关重登: 每日特惠不弹且id13不入队", no_pop and (13 not in (ao.get("list") or [])),
        f"ao={ao}", shot="T7_no_popup_69")
    # T8 遮挡情况下开启 → 弹窗延迟；移开遮挡 → 弹出
    cover = qa(page, "() => window.__SHOW('UIBoard', 0)")
    covered = cover == "ok" and qa(page, "() => window.__qa.uiActive('UIBoard')")
    r70 = gm("set_mainline_stage", uuid=UUID, stage_id=70)
    page.wait_for_timeout(4000)
    deferred = not qa(page, "() => window.__qa.uiActive('UIComIntegrationTabView')") if covered else None
    if covered:
        qa(page, "() => window.__HIDE('UIBoard')")
        page.wait_for_timeout(600)
    popped = active_ui(page, "UIComIntegrationTabView", timeout_s=15)
    ao2 = qa(page, "() => window.__AO()", {})
    shot(page, "T8_daily_popup")
    if covered:
        rec("T8", "70关开启弹出(遮挡时延迟/移开后弹出)", popped and deferred,
            f"cover={cover} deferred={deferred} gm={r70.get('body', r70)} ao={ao2}")
    else:
        rec("T8", "70关开启弹出", popped, f"遮挡用例NA(cover={cover}) gm={r70.get('body', r70)} ao={ao2}")
    ts = live_texts(page, "UIComIntegrationTabView")
    R["probe"]["daily_texts"] = " | ".join(str(e.get("text")) for e in ts)[:2500]
    if popped:
        shot(page, "T8_daily_ui")
        how = close_popup(page, "UIComIntegrationTabView")
        rec("T8b", "每日特惠集成窗可关闭", not qa(page, "() => window.__qa.uiActive('UIComIntegrationTabView')"), f"close={how}")
        # T10 免费礼包领取(DailyGiftPack.1, pay_id=0)
        rw = qa(page, "() => window.__PACK_REWARDS('cfg_daily_gift_packbase', '20106')", []) or []
        if not rw:
            rw = qa(page, "() => window.__PACK_REWARDS('cfg_daily_gift_packreward', '20106')", []) or []
        ids = [r["id"] for r in rw if r.get("id") is not None]
        before = qa(page, f"() => window.__ITEMC({json.dumps(ids)})", {}) or {} if ids else {}
        rp = gm_recharge("DailyGiftPack.1")
        page.wait_for_timeout(3500)
        delta, _ = item_delta(page, ids, before)
        rec("T10", "每日特惠免费礼包领取+实际获得", bool(delta),
            f"gm={rp.get('body', rp)} 奖励={rw} 入账Δ={delta or '无'}", detail={"delta": delta, "rewards": rw})
    # T9 仅一次: 重登不再弹
    login_flow(page, R["account"])
    page.wait_for_timeout(6000)
    no_pop2 = inactive_ui(page, "UIComIntegrationTabView", settle_s=8)
    ao3 = qa(page, "() => window.__AO()", {})
    rec("T9", "重登后每日特惠不再弹(仅一次)", no_pop2 and (13 not in (ao3.get("list") or [])), f"ao={ao3}")


def d_group(page):
    print("== D组 30001 富甲礼包(开启弹一次/结束关闭) ==", flush=True)
    orig_open = R["probe"].get("act30001_original_open")
    # T11 关闭活动 → 重登 → 不弹
    rc = gm_yxact.gm_close(SVR_ID, ACT)
    page.wait_for_timeout(1500)
    login_flow(page, R["account"])
    page.wait_for_timeout(6000)
    no_pop = inactive_ui(page, "UIYxActLimitTimeGift", settle_s=8)
    ls = qa(page, "() => window.__LSK('yxact_limit_time_gift_new_act')", {}) or {}
    rec("T11", "活动关闭: 重登富甲不弹且无本地记录", no_pop and not {k: v for k, v in ls.items() if k != '__uuid'},
        f"close={rc} ls={ls}")
    # T12 开启活动 → 弹一次
    ro = gm_yxact.gm_open(SVR_ID, ACT)
    popped = active_ui(page, "UIYxActLimitTimeGift", timeout_s=20)
    shot(page, "T12_fujia_popup")
    rec("T12", "活动开启: 富甲礼包自动弹出一次", popped, f"open={ro}", shot=None if popped else "T12_fujia_popup")
    if not popped:
        return
    ts = live_texts(page, "UIYxActLimitTimeGift")
    R["probe"]["fujia_texts"] = " | ".join(str(e.get("text")) for e in ts)[:2500]
    shot(page, "T12_fujia_ui")
    # T15 购买(活动开启期内): notify_key=LimitTimeGift.1
    rw = qa(page, "() => window.__PACK_REWARDS('cfg_yxact_limit_time_gift', '30001')", []) or []
    if not rw:
        rw = qa(page, "() => window.__PACK_REWARDS('cfg_charge_yxact_limit_time_gift', '200001')", []) or []
    ids = [r["id"] for r in rw if r.get("id") is not None]
    before = qa(page, f"() => window.__ITEMC({json.dumps(ids)})", {}) or {} if ids else {}
    rp = gm_recharge("LimitTimeGift.1")
    page.wait_for_timeout(3500)
    delta, _ = item_delta(page, ids, before)
    rec("T15", "富甲礼包购买+实际获得", bool(delta),
        f"gm={rp.get('body', rp)} 奖励源={len(rw)}条 入账Δ={delta or '无'}", detail={"delta": delta, "rewards": rw[:8]})
    # 关闭弹窗 → LS 记录
    how = close_popup(page, "UIYxActLimitTimeGift")
    page.wait_for_timeout(1000)
    ls2 = qa(page, "() => window.__LSK('yxact_limit_time_gift_new_act')", {}) or {}
    rec("T12b", "弹窗可关闭且查看后写本地记录", not qa(page, "() => window.__qa.uiActive('UIYxActLimitTimeGift')"),
        f"close={how} ls_keys={list(ls2.keys())}")
    # T13 重登(活动仍开) → 不再弹
    login_flow(page, R["account"])
    page.wait_for_timeout(6000)
    no_pop2 = inactive_ui(page, "UIYxActLimitTimeGift", settle_s=8)
    rec("T13", "活动开启中重登不再弹(仅一次)", no_pop2, "")
    # T14 活动结束界面自动关闭: showUI 强开 → gm_close → 自动消失
    shown = qa(page, "() => window.__SHOW('UIYxActLimitTimeGift', 0)")
    page.wait_for_timeout(1200)
    if qa(page, "() => window.__qa.uiActive('UIYxActLimitTimeGift')"):
        rclose = gm_yxact.gm_close(SVR_ID, ACT)
        gone = not active_ui(page, "UIYxActLimitTimeGift", timeout_s=0) and inactive_ui(page, "UIYxActLimitTimeGift", settle_s=10)
        shot(page, "T14_after_act_close")
        rec("T14", "活动结束: 已打开的富甲界面自动关闭", gone, f"gm_close={rclose.get('body', rclose)}")
    else:
        rec("T14", "活动结束: 已打开的富甲界面自动关闭", None, f"showUI强开失败({shown})，结束不弹已由T11覆盖")
    # R0 还原活动原状
    if orig_open:
        rr = gm_yxact.gm_reopen(SVR_ID, ACT)
    else:
        rr = gm_yxact.gm_close(SVR_ID, ACT)
    rec("R0", "还原30001活动原状(共享环境纪律)", True, f"原状={orig_open} 还原={rr}")


def main():
    global UUID
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"[env] GAME_URL={base.GAME_URL} HEADLESS={base.HEADLESS} OUT={OUT}", flush=True)
    acc = gm_account.create_new_account(SVR_ID, SVR_NAME)
    account = (acc or {}).get("account") or (acc or {}).get("report", {}).get("account")
    if not account:
        raise RuntimeError(f"建号失败: {acc}")
    R["account"] = str(account)
    save()
    print(f"[account] 新号={account}", flush=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=base.HEADLESS)
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        login_flow(page, R["account"], first=True)
        uuid = qa(page, "() => { const g = window.__G(); return g ? g.playerUuid : null; }")
        UUID = str(uuid) if uuid else None
        R["uuid"] = UUID
        save()
        print(f"[uuid] {UUID}", flush=True)
        p0_probe(page)
        t1_cold_start(page)
        b_group(page)
        c_group(page)
        d_group(page)
        page.wait_for_timeout(1000)
        browser.close()
    R["end"] = datetime.now().isoformat(timespec="seconds")
    save()
    npass = sum(1 for c in R["cases"] if c["passed"] is True)
    nfail = sum(1 for c in R["cases"] if c["passed"] is False)
    nna = sum(1 for c in R["cases"] if c["passed"] is None)
    print(f"[done] PASS={npass} FAIL={nfail} NA={nna} → {OUT}", flush=True)


if __name__ == "__main__":
    main()
