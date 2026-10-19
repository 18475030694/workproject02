# -*- coding: utf-8 -*-
"""cfg_sys_jump 跳转id 29/43/46/181/182「跳转后无法关闭」修复验收 E2E。

背景（已核实）:
  - 5个界面均为 UIComIntegrationTabView 内嵌页签，自身关闭按钮仅 emit
    MSG_ON_INTEGRATION_TABVIEW_CLOSE 由父容器 uiHide；获取途径直开页签无父容器 → 关不掉。
  - 修复 r10605/10606 = 从 cfg_item_source 移除「每日特惠→29 / 七天签到→43」跳转。

Part A（真实路径）: 背包→道具→tips获取途径
  A1 点击「每日特惠」→ 预期不跳转（修复生效）
  A2 点击「七天签到」→ 预期不跳转（修复生效）
  A3 回归: 点击「挂机奖励」(goWin=10→UIGuaJi) → 正常跳转且目标界面可关闭
Part B（留证）: 模拟旧跳转路径 getUI(ui_name).showUI() 直开5个界面 →
  实测关闭行为（找 Close/BtnBg 节点点击 → 观察是否隐藏）

产物: temp_case/reports/e2e_jump_close_<ts>/{data.json, report.md, screenshots/}
"""
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # E:\workproject
sys.path.insert(0, str(ROOT / "harness"))
import e2e_login as base  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

ACCOUNT = os.environ.get("QA_ACCOUNT", "4451")
GAME_URL = os.environ.get("GAME_URL", "http://localhost:7456").rstrip("/")
SVR_ID = int(os.environ.get("SVR_ID", "5"))
SVR_NAME = os.environ.get("SVR_NAME", "S5")
GM_BASE = os.environ.get("GM_BASE", "http://192.168.*.*:6011/index")
HEADLESS = os.environ.get("HEADED", "0") != "1"

TARGETS = [
    (29, "UIRechargeDailyGift", "每日特惠"),
    (43, "UISevenDaySign", "七天签到"),
    (46, "UISevenDailyTaskMain", "精彩活动"),
    (181, "UIZeroPricePurchase", "零元购"),
    (182, "UIMicroPayment", "6元狂欢"),
]
# cfg_item_source 中原本指向29/43的条目（修复后 goWin 应为 null）
FIXED_ENTRIES = [(5, 4, "每日特惠"), (1000, 4, "每日特惠"), (1006, 5, "每日特惠"),
                 (1007, 4, "每日特惠"), (30005, 2, "七天签到")]
# 每日特惠入口可用的道具（背包里找其一即可）
ITEMS_WITH_DAILY = [(5, "灵力"), (1000, "凡灵召符"), (1006, "武器零件"), (1007, "炼宝玉佩")]
ITEM_QIANDAO = (30005, "战车突击")

