"""挂机奖励 30% 翻倍概率专项探针 v2（广告通道 + 多账号并行；实现方法改造 前后对照通用）
用法:
  python probe_guaji_rate.py --prep --accounts 4501,4502,4503      # 造新号+一键高级号+推主线19400（一次性）
  python probe_guaji_rate.py --tag baseline --accounts 4501,4502,4503   # 采样: 每号3次广告
  python probe_guaji_rate.py --tag after    --accounts 4501,4502,4503   # 改造后对照
  python probe_guaji_rate.py --opencard --tag opencard --accounts 4501,4502,4503  # 激活离线闯关特权卡(card_id=7)
  python probe_guaji_rate.py --compare reports/.../data.json reports/.../data.json

v2 依据（v1 冒烟结论）:
  - 本环境(product) set_timeshift 对 Date.Second() 无效(date.lua L31-48 IsProductEnv 分支) → 弃时间加速
  - 加速器: c2gs_advert_finish(ad_type=1) → mod_advert C2gsAdvertFinish(无真实广告校验, cd=1s, 每日3次)
            → guaji OnAdvertCallback → CalcReward(7200s) = tier1 1440掷 + tier2 24掷 即时进背包
  - 档位: GM set_mainline_stage 推主线 19400 → cfg_guaji_reward[103] tier1 全必中
          reward1={{2,10605,10000},{2,2,10000},{3,1,10000},{3,3,10000},{5,1,10000},{5,2,10000}}
  - 统计: 广告产出入背包(不走领取响应) → 背包快照diff。主判据 item3/item5(量小无溢出风险),
          item2 量级 2000万/次 仅参考。主城挂机战斗掉落同窗口污染比例 <0.1% 记为已知干扰。
  - 特权快照: privilegeMgr.getPrivilegeVal(10/22) + 离线卡(7)。4451 实测读数 0 → 翻倍期望 p 以读数为准。
样本预算: 3号 × 3次 × 1440 = 12960 tier1 掷 → 必中项 p̂ 3σ ≈ ±1.2pp
产物: reports/probe_guaji_rate_<ts>/data.json + temp_case/reports/probe_guaji_翻倍概率_<tag>.md
静态依据: mod_guaji_reward.lua L248-271 双段掷点; cfg_advert[1] count=3 cd=1; advertc2s.lua L21;
         defines.lua ADVERT_TYPE.GUAJI_REWARD=1, PRIVILEGE_FUNC.GUAJI_MUL=10/GUAJI_MUL2=22
"""
import argparse
import json
import math
import re
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, r"E:\workproject\harness")
import e2e_login as base  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

ROOT = Path("E:/workproject")
GAME_URL = "http://localhost:7456"
SVR_ID, SVR_NAME = 5, "S5"
GM_BASE = "http://192.168.*.*:6011/index"
DEFAULT_ACCOUNTS = "4501,4502,4503"
CFG_LUA = Path("E:/p1-x/trunk/server/src/res/Config/guaji/cfg_guaji_reward.lua")

PRIV_GUAJI_MUL, PRIV_GUAJI_MUL2 = 10, 22
CARD_OFFLINE_MAINLINE = 7
P_REQUIRE = 0.30          # 需求口径 30%（期望以运行时特权读数为准, 此为兜底）
MAINLINE_STAGE = 19400    # 推主线目标 → 档位[103] tier1 全必中
AD_TYPE_GUAJI = 1
AD_COUNT = 3              # cfg_advert[1].count 每日3次
AD_CALC_SEC = 7200        # cfg_guaji_global.ad_reward_sec
STAT_ITEMS = [2, 3, 5, 1001, 1002, 1003]