JS_HEAD = """
window.__G = () => { for (const [k, v] of System.entries()) { if (v && v.Global && v.Global.uiMgr) return v.Global; } return null; };
window.__SHARE = () => { for (const [k, v] of System.entries()) { if (v && v.ShareRes && v.ShareRes.cfg_sys_jump) return v.ShareRes; } return null; };
window.__SM = () => { try { return SystemModules; } catch (e) { return null; } };
window.__SHOWUI = (name, arg) => { try { const g = window.__G(); g.uiMgr.getUI(name).showUI(arg); return true; } catch (e) { return 'ERR:' + e; } };
window.__HIDE = (name) => { try { const g = window.__G(); const u = g.uiMgr.getUI(name); if (u) u.uiHide(); return true; } catch (e) { return 'ERR:' + e; } };
window.__ITEM = (id) => { try { return SystemModules.knapsackMgr.getItemCount(id); } catch (e) { return -1; } };
/* 获取途径条目点击：在 UIItemTips 下按文本找条目, 从文本节点向上找 Toggle/Button 直调(不依赖节点名) */
window.__CLICK_SOURCE = (title) => {
  try {
    const g = window.__G();
    const tips = g.uiMgr.getUI('UIItemTips');
    const root = tips && tips.uiObject ? tips.uiObject : null;
    if (!root) return { ok: false, err: 'no UIItemTips root' };
    let hit = null;
    const walk = (n) => { if (hit) return;
      const l = n.getComponent('cc.Label'); const r = n.getComponent('cc.RichText');
      const t = l ? l.string : (r ? r.string : null);
      if (t && String(t).includes(title) && n.activeInHierarchy) { hit = n; return; }
      for (const c of n.children) walk(c); };
    walk(root);
    if (!hit) return { ok: false, err: 'no label: ' + title };
    let n = hit;
    for (let i = 0; i < 5 && n; i++) {
      const tg = n.getComponent('cc.Toggle');
      if (tg) { tg.isChecked = true; tg.emit('toggle', tg); return { ok: true, mode: 'toggle', node: n.name }; }
      const btn = n.getComponent('cc.Button');
      if (btn) { n.emit('click', btn); return { ok: true, mode: 'button', node: n.name }; }
      n = n.parent;
    }
    return { ok: false, err: 'no toggle/button above label' };
  } catch (e) { return { ok: false, err: String(e) }; }
};
/* 按文本找祖先节点(ancName)，有 Toggle 走 toggle，有 Button 走 click */
window.__CLICK_BY_LABEL = (text, ancName) => {
  const qa = window.__qa;
  for (const p of qa.findByName(ancName)) {
    const node = qa.resolvePath(p);
    if (!node || !node.activeInHierarchy) continue;
    let has = false;
    const walk = (n) => { if (has) return;
      const l = n.getComponent('cc.Label'); const r = n.getComponent('cc.RichText');
      const t = l ? l.string : (r ? r.string : null);
      if (t && String(t).includes(text) && n.activeInHierarchy) { has = true; return; }
      for (const c of n.children) walk(c); };
    walk(node);
    if (!has) continue;
    const tg = node.getComponent('cc.Toggle');
    if (tg) { tg.isChecked = true; tg.emit('toggle', tg); return { ok: true, mode: 'toggle', path: p }; }
    const btn = node.getComponent('cc.Button');
    if (btn) { node.emit('click', btn); return { ok: true, mode: 'button', path: p }; }
    return { ok: false, err: 'no comp on ' + p };
  }
  return { ok: false, err: 'not found: ' + text + ' @ ' + ancName };
};
"""

RESULT = {"title": "cfg_sys_jump 29/43/46/181/182 跳转关闭修复验收",
          "account": ACCOUNT, "server": SVR_NAME,
          "start_time": datetime.now().isoformat(timespec="seconds"),
          "prep": {}, "cases": []}
OUT_DIR = None
DATA_JSON = None


def save():
    if DATA_JSON:
        DATA_JSON.write_text(json.dumps(RESULT, ensure_ascii=False, indent=1), encoding="utf-8")


def rec(cid, title, ok, note="", shot_name=None, detail=None):
    entry = {"case_id": cid, "title": title, "passed": ok, "note": note,
             "time": datetime.now().isoformat(timespec="seconds")}
    if shot_name:
        entry["screenshot"] = f"screenshots/{shot_name}.png"
    if detail is not None:
        entry["detail"] = detail
    RESULT["cases"].append(entry)
    save()
    tag = "PASS" if ok is True else ("FAIL" if ok is False else "FACT")
    print(f"  [{tag}] {cid} {title} | {note}"[:240])
    return entry


def qa(page, expr, default=None):
    try:
        return page.evaluate(expr)
    except Exception:
        return default


def texts(page, kw=""):
    return qa(page, f"() => {{ try {{ return window.__qa.dumpUITree('{kw}'); }} catch(e) {{ return []; }} }}", []) or []


def ui_active(page, name):
    return qa(page, f"() => window.__qa.uiActive('{name}')", False)


def wait_ui(page, name, timeout_s=10):
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        if ui_active(page, name):
            return True
        page.wait_for_timeout(400)
    return False


def shot(page, name):
    try:
        return base.screenshot(page, OUT_DIR, name)
    except Exception:
        return None


def click_node(page, path):
    return qa(page, f"() => window.__qa.clickNode({json.dumps(path)})", False)


def click_by_label(page, text, anc):
    return qa(page, f"() => window.__CLICK_BY_LABEL({json.dumps(text)}, {json.dumps(anc)})", {"ok": False, "err": "eval err"})


def click_ancestor_of_label(page, text, anc):
    return qa(page, f"() => window.__qa.clickAncestorOfLabel({json.dumps(text)}, {json.dumps(anc)})", False)


def gm(uuid, path):
    import urllib.request
    url = f"{GM_BASE}/{path}"
    try:
        return urllib.request.urlopen(url, timeout=20).read(300).decode("utf-8", "ignore")
    except Exception as e:
        return f"ERR {e}"


def hide_all(page):
    for name in ["UIItemTips", "UIBag", "UIGuaJi"] + [u for _, u, _ in TARGETS]:
        qa(page, f"() => window.__HIDE('{name}')")
    page.wait_for_timeout(500)


def close_candidates(page, ui_name):
    """在指定 UI 下找名字含 close/btnbg 的节点（去重，取激活路径）"""
    out, seen = [], set()
    for e in texts(page, ui_name):
        nm = str(e.get("name") or "")
        if not re.search(r"close|btnbg", nm, re.I):
            continue
        p = str(e.get("path") or "")
        if not e.get("active") or p in seen:
            continue
        seen.add(p)
        out.append({"name": nm, "path": p})
    return out


def try_real_close(page, ui_name, shot_prefix):
    """点击 UI 内所有关闭候选节点，返回 (closed, tried)"""
    tried = []
    for c in close_candidates(page, ui_name):
        click_node(page, c["path"])
        page.wait_for_timeout(800)
        still = ui_active(page, ui_name)
        tried.append({"node": c["name"], "path": c["path"], "closed_after": not still})
        if not still:
            shot(page, f"{shot_prefix}_after_close_{c['name']}")
            return True, tried
    return False, tried


def find_bag_item_text(page, names):
    """在背包可见单元格(ItemName_ 标签)中找目标道具名，只认激活节点"""
    for e in texts(page, "UIBag"):
        if str(e.get("name")) != "ItemName_" or not e.get("active"):
            continue
        t = str(e.get("text") or "")
        if t in names:
            return t
    return ""


def scroll_bag_collect(page, names):
    """背包列表虚拟化：滚动过程中采样渲染出的单元格文本"""
    sv_path = ""
    for e in texts(page, "ScrollNormal_"):
        if e.get("name") == "ScrollNormal_" and e.get("active"):
            sv_path = str(e.get("path"))
            break
    if not sv_path:
        return ""
    for dur, samples in ((2.5, 8), (1.5, 6)):
        qa(page, f"() => window.__qa.compCall({json.dumps(sv_path)}, 'cc.ScrollView', 'scrollToBottom', {dur})")
        for _ in range(samples):
            page.wait_for_timeout(int(dur * 1000 / samples))
            hit = find_bag_item_text(page, names)
            if hit:
                return hit
        qa(page, f"() => window.__qa.compCall({json.dumps(sv_path)}, 'cc.ScrollView', 'scrollToTop', 1.0)")
        for _ in range(4):
            page.wait_for_timeout(250)
            hit = find_bag_item_text(page, names)
            if hit:
                return hit
    return ""


def open_bag_and_find_item(page, item_names):
    """打开背包，翻页签+滚动找目标道具单元格并点击弹tips。返回道具名或None"""
    if not ui_active(page, "UIBag"):
        qa(page, "() => window.__SHOWUI('UIBag')")
        wait_ui(page, "UIBag", 8)
    page.wait_for_timeout(800)

    hit = find_bag_item_text(page, item_names)
    for round_i in range(6):  # 翻页签兜底
        if hit:
            break
        r = qa(page, """() => {
          try {
            const qa = window.__qa; const togList = qa.findByName('TogItem');
            const items = [];
            for (const p of togList) { if (!p.includes('UIBag')) continue;
              const n = qa.resolvePath(p); if (!n || !n.activeInHierarchy) continue;
              const tg = n.getComponent('cc.Toggle'); if (tg) items.push({ p, tg });
            }
            for (const it of items) { if (!it.tg.isChecked) { it.tg.isChecked = true; it.tg.emit('toggle', it.tg); return { ok: true, path: it.p }; } }
            return { ok: false, err: 'all checked' };
          } catch (e) { return { ok: false, err: String(e) }; }
        }""")
        page.wait_for_timeout(900)
        if not (r or {}).get("ok"):
            break
        hit = find_bag_item_text(page, item_names)
    if not hit:
        hit = scroll_bag_collect(page, item_names)
    if not hit:
        return None

    # 点击道具单元格（Toggle 在 UIItemWithName_ 节点上）
    r = click_by_label(page, hit, "UIItemWithName_")
    if not (isinstance(r, dict) and r.get("ok")):
        if not click_ancestor_of_label(page, hit, "UIItemWithName_"):
            return None
    if not wait_ui(page, "UIItemTips", 8):
        return None
    page.wait_for_timeout(1000)  # 获取途径按钮 0.5s 后才可点
    return hit