JS_HEAD = """
window.__NET = () => { for (const [k, v] of System.entries()) { if (v && v.Network && v.Network.call) return v.Network; } return null; };
window.__NETC = (payload) => new Promise((resolve) => { try { const net = window.__NET(); if (!net) return resolve({ ok: false, resp: { err: 'no Network' } });
  net.call(payload.proto, payload.args || {}, (ok, resp) => resolve({ ok, resp })); setTimeout(() => resolve({ ok: false, resp: { timeout: true } }), 15000); } catch(e) { resolve({ ok: false, resp: { err: String(e) } }); } });
window.__PRIV = () => { try {
  const pm = SystemModules.privilegeMgr; if (!pm) return { err: 'no privilegeMgr' };
  const out = {};
  try { out.mul = pm.getPrivilegeVal(10); } catch(e) { out.mul = null; }
  try { out.mul2 = pm.getPrivilegeVal(22); } catch(e) { out.mul2 = null; }
  try { out.card_valid = !!pm.getPrivilegeCardStatus(7); } catch(e) { out.card_valid = null; }
  return out;
} catch(e) { return { err: String(e) } } };
window.__ITEMS = (ids) => { try { return ids.map(id => { try { return SystemModules.knapsackMgr.getItemCount(id); } catch(e) { return -1; } }); } catch(e) { return null; } };
window.__UUID = () => { try { return (window.__GAME__ && window.__GAME__.playerUuid) || null; } catch(e) { return null; } };
window.__GUAJI_LAST = () => { try { return SystemModules.guaJiMgr.lastReceiveTime; } catch(e) { return -1; } };
window.__SYSOPEN = (id) => { try { return SystemModules.sysOpenMgr.isSysOpen(id); } catch(e) { return null; } };
window.__CFGROW = () => { try { const pid = arguments; return null; } catch(e) { return null; } };
"""

RESULT = {
    "title": "挂机奖励30%翻倍概率专项探针v2(广告通道)",
    "static_evidence": (
        "mod_guaji_reward.lua L248-271: 每掷点每条目 r=math.random(0,10000) vs 权重掉落 → 命中后 r2 vs nDoubleWeight 翻倍(*2); "
        "nDoubleWeight=GetPrivilege(GUAJI_MUL=10)(tier1)/GUAJI_MUL2(=22)(tier2); 无离线卡时溢出部分进 privilege_reward_map; "
        "广告: c2gs_advert_finish(ad_type=1) → OnAdvertCallback → CalcReward(7200s) 直接 RewardList 进背包; "
        "档位[103](主线19400) tier1 全必中 w=10000"
    ),
}
OUT_DIR = None
DATA_JSON = None
TAG = "baseline"


def save():
    if DATA_JSON:
        DATA_JSON.write_text(json.dumps(RESULT, ensure_ascii=False, indent=1), encoding="utf-8")


def rec(key, ok, note, detail=None):
    entry = {"key": key, "passed": ok, "note": note, "time": datetime.now().isoformat(timespec="seconds")}
    if detail is not None:
        entry["detail"] = detail
    RESULT.setdefault("checks", []).append(entry)
    save()
    tag = "PASS" if ok is True else ("FAIL" if ok is False else "INFO")
    print(f"  [{tag}] {key} | {note}"[:240], flush=True)
    return entry


def qa(page, expr, default=None):
    try:
        return page.evaluate(expr)
    except Exception:
        return default


def gm_get(url_path):
    url = f"{GM_BASE}/{url_path}"
    try:
        return urllib.request.urlopen(url, timeout=20).read(300).decode("utf-8", "ignore")
    except Exception as e:
        return f"ERR {e}"


def wait_main_city(page, timeout_s=180):
    dead = {"网络波动", "连接中断", "连接失败", "登录失败", "服务器未开启", "维护中", "无法连接"}
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        if qa(page, "() => window.__qa && window.__qa.isReady()"):
            if not qa(page, "() => window.__qa.uiActive('UILoading')"):
                return True
        for k in dead:
            if qa(page, f"() => window.__qa.uiActive('{k}')"):
                return False
        page.wait_for_timeout(2000)
    return False