def open_tips_direct(page, item_id):
    """兜底：与 ItemHelper 默认分支完全等价的直调（showSource=true, fromBag=true）"""
    r = qa(page, f"() => {{ try {{ const g = window.__G(); "
                 f"g.uiMgr.getUI('UIItemTips').showUI({item_id}, null, true, true); return true; }} "
                 f"catch(e) {{ return 'ERR:' + e; }} }}")
    wait_ui(page, "UIItemTips", 6)
    page.wait_for_timeout(1000)
    return ui_active(page, "UIItemTips")


def source_entries_of_tips(page):
    return [str(e.get("text") or "") for e in texts(page, "SourceItemTxt") if e.get("active") and e.get("text")]


def click_source_entry(page, title):
    """自适应: 按文本找条目→向上找 Toggle/Button 直调; 失败回退 QABridge 旧写法"""
    r = qa(page, f"() => window.__CLICK_SOURCE({json.dumps(title)})", {"ok": False, "err": "eval err"})
    if (r or {}).get("ok"):
        return r
    ok = click_ancestor_of_label(page, title, "SourceItem")
    return {"ok": bool(ok), "mode": "legacy"} if ok else r


# ---------------------------------------------------------------- 用例
def prep(page):
    p = RESULT["prep"]
    uid = qa(page, "() => window.__G().playerUuid")
    p["uuid"] = uid

    # 1) 配置生效证据（运行时 ShareRes）
    cfg = qa(page, """() => {
      const S = window.__SHARE(); if (!S) return { err: 'no ShareRes' };
      const fixed = %s;
      const out = { fixed: [], jumps: {}, item5_sources: [] };
      for (const [iid, idx, title] of fixed) {
        const grp = S.cfg_item_source[String(iid)];
        const e = grp && grp[String(idx)];
        out.fixed.push({ itemId: iid, idx, title, goWin: e ? e.goWin : 'NO_ENTRY' });
      }
      for (const id of ['29','43','46','181','182']) {
        const j = S.cfg_sys_jump[id];
        out.jumps[id] = j ? j.ui_name : null;
      }
      const s5 = S.cfg_item_source['5'];
      for (const k in (s5 || {})) out.item5_sources.push({ title: s5[k].title, goWin: s5[k].goWin });
      return out;
    }""" % json.dumps([[i, x, t] for i, x, t in FIXED_ENTRIES]))
    p["runtime_cfg"] = cfg
    ok_cfg = bool(cfg) and "err" not in cfg and \
        all(e.get("goWin") in (None, 0) for e in cfg.get("fixed", [])) and \
        all(cfg.get("jumps", {}).get(i) for i in ("29", "43", "46", "181", "182"))
    rec("P0", "运行时配置确认(修复已在测试客户端生效)", ok_cfg,
        f"fixed goWin全空={all(e.get('goWin') in (None, 0) for e in (cfg or {}).get('fixed', []))}; "
        f"jumps={cfg.get('jumps') if cfg else None}",
        detail=cfg)

    # 2) 道具准备（战车突击用于A2）
    cnt5, cnt30005 = qa(page, "() => window.__ITEM(5)"), qa(page, "() => window.__ITEM(30005)")
    if not cnt30005:
        r = gm(uid, "award_item?uuid=%d&item_id=30005&count=1" % uid)
        p["award_30005"] = r[:80]
        page.wait_for_timeout(2500)
        cnt30005 = qa(page, "() => window.__ITEM(30005)")
    p["items"] = {"5": cnt5, "30005": cnt30005}
    print(f"  items: 灵力={cnt5} 战车突击={cnt30005}")
    return ok_cfg


def part_a(page):
    hide_all(page)

    # ---- A1 每日特惠入口 ----
    item = open_bag_and_find_item(page, [n for _, n in ITEMS_WITH_DAILY])
    shot(page, "A1_tips_open")
    if not item or not ui_active(page, "UIItemTips"):
        # 兜底: 等价直调弹tips（showSource=true, fromBag=true）
        for iid, iname in ITEMS_WITH_DAILY:
            if open_tips_direct(page, iid):
                item = f"兜底直调(item={iid} {iname})"
                break
    if not item or not ui_active(page, "UIItemTips"):
        rec("A1", "获取途径点「每日特惠」不再跳转", False,
            f"未能打开含每日特惠的道具tips(找到道具={item}, 含兜底直调)")
    else:
        entries = source_entries_of_tips(page)
        has_daily = any("每日特惠" in t for t in entries)
        if not has_daily:
            rec("A1", "获取途径点「每日特惠」不再跳转", False,
                f"tips[{item}]获取途径无「每日特惠」条目: {entries}")
        else:
            # 点击前目标UI必须未开
            pre_ok = not ui_active(page, "UIRechargeDailyGift")
            click_source_entry(page, "每日特惠")
            page.wait_for_timeout(1500)
            jumped = ui_active(page, "UIRechargeDailyGift")
            tips_alive = ui_active(page, "UIItemTips")
            shot(page, "A1_after_click_daily")
            rec("A1", "获取途径点「每日特惠」不再跳转(修复生效)",
                bool(pre_ok and not jumped),
                f"道具={item} 点击后UIRechargeDailyGift激活={jumped}(预期False), tips仍在={tips_alive}, 条目={entries}",
                detail={"entries": entries, "jumped": jumped, "tips_alive": tips_alive})
            if jumped:
                qa(page, "() => window.__HIDE('UIRechargeDailyGift')")
        hide_all(page)

    # ---- A2 七天签到入口 ----
    item2 = open_bag_and_find_item(page, [ITEM_QIANDAO[1]])
    if not (item2 and ui_active(page, "UIItemTips")) and qa(page, "() => window.__ITEM(30005)"):
        # 兜底: 等价直调弹tips（showSource=true, fromBag=true）
        if open_tips_direct(page, ITEM_QIANDAO[0]):
            item2 = f"兜底直调(item={ITEM_QIANDAO[0]} {ITEM_QIANDAO[1]})"
    if not item2 or not ui_active(page, "UIItemTips"):
        rec("A2", "获取途径点「七天签到」不再跳转", False, "未能打开战车突击tips(含兜底直调)")
    else:
        entries = source_entries_of_tips(page)
        if not any("七天签到" in t for t in entries):
            rec("A2", "获取途径点「七天签到」不再跳转", False, f"tips获取途径无「七天签到」: {entries}")
        else:
            click_source_entry(page, "七天签到")
            page.wait_for_timeout(1500)
            jumped = ui_active(page, "UISevenDaySign")
            tips_alive = ui_active(page, "UIItemTips")
            shot(page, "A2_after_click_qiandao")
            rec("A2", "获取途径点「七天签到」不再跳转(修复生效)", not jumped,
                f"点击后UISevenDaySign激活={jumped}(预期False), tips仍在={tips_alive}, 条目={entries}",
                detail={"entries": entries, "jumped": jumped})
            if jumped:
                qa(page, "() => window.__HIDE('UISevenDaySign')")
        hide_all(page)

    # ---- A3 回归: 挂机奖励跳转 + 目标界面可关闭（灵力[5] 获取途径 idx3=挂机奖励 goWin=10→UIGuaJi）----
    item3 = open_bag_and_find_item(page, ["灵力"])
    if not (item3 and ui_active(page, "UIItemTips")):
        # 兜底: 等价直调弹tips（showSource=true, fromBag=true）
        if open_tips_direct(page, 5):
            item3 = "兜底直调(item=5 灵力)"
    if not item3 or not ui_active(page, "UIItemTips"):
        rec("A3", "回归: 其他获取途径跳转正常且可关闭", False, "未能打开灵力tips(含兜底直调)")
    else:
        entries = source_entries_of_tips(page)
        if not any("挂机奖励" in t for t in entries):
            rec("A3", "回归: 其他获取途径跳转正常且可关闭", False, f"tips无「挂机奖励」条目: {entries}")
        else:
            click_source_entry(page, "挂机奖励")
            page.wait_for_timeout(1800)
            opened = wait_ui(page, "UIGuaJi", 8)
            shot(page, "A3_guaji_open")
            if not opened:
                rec("A3", "回归: 其他获取途径跳转正常且可关闭", False,
                    f"点击挂机奖励后UIGuaJi未打开, tips仍在={ui_active(page, 'UIItemTips')}, 条目={entries}")
            else:
                closed, tried = try_real_close(page, "UIGuaJi", "A3_guaji")
                if not closed:
                    qa(page, "() => window.__HIDE('UIGuaJi')")
                rec("A3", "回归: 其他获取途径跳转正常且可关闭", bool(opened and closed),
                    f"UIGuaJi打开={opened}, 点关闭按钮后关闭={closed}, 关闭节点={[t['node'] for t in tried]}",
                    detail=tried)
        hide_all(page)