def wait_login_ready(page, timeout_s=240):
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        n = qa(page, "() => { try { return window.__qa.findByName('LoginBtn_').length; } catch(e) { return 0; } }", 0)
        if n:
            return True
        qa(page, "() => { try { window.__qa.findByName('ConformBtn_').forEach(p => window.__qa.clickNode(p)); } catch(e) {} }")
        page.wait_for_timeout(2500)
    return False


def login_flow(page, account):
    page.goto(f"{GAME_URL}/?qa=1", wait_until="domcontentloaded", timeout=90_000)
    base.wait_qa_bridge(page)
    page.wait_for_timeout(4000)
    page.evaluate(f"() => {{ try {{ localStorage.setItem('TMP_ACCOUNT_', '{account}'); }} catch(e) {{}} }}")
    base.force_select_server(page, SVR_ID, SVR_NAME)
    page.reload(wait_until="domcontentloaded", timeout=90_000)
    base.wait_qa_bridge(page)
    page.wait_for_timeout(3000)
    assert wait_login_ready(page), "登录按钮未出现(加载超时)"
    page.evaluate("() => window.__qa.findByName('LoginBtn_').forEach(n => window.__qa.clickNode(n))")
    assert wait_main_city(page), "登录失败"
    page.wait_for_timeout(3000)
    page.evaluate(JS_HEAD)


def prep_account(page, account):
    """新号准备: 登录 → 读uuid → GM推主线19400 → 重登 → 快照(特权/系统开放/档位)."""
    login_flow(page, account)
    uuid = qa(page, "() => window.__UUID()")
    assert uuid, f"{account} 未取到 playerUuid"
    r = gm_get(f"set_mainline_stage?uuid={uuid}&stage_id={MAINLINE_STAGE}")
    print(f"  set_mainline_stage → {r[:80]}", flush=True)
    if "ERR" not in r:
        time.sleep(2)
        login_flow(page, account)  # 重登触发 SceneReady/SYS_OPEN 重算
        uuid = qa(page, "() => window.__UUID()") or uuid
    last = qa(page, "() => window.__GUAJI_LAST()")
    sys_open = qa(page, "() => window.__SYSOPEN(10)")
    priv = qa(page, "() => window.__PRIV()")
    info = {"account": account, "uuid": uuid, "gm_resp": r[:100],
            "guaji_last_recv": last, "sys10_open": sys_open, "priv": priv,
            "time": datetime.now().isoformat(timespec="seconds")}
    rec("PREP", None, f"{account}: uuid={uuid} sys10={sys_open} last_recv={last} priv={priv} gm={r[:40]}", detail=info)
    return info


def opencard_account(page, account):
    """激活离线闯关特权卡(card_id=7): c2gs_buy_privilege_card 无扣费校验(支付在上层商店)。
    判定以特权快照为准(客户端getPrivilegeVal与服务端GetPrivilege同构): mul=3000 即生效;
    ALREADY_HAD_PRIVILEGE_CARD 视为已激活(读数仍应=3000)。"""
    login_flow(page, account)
    uuid = qa(page, "() => window.__UUID()")
    r = qa(page, "() => window.__NETC({proto:'c2gs_buy_privilege_card', args:{card_id:7}})")
    page.wait_for_timeout(1500)
    priv = qa(page, "() => window.__PRIV()")
    err = ((r or {}).get("resp") or {}).get("errcode") if (r or {}).get("ok") else (r or {}).get("resp")
    ok = bool(isinstance(priv, dict) and priv.get("mul") == 3000 and priv.get("mul2") == 3000)
    info = {"account": account, "uuid": uuid, "buy": r, "priv": priv,
            "time": datetime.now().isoformat(timespec="seconds")}
    RESULT.setdefault("opencards", []).append(info)
    rec(f"OPENCARD_{account}", ok, f"buy_errcode={err} priv={priv}", detail=info)
    return ok


def sample_account(page, account, info):
    """单号采样: 3次广告, 每次背包快照diff。返回该号样本。"""
    samples = []
    item_ids = json.dumps(STAT_ITEMS)
    before = qa(page, f"() => window.__ITEMS({item_ids})")
    assert before and all(x >= 0 for x in before), f"{account} 背包读取失败: {before}"
    RESULT.setdefault("bag_start", {})[account] = dict(zip(map(str, STAT_ITEMS), before))

    for i in range(1, AD_COUNT + 1):
        snap0 = qa(page, f"() => window.__ITEMS({item_ids})")
        r = qa(page, "() => window.__NETC({proto:'c2gs_advert_finish', args:{ad_type:1, extra_param:{pos:0}}})")
        page.wait_for_timeout(1500)
        snap1 = qa(page, f"() => window.__ITEMS({item_ids})")
        ok = bool(r and r.get("ok"))
        err = ((r or {}).get("resp") or {}).get("errcode") if ok else (r or {}).get("resp")
        diff = {}
        if ok and snap0 and snap1:
            diff = {str(STAT_ITEMS[j]): snap1[j] - snap0[j] for j in range(len(STAT_ITEMS))}
        entry = {"account": account, "round": i, "ok": ok, "errcode": err, "bag_diff": diff,
                 "n1_expect": AD_CALC_SEC // 5, "n2_expect": AD_CALC_SEC // 300,
                 "time": datetime.now().isoformat(timespec="seconds")}
        samples.append(entry)
        RESULT.setdefault("samples", []).append(entry)
        rec(f"AD_{account}_R{i}", ok, f"errcode={err} diff={diff}", detail=entry)
        save()
        if i < AD_COUNT:
            time.sleep(2)  # cd=1s 余量
    after = qa(page, f"() => window.__ITEMS({item_ids})")
    RESULT.setdefault("bag_end", {})[account] = dict(zip(map(str, STAT_ITEMS), after)) if after else {}
    return samples


def parse_cfg_lua(path=CFG_LUA):
    """解析服务端 cfg_guaji_reward.lua → {id: {mainline_pass_id, interval1, reward1, interval2, reward2}}。
    只依赖静态文件(只读), 前后两轮档位若变, restat 也能正确拟合。"""
    text = path.read_text(encoding="utf-8")
    rows = {}
    for m in re.finditer(r"\[(\d+)\]\s*=\s*\{(.*?)\n\}", text, re.S):
        rid, body = int(m.group(1)), m.group(2)
        row = {"id": rid}
        mp = re.search(r"mainline_pass_id\s*=\s*(\d+)", body)
        row["mainline_pass_id"] = int(mp.group(1)) if mp else 0
        for tier in ("1", "2"):
            itv = re.search(rf"interval{tier}\s*=\s*(\d+)", body)
            row[f"interval{tier}"] = int(itv.group(1)) if itv else None
            rw = re.search(rf"reward{tier}\s*=\s*\{{(.*?)\}}\s*,?\s*\n", body + "\n", re.S)
            items = []
            if rw:
                for t in re.finditer(r"\{\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\}", rw.group(1)):
                    items.append([int(t.group(1)), int(t.group(2)), int(t.group(3))])
            row[f"reward{tier}"] = items
        rows[rid] = row
    return rows


def fit_cfg_row(rows, n1, agg, p):
    """按 tier1 产出拟合最优档位: 对每行 per-item |z| 均分取最小。agg: {id: count}"""
    best, best_score = None, float("inf")
    for rid, row in rows.items():
        rw = row.get("reward1") or []
        if not rw:
            continue
        em, vm = {}, {}
        for item_id, num, weight in rw:
            w = weight / 10000.0
            em[item_id] = em.get(item_id, 0) + n1 * w * num * (1 + p)
            vm[item_id] = vm.get(item_id, 0) + n1 * ((w * num * num * (1 + 3 * p)) - (w * num * (1 + p)) ** 2)
        score, used = 0.0, 0
        for iid, e in em.items():
            if vm.get(iid, 0) <= 0:
                continue
            obs = agg.get(int(iid), 0)
            score += abs((obs - e) / math.sqrt(vm[iid]))
            used += 1
        if used and score / used < best_score:
            best_score, best = score / used, rid
    return best, best_score