def part_b(page):
    hide_all(page)
    for jid, ui_name, cn in TARGETS:
        r = qa(page, f"() => window.__SHOWUI('{ui_name}')")
        page.wait_for_timeout(1500)
        opened = wait_ui(page, ui_name, 6)
        shot(page, f"B{jid}_open")
        err = isinstance(r, str) and r.startswith("ERR")
        if not opened or err:
            rec(f"B{jid}", f"直开{cn}({ui_name}) 关闭行为留证", None,
                f"showUI返回={r}, 激活={opened}（可能需系统开启/配置依赖，无法留证）")
            qa(page, f"() => window.__HIDE('{ui_name}')")
            page.wait_for_timeout(400)
            continue
        cands = close_candidates(page, ui_name)
        closed, tried = try_real_close(page, ui_name, f"B{jid}")
        still = ui_active(page, ui_name)
        shot(page, f"B{jid}_after_close")
        qa(page, f"() => window.__HIDE('{ui_name}')")
        page.wait_for_timeout(400)
        rec(f"B{jid}", f"直开{cn}({ui_name}) 关闭行为留证", None,
            f"打开=是; 关闭候选={[c['name'] for c in cands]}; 点击后关闭={closed}; 仍激活={still} → "
            + ("直开场景可关闭" if closed else "直开场景无法关闭(页签设计依赖父容器, 修复方案=移除入口)"),
            detail={"jump_id": jid, "candidates": cands, "tried": tried, "still_active": still})


def run():
    global OUT_DIR, DATA_JSON
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    OUT_DIR = ROOT / "temp_case" / "reports" / f"e2e_jump_close_{ts}"
    (OUT_DIR / "screenshots").mkdir(parents=True, exist_ok=True)
    DATA_JSON = OUT_DIR / "data.json"
    RESULT["out_dir"] = str(OUT_DIR)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()
        try:
            page.goto(f"{GAME_URL}/?qa=1", wait_until="domcontentloaded", timeout=60_000)
            base.wait_qa_bridge(page)
            page.wait_for_timeout(5000)
            page.evaluate(f"() => {{ try {{ localStorage.setItem('TMP_ACCOUNT_', '{ACCOUNT}'); }} catch(e) {{}} }}")
            base.force_select_server(page, SVR_ID, SVR_NAME)
            page.reload(wait_until="domcontentloaded", timeout=60_000)
            base.wait_qa_bridge(page)
            page.wait_for_timeout(3000)
            page.wait_for_function("() => window.__qa.findByName('LoginBtn_').length > 0", timeout=90_000)
            page.evaluate("() => window.__qa.findByName('LoginBtn_').forEach(n => window.__qa.clickNode(n))")

            dead = {"网络波动", "连接中断", "登录失败", "服务器未开启", "维护中", "无法连接"}
            t0 = time.time()
            ok = False
            while time.time() - t0 < 150:
                if qa(page, "() => window.__qa && window.__qa.isReady()") and \
                        not qa(page, "() => window.__qa.uiActive('UILoading')"):
                    ok = True
                    break
                joined = " ".join(str(e.get("text")) for e in texts(page) if e.get("text"))
                if any(k in joined for k in dead):
                    break
                page.wait_for_timeout(2000)
            assert ok, "登录失败"
            page.wait_for_timeout(3000)
            page.evaluate(JS_HEAD)
            shot(page, "00_main_city")

            if prep(page):
                part_a(page)
                part_b(page)
            else:
                rec("P0", "配置确认失败，中止", False, "运行时配置与修复预期不符")
        finally:
            hide_all(page)
            RESULT["end_time"] = datetime.now().isoformat(timespec="seconds")
            save()
            browser.close()

    cases = RESULT["cases"]
    npass = sum(1 for c in cases if c["passed"] is True)
    nfail = sum(1 for c in cases if c["passed"] is False)
    nfact = sum(1 for c in cases if c["passed"] is None)
    print(f"\n==== 结果: PASS {npass} / FAIL {nfail} / FACT {nfact} ====")
    for c in cases:
        tag = "PASS" if c["passed"] is True else ("FAIL" if c["passed"] is False else "FACT")
        print(f"  {c['case_id']:6s} {tag}  {c['note'][:130]}")
    return RESULT


if __name__ == "__main__":
    run()