def stats_all():
    """汇总所有号样本: 先按产出拟合实际档位(硬编码[103]不可靠, GM推主线可能未生效),
    再用拟合档位权重做 z 检验。纯必中+p=0 时 var=0(确定性), 任何非零翻倍都会打破恒定值。"""
    samples = RESULT.get("samples", [])
    good = [s for s in samples if s.get("ok") and s.get("bag_diff")]
    if not good:
        rec("STATS", False, "无有效广告样本", detail=None)
        return
    n_success = len(good)
    n1 = n_success * (AD_CALC_SEC // 5)
    n2 = n_success * (AD_CALC_SEC // 300)
    sums = {str(i): 0 for i in STAT_ITEMS}
    for s in good:
        for k, v in s["bag_diff"].items():
            sums[k] = sums.get(k, 0) + v

    priv = RESULT.get("priv_ref") or {}
    p1 = priv.get("mul") / 10000.0 if isinstance(priv.get("mul"), (int, float)) else P_REQUIRE
    p2 = priv.get("mul2") / 10000.0 if isinstance(priv.get("mul2"), (int, float)) else P_REQUIRE

    rows = RESULT.get("cfg_rows") or parse_cfg_lua()
    assert rows, "cfg_guaji_reward 解析失败"
    fitted_id, fit_score = fit_cfg_row(rows, n1, {int(k): v for k, v in sums.items()}, p1)
    row = rows[fitted_id]
    RESULT["fitted_row_id"] = fitted_id
    RESULT["fitted_row"] = row
    rec("CFG_ROW_FITTED", None, f"产出拟合档位 id={fitted_id} (|z|均分={round(fit_score, 2)}), "
                                f"reward1={row.get('reward1')} interval1={row.get('interval1')}")
    save()

    def zcheck(reward_items, n_total, p, label):
        detail, all_ok = {}, True
        wm = sum(m * w / 10000.0 for _, m, w in reward_items)
        var = n_total * sum((w / 10000.0) * m * m * (1 + 3 * p) - ((w / 10000.0) * m * (1 + p)) ** 2
                            for _, m, w in reward_items)
        # 按 id 合并
        merged = {}
        for iid, m, w in reward_items:
            merged.setdefault(iid, []).append((m, w))
        for iid, entries in sorted(merged.items()):
            e = n_total * sum(m * w / 10000.0 for m, w in entries) * (1 + p)
            v = n_total * sum((w / 10000.0) * m * m * (1 + 3 * p) - ((w / 10000.0) * m * (1 + p)) ** 2
                              for m, w in entries)
            obs = sums.get(str(iid), 0)
            sd = math.sqrt(v) if v > 0 else 0
            z = (obs - e) / sd if sd > 0 else None
            phat = obs / (n_total * sum(m * w / 10000.0 for m, w in entries)) - 1 if n_total > 0 else None
            zphat = None
            if phat is not None and v > 0:
                zphat = (phat - p) / math.sqrt(v / (n_total * sum(m * w / 10000.0 for m, w in entries)) ** 2)
            if z is not None and abs(z) > 3:
                all_ok = False
            detail[str(iid)] = {"obs": obs, "expect": round(e, 1), "z": round(z, 2) if z is not None else None,
                                "p_hat": round(phat, 4) if phat is not None else None,
                                "z_phat": round(zphat, 2) if zphat is not None else None}
        return {"n": n_total, "p_expect": p, "wm_total": round(wm, 2), "var_total": round(var, 1),
                "p_snapshot_source": "runtime_getPrivilegeVal", "per_item": detail}, all_ok

    st1, ok1 = zcheck(row.get("reward1") or [], n1, p1, "tier1")
    RESULT["stats_tier1"] = st1
    rec("TIER1_DROP_Z", ok1, f"tier1 掉落+翻倍联合 z 检验 ({n_success}次广告, n={n1}, p={p1}, 档位{fitted_id}): "
                             f"{ {k: v['z'] for k, v in st1['per_item'].items()} }", detail=st1)
    zps = [v["z_phat"] for v in st1["per_item"].values() if v["z_phat"] is not None]
    dbl_ok = bool(zps) and all(abs(z) <= 3 for z in zps)
    det_note = ""
    if not zps:  # 纯必中+p=0 → var=0 确定性: 直接看恒定值
        exact = all(st1["per_item"][k]["obs"] == st1["per_item"][k]["expect"] for k in st1["per_item"])
        dbl_ok = exact
        det_note = f"(必中条目方差=0→确定性判定: {'观测与期望精确恒等' if exact else '观测偏离期望→存在非零翻倍!'})"
    rec("TIER1_DOUBLE_30PCT", dbl_ok,
        f"翻倍率 p̂(per-item)={ [v['p_hat'] for v in st1['per_item'].values()] } 期望 p={p1} z={zps} {det_note} "
        f"(特权读数 {RESULT.get('priv_ref')})")
    st2, ok2 = zcheck(row.get("reward2") or [], n2, p2, "tier2")
    RESULT["stats_tier2"] = st2
    rec("TIER2_DROP_Z", ok2 if n2 >= 1000 else None,
        f"tier2 z 检验 (n={n2}, p={p2}, 参考级): { {k: v['z'] for k, v in st2['per_item'].items()} }", detail=st2)
    RESULT["aggregate_counts"] = sums
    save()


def main():
    global OUT_DIR, DATA_JSON, TAG
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="baseline", choices=["smoke", "baseline", "after", "opencard"])
    ap.add_argument("--accounts", default=DEFAULT_ACCOUNTS)
    ap.add_argument("--prep", action="store_true", help="仅执行账号准备(造号由 gm_account.py 先行)")
    ap.add_argument("--opencard", action="store_true", help="激活离线闯关特权卡(card_id=7)并校验特权读数, 不采样")
    a = ap.parse_args()
    TAG = a.tag
    accounts = [x.strip() for x in a.accounts.split(",") if x.strip()]

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    OUT_DIR = ROOT / "reports" / f"probe_guaji_rate_{ts}"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DATA_JSON = OUT_DIR / "data.json"
    RESULT.update({"tag": TAG, "accounts": accounts, "start_time": datetime.now().isoformat(timespec="seconds"),
                   "out_dir": str(OUT_DIR), "p_require": P_REQUIRE, "mainline_stage": MAINLINE_STAGE,
                   "ad_calc_sec": AD_CALC_SEC})
    try:
        RESULT["cfg_rows"] = parse_cfg_lua()
    except Exception as e:
        print(f"cfg 解析失败(将无法拟合档位): {e}", flush=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
        ])
        ctx = browser.new_context(viewport={"width": 1280, "height": 720})
        page = ctx.new_page()
        try:
            # 0) 开卡模式: 激活卡7 + 特权读数校验, 不采样
            if a.opencard:
                oks = {}
                for acc in accounts:
                    print(f"[opencard] {acc}", flush=True)
                    oks[acc] = opencard_account(page, acc)
                    save()
                rec("OPENCARD_DONE", all(oks.values()), f"开卡判定(以特权读数mul=3000为准): {oks}")
                return

            # 1) 账号准备/快照
            infos = {}
            for acc in accounts:
                print(f"[prep] {acc}", flush=True)
                infos[acc] = prep_account(page, acc)
                save()
            RESULT["account_infos"] = infos
            RESULT["priv_ref"] = next((v["priv"] for v in infos.values()
                                       if isinstance(v.get("priv"), dict) and v["priv"].get("mul") is not None),
                                      {}) or {"mul": None, "mul2": None, "card_valid": None}
            rec("PRIV_REF", None, f"期望翻倍率来源: {RESULT['priv_ref']} (读数缺失则按口径30%兜底)")
            if a.prep:
                rec("PREP_ONLY", True, "--prep 模式: 账号准备完成, 未采样")
                return

            # 2) 逐号采样(单浏览器顺序执行, 每号3次广告)
            for acc in accounts:
                print(f"[sample] {acc}", flush=True)
                login_flow(page, acc)
                sample_account(page, acc, infos.get(acc) or {})
            # 3) 统计
            stats_all()
        except Exception as e:
            rec("EXCEPTION", False, f"{type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
        finally:
            RESULT["end_time"] = datetime.now().isoformat(timespec="seconds")
            save()
            browser.close()

    gen_report()
    print(f"\n产物: {OUT_DIR}\n报告: temp_case/reports/probe_guaji_翻倍概率_{TAG}.md", flush=True)


def gen_report():
    L = [f"# 挂机奖励30%翻倍概率探针报告 v2（{TAG}轮·广告通道）", "",
         f"- 时间: {RESULT.get('start_time')}  账号: {RESULT.get('accounts')}  档位: 主线{RESULT.get('mainline_stage')}→cfg[103](tier1全必中)",
         f"- 特权快照: {RESULT.get('priv_ref')}  每号广告次数: {AD_COUNT}×CalcReward({AD_CALC_SEC}s)",
         f"- 产物: {RESULT.get('out_dir')}", "",
         "## 结论速览", ""]
    for c in RESULT.get("checks", []):
        if c["key"].startswith("AD_"):
            continue
        tag = "PASS" if c["passed"] is True else ("FAIL" if c["passed"] is False else "INFO")
        L.append(f"- **[{tag}] {c['key']}**: {c['note']}")
    st1 = RESULT.get("stats_tier1")
    if st1:
        L += ["", "## tier1 明细（广告通道, 掉落+翻倍联合 z 检验）", "",
              f"n={st1['n']} 掷, 期望翻倍率 p={st1['p_expect']}", "",
              "| item | 实测 | 期望 | z | p̂(翻倍率) | z(p̂) |", "|---|---|---|---|---|---|"]
        for iid, d in st1["per_item"].items():
            L.append(f"| {iid} | {d['obs']} | {d['expect']} | {d['z']} | {d['p_hat']} | {d['z_phat']} |")
    st2 = RESULT.get("stats_tier2")
    if st2:
        L += ["", "## tier2 明细（n 较小, 参考级）", "",
              f"n={st2['n']}, p={st2['p_expect']}", "",
              "| item | 实测 | 期望 | z | p̂ | z(p̂) |", "|---|---|---|---|---|---|"]
        for iid, d in st2["per_item"].items():
            L.append(f"| {iid} | {d['obs']} | {d['expect']} | {d['z']} | {d['p_hat']} | {d['z_phat']} |")
    L += ["", "## 逐次记录", "", "| 账号 | 轮次 | 成功 | errcode | 背包增量 |", "|---|---|---|---|---|"]
    for s in RESULT.get("samples", []):
        d = s.get("bag_diff") or {}
        ds = " ".join(f"{k}×{v}" for k, v in d.items() if v) or "-"
        L.append(f"| {s['account']} | {s['round']} | {s.get('ok')} | {s.get('errcode')} | {ds} |")
    L += ["", "## 已知干扰与边界", "",
          "- 主城挂机战斗掉落同窗口进背包（比例<0.1%, item2 万级产出下可忽略）",
          "- item2 单次产出约 2000 万（翻倍部分另计 30%）, 已用 item3/item5（单次≈1872/5616）作主判据防溢出干扰",
          "- 广告每日 3 次/号: 连续两轮采样需跨日或补号",
          "", "## 静态依据", "",
          "- [mod_guaji_reward.lua L248-271](file:///E:/p1-x/trunk/server/src/lua-server/service/lobby/guaji/mod_guaji_reward.lua#L248-L271): "
          "每掷点每条目 r=math.random(0,10000) vs 权重 → 命中后 r2 vs nDoubleWeight 翻倍; nDoubleWeight=GetPrivilege(GUAJI_MUL=10)/GUAJI_MUL2(22)",
          "- [mod_advert.lua L133-168](file:///E:/p1-x/trunk/server/src/lua-server/service/lobby/advert/mod_advert.lua#L133-L168): "
          "C2gsAdvertFinish 无真实广告校验, cd/count 校验后直接 OnFinishCallback → guaji OnAdvertCallback → CalcReward(7200)",
          "- [cfg_advert.lua](file:///E:/p1-x/trunk/server/src/res/Config/advert/cfg_advert.lua): ad_type=1 count=3 cd=1",
          "- [cfg_guaji_reward.lua [103]](file:///E:/p1-x/trunk/server/src/res/Config/guaji/cfg_guaji_reward.lua#L818-L824): "
          "主线19400档 tier1 全必中 {{2,10605},{2,2},{3,1},{3,3},{5,1},{5,2}}×w10000, tier2 7000/2000/1400", ""]
    out = ROOT / "temp_case" / "reports" / f"probe_guaji_翻倍概率_{TAG}.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print("报告已生成:", out, flush=True)


def compare(path_a, path_b):
    da = json.loads(Path(path_a).read_text(encoding="utf-8"))
    db = json.loads(Path(path_b).read_text(encoding="utf-8"))
    L = ["# 挂机奖励30%翻倍概率 前后对照报告（v2广告通道）", "",
         f"- 前(baseline): {da.get('out_dir')}  特权={da.get('priv_ref')}",
         f"- 后(after):    {db.get('out_dir')}  特权={db.get('priv_ref')}", "",
         "## tier1 对比", "", "| item | 前obs | 前p̂ | 后obs | 后p̂ | p̂差 |", "|---|---|---|---|---|---|"]
    sa = da.get("stats_tier1", {}).get("per_item", {})
    sb = db.get("stats_tier1", {}).get("per_item", {})
    for iid in sorted(set(sa) | set(sb), key=int):
        xa, xb = sa.get(iid, {}), sb.get(iid, {})
        pa, pb = xa.get("p_hat"), xb.get("p_hat")
        diff = round(pb - pa, 4) if (pa is not None and pb is not None) else None
        L.append(f"| {iid} | {xa.get('obs', '-')} | {pa} | {xb.get('obs', '-')} | {pb} | {diff} |")
    ka = {c["key"]: c for c in da.get("checks", [])}
    kb = {c["key"]: c for c in db.get("checks", [])}
    L += ["", "## 判定对比", ""]
    for k in sorted(set(ka) | set(kb)):
        va, vb = ka.get(k, {}).get("passed"), kb.get(k, {}).get("passed")
        L.append(f"- {k}: 前={'PASS' if va is True else ('FAIL' if va is False else 'INFO')} / "
                 f"后={'PASS' if vb is True else ('FAIL' if vb is False else 'INFO')}")
    out = ROOT / "temp_case" / "reports" / "probe_guaji_翻倍概率_前后对照.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print("对比报告:", out, flush=True)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--compare":
        compare(sys.argv[2], sys.argv[3])
    elif len(sys.argv) > 2 and sys.argv[1] == "--restat":
        # 从已有 data.json 重算统计(档位拟合修正后无需重采样)
        src = Path(sys.argv[2])
        loaded = json.loads(src.read_text(encoding="utf-8"))
        RESULT.clear()
        RESULT.update(loaded)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        OUT_DIR = src.parent
        DATA_JSON = OUT_DIR / f"data_restat_{ts}.json"
        TAG = f"{RESULT.get('tag')}_restat{ts[-6:]}"
        RESULT["out_dir"] = str(OUT_DIR)
        RESULT["tag"] = TAG
        RESULT["checks"] = [c for c in RESULT.get("checks", []) if not c["key"].startswith(("TIER", "CFG_ROW", "STATS"))]
        stats_all()
        gen_report()
        print(f"\n重算产物: {DATA_JSON}\n报告: temp_case/reports/probe_guaji_翻倍概率_{TAG}.md", flush=True)
    else:
        main()
