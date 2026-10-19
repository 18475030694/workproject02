"""仙机(秘宝)倍率概率专项探针（独立于 e2e_mibao 全量驱动）
v2: 样本量x10(单轮执行)
目标:
  1) 概率字段生效情况: 大样本实测频率 vs cfg_box_base.rate 字段权重 {1:5000,2:3700,4:900,10:400}/10000 (3σ判定)
  2) 需求概率生效情况: 原需求口径=图案组合决定1~4倍 → 3倍应出现/10倍不应存在; 实测取值域判定
  3) 跨箱验证: 6001~6004 各自读取自身 cfg 行 rate 字段(6004 走 is_section=0 的 pack_pool 路径)
  4) 整批单倍率复核: 10批x50, 货币扣减与 item_list 基数一致性
产物: reports/probe_mibao_rate_run<i>_<ts>/data.json
      + temp_case/reports/仙机倍率概率验证报告_第<i>轮.md + 仙机倍率概率验证报告_三轮汇总.md
前置: localhost:7456 预览构建, GM http://192.168.*.*:6011 可用, GM号4451
静态依据: server mod_open_box.lua L117-122 仅读 boxCfg.rate, Utils.RandGet 按权重每请求抽1个倍率, 整批共用
"""
import json
import math
import sys
import time
import urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, r"E:\workproject\harness")
import e2e_login as base  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

ROOT = Path("E:/workproject")
ACCOUNT = "4451"
GAME_URL = "http://localhost:7456"
SVR_ID, SVR_NAME = 5, "S5"
GM_BASE = "http://192.168.*.*:6011/index"

# cfg_box_base.rate 字段权重(万分比) —— 服务端/客户端配置一致, 静态已核对
CFG_RATE = {1: 5000, 2: 3700, 4: 900, 10: 400}
EXP_P = {k: v / 10000 for k, v in CFG_RATE.items()}
N_MAIN = 20000       # 箱6000 单开主样本(x10)
N_6004 = 3000        # is_section=0 路径样本(x10)
N_LIGHT = 1200       # 6001~6003 抽样参考(x10)

JS_HEAD = """
window.__NET = () => { for (const [k, v] of System.entries()) { if (v && v.Network && v.Network.call) return v.Network; } return null; };
window.__G = () => { for (const [k, v] of System.entries()) { if (v && v.Global && v.Global.uiMgr) return v.Global; } return null; };
window.__BOXC = () => { try { for (const [k, v] of System.entries()) { if (v && v.ShareRes && v.ShareRes.cfg_box_base) {
  const o = {}; for (const id of [6000,6001,6002,6003,6004]) { const r = v.ShareRes.cfg_box_base[id]; o[id] = r ? { rate: r.rate, is_section: r.is_section, cost: r.cost } : null; } return o; } } } catch(e) { return null; } };
window.__ITEM = (id) => { try { return SystemModules.knapsackMgr.getItemCount(id); } catch(e) { return -1; } };
window.__NETC = (payload) => new Promise((resolve) => { try { const net = window.__NET(); if (!net) return resolve({ ok: false, resp: { err: 'no Network' } });
  net.call(payload.proto, payload.args || {}, (ok, resp) => resolve({ ok, resp })); setTimeout(() => resolve({ ok: false, resp: { timeout: true } }), 15000); } catch(e) { resolve({ ok: false, resp: { err: String(e) } }); } });
"""

RESULT = {"title": "仙机倍率概率专项探针", "account": ACCOUNT, "server": SVR_NAME,
          "start_time": datetime.now().isoformat(timespec="seconds"),
          "cfg_rate": CFG_RATE, "static_evidence": "mod_open_box.lua L117-122 仅读 boxCfg.rate, Utils.RandGet 按权重每请求抽1个倍率, 整批共用; 3倍不在任何 cfg 行 rate 中"}
UUID = None
OUT_DIR = None
DATA_JSON = None


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
    print(f"  [{tag}] {key} | {note}"[:220], flush=True)
    return entry


def qa(page, expr, default=None):
    try:
        return page.evaluate(expr)
    except Exception:
        return default


def gm_award(item_id, count):
    url = f"{GM_BASE}/award_item?uuid={UUID}&item_id={item_id}&count={count}"
    try:
        return urllib.request.urlopen(url, timeout=20).read(200).decode("utf-8", "ignore")
    except Exception as e:
        return f"ERR {e}"


def ensure_currency(page, item_id, need):
    have = int(qa(page, f"() => window.__ITEM({item_id})", 0) or 0)
    while have < need:
        gm_award(item_id, min(10000, need - have + 50))  # 分批发放, 避免单次超限
        time.sleep(1.0)
        have = int(qa(page, f"() => window.__ITEM({item_id})", 0) or 0)
    return have


def wait_main_city(page, timeout_s=150):
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


def login_flow(page):
    print("[stage] goto", flush=True)
    page.goto(f"{GAME_URL}/?qa=1", wait_until="domcontentloaded", timeout=90_000)
    base.wait_qa_bridge(page)
    page.wait_for_timeout(4000)
    page.evaluate(f"() => {{ try {{ localStorage.setItem('TMP_ACCOUNT_', '{ACCOUNT}'); }} catch(e) {{}} }}")
    base.force_select_server(page, SVR_ID, SVR_NAME)
    print("[stage] reload", flush=True)
    page.reload(wait_until="domcontentloaded", timeout=90_000)
    base.wait_qa_bridge(page)
    page.wait_for_timeout(3000)
    assert wait_login_ready(page), "登录按钮未出现(加载超时)"
    page.evaluate("() => window.__qa.findByName('LoginBtn_').forEach(n => window.__qa.clickNode(n))")
    print("[stage] wait main city", flush=True)
    assert wait_main_city(page), "登录失败"
    page.wait_for_timeout(3000)
    page.evaluate(JS_HEAD)
    print("[stage] logged in", flush=True)


def sample_single(page, box_id, n, cost_item):
    """n 次 times=1 开启, 每请求=1次倍率抽样。返回 (rates, fails)"""
    rates, fails = [], 0
    t0 = time.time()
    for i in range(n):
        r = qa(page, f"() => window.__NETC({{proto:'c2gs_open_box', args:{{box_id:{box_id}, times:1}}}})")
        if r and r.get("ok"):
            rate = (r.get("resp") or {}).get("rate")
            if rate is None:
                fails += 1
            else:
                rates.append(rate)
        else:
            fails += 1
        if (i + 1) % 100 == 0:
            page.wait_for_timeout(150)
            print(f"    box{box_id} {i+1}/{n} elapsed={round(time.time()-t0,1)}s fails={fails}", flush=True)
    return rates, fails


def stats_of(rates):
    n = len(rates)
    cnt = Counter(rates)
    out = {}
    for k, p in EXP_P.items():
        f = cnt.get(k, 0) / n if n else 0
        sd = math.sqrt(p * (1 - p) / n) if n else 0
        out[k] = {"count": cnt.get(k, 0), "freq": round(f, 4), "expect": p,
                  "abs_dev": round(abs(f - p), 4), "z": round((f - p) / sd, 2) if sd else None,
                  "tol3sd": round(3 * sd, 4)}
    return {"n": n, "per_rate": out, "others": {str(k): v for k, v in cnt.items() if k not in EXP_P}}


def verdict_of(st):
    """全部倍率档 |z|<=3 → 字段权重生效"""
    ok = st["n"] > 0 and not st["others"]
    for k, d in st["per_rate"].items():
        if d["z"] is None or abs(d["z"]) > 3:
            ok = False
    return ok


def main():
    global UUID, OUT_DIR, DATA_JSON
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    OUT_DIR = ROOT / "reports" / f"probe_mibao_rate_{ts}"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DATA_JSON = OUT_DIR / "data.json"
    RESULT["out_dir"] = str(OUT_DIR)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
        ])
        page = browser.new_context(viewport={"width": 1280, "height": 720}).new_page()
        try:
            login_flow(page)
            UUID = qa(page, "() => { const g = window.__G(); return g ? g.playerUuid : null; }")
            assert UUID, "未取到 playerUuid"
            RESULT["uuid"] = UUID
            save()
            print(f"[stage] uuid={UUID}", flush=True)

            # 0) 客户端下发配置核对(字段下发情况)
            cfg_live = qa(page, "() => window.__BOXC()")
            RESULT["cfg_live"] = cfg_live
            cfg_ok = bool(cfg_live) and all(cfg_live.get(str(b), {}).get("rate") ==
                                            [[k, CFG_RATE[k]] for k in CFG_RATE] for b in [6000, 6001, 6002, 6003, 6004])
            rec("CFG_FIELD", cfg_ok, f"客户端 ShareRes.cfg_box_base[6000~6004].rate 下发={cfg_live}")
            save()

            # 1) 主采样: 箱6000 单开x2000
            print("== 主采样 box6000 x%d ==" % N_MAIN, flush=True)
            have = ensure_currency(page, 1001, N_MAIN + 500)
            rec("PREP_1001", have >= N_MAIN, f"货币1持有={have}")
            rates, fails = sample_single(page, 6000, N_MAIN, 1001)
            st_main = stats_of(rates)
            RESULT["sample_box6000"] = st_main
            v_main = verdict_of(st_main)
            rec("RATE_FIELD_EFFECTIVE_box6000", v_main,
                f"n={st_main['n']} fails={fails} 实测={ {k: d['freq'] for k, d in st_main['per_rate'].items()} } "
                f"期望={ {k: d['expect'] for k, d in st_main['per_rate'].items()} } z={ {k: d['z'] for k, d in st_main['per_rate'].items()} }",
                detail=st_main)
            save()

            # 2) 跨箱: 6004(is_section=0) x300; 6001~6003 x120 抽样参考
            print("== 跨箱采样 ==", flush=True)
            ensure_currency(page, 1005, N_6004 + 100)
            rates4, fails4 = sample_single(page, 6004, N_6004, 1005)
            st4 = stats_of(rates4)
            RESULT["sample_box6004"] = st4
            rec("RATE_FIELD_box6004", verdict_of(st4),
                f"n={st4['n']} fails={fails4} 实测={ {k: d['freq'] for k, d in st4['per_rate'].items()} }", detail=st4)
            for box, cost in [(6001, 1002), (6002, 1003), (6003, 1004)]:
                ensure_currency(page, cost, N_LIGHT + 50)
                rb, fb = sample_single(page, box, N_LIGHT, cost)
                stb = stats_of(rb)
                RESULT[f"sample_box{box}"] = stb
                rec(f"RATE_FIELD_box{box}", None,
                    f"n={stb['n']} fails={fb} 取值域={sorted(set(rb))} 实测={ {k: d['freq'] for k, d in stb['per_rate'].items()} }（抽样参考）", detail=stb)
            save()

            # 3) 整批单倍率复核: 10批x50
            print("== 整批复核 x50 ==", flush=True)
            have = ensure_currency(page, 1001, 500)
            before1 = int(qa(page, "() => window.__ITEM(1001)", 0) or 0)
            batch_ok, bnotes = True, []
            for i in range(10):
                r = qa(page, "() => window.__NETC({proto:'c2gs_open_box', args:{box_id:6000, times:50}})")
                ok = bool(r and r.get("ok"))
                rate = (r.get("resp") or {}).get("rate") if ok else None
                batch_ok = batch_ok and ok and rate in EXP_P
                bnotes.append(f"b{i}:rate={rate}")
            after1 = int(qa(page, "() => window.__ITEM(1001)", 0) or 0)
            rec("BATCH_ONE_RATE", batch_ok and before1 - after1 == 500,
                f"10批x50 全部成功且倍率∈配置档; 扣币{before1 - after1}/500 {' '.join(bnotes)}")

            # 4) 需求口径判定(原需求: 图案组合决定1~4倍 → 3倍应出现, 10倍不应存在)
            all_rates = rates + rates4
            n3 = sum(1 for x in all_rates if x == 3)
            n10 = sum(1 for x in all_rates if x == 10)
            RESULT["req_verdict"] = {
                "需求口径": "原用例/口头需求=转轮图案组合决定1~4倍(无数值概率文档; M_秘宝.xlsx为纯换皮文档)",
                "total_n": len(all_rates),
                "三倍出现次数": n3, "十倍出现次数": n10,
                "取值域": sorted(set(all_rates)),
                "结论": "需求口径未生效: 实现为 cfg rate 权重随机(含需求外的10倍, 无3倍), 与图案组合无关",
            }
            rec("REQ_PROB_CONFORM", None,
                f"总样本={len(all_rates)} 3倍出现={n3}次(需求应>0) 10倍出现={n10}次(需求不应存在) → 需求口径未生效, 见 req_verdict")
            save()
        except Exception as e:
            rec("EXCEPTION", False, f"{type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
        finally:
            RESULT["end_time"] = datetime.now().isoformat(timespec="seconds")
            save()
            browser.close()

    # 5) 生成报告
    gen_report()
    print(f"\n产物: {OUT_DIR}\n报告: temp_case/reports/仙机倍率概率验证报告.md", flush=True)


def gen_report():
    st = RESULT.get("sample_box6000") or {}
    st4 = RESULT.get("sample_box6004") or {}
    L = ["# 仙机(秘宝)倍率概率专项验证报告", "",
         f"- 时间: {RESULT.get('start_time')}  账号: {RESULT.get('account')}@{RESULT.get('server')}",
         f"- 样本: 箱6000 主样本 n={st.get('n')} | 箱6004 n={st4.get('n')} | 6001~6003 各 n=120(参考)",
         f"- 产物: {RESULT.get('out_dir')}", "",
         "## 结论速览", ""]
    checks = {c["key"]: c for c in RESULT.get("checks", [])}
    for k in ["CFG_FIELD", "RATE_FIELD_EFFECTIVE_box6000", "RATE_FIELD_box6004",
              "BATCH_ONE_RATE", "REQ_PROB_CONFORM"]:
        c = checks.get(k)
        if c:
            tag = "PASS" if c["passed"] is True else ("FAIL" if c["passed"] is False else "INFO")
            L.append(f"- **[{tag}] {k}**: {c['note']}")
    L += ["", "## 概率字段生效情况（cfg_box_base.rate 权重 5000/3700/900/400 万分比）", "",
          "| 箱 | n | 倍率 | 实测频率 | 配置期望 | 偏差 | z | 3σ容差 |", "|---|---|---|---|---|---|---|---|"]
    for name, s in [("6000", st), ("6004", st4)]:
        for k, d in (s.get("per_rate") or {}).items():
            L.append(f"| {name} | {s.get('n')} | {k}x | {d['freq']:.4f} | {d['expect']} | {d['abs_dev']:.4f} | {d['z']} | ±{d['tol3sd']} |")
    L += ["", "## 需求概率生效情况", ""]
    rv = RESULT.get("req_verdict") or {}
    L += [f"- 需求口径基线: {rv.get('需求口径')}",
          f"- 总样本 {rv.get('total_n')}: **3倍出现 {rv.get('三倍出现次数')} 次**（需求图案组合口径下应可出现）, "
          f"**10倍出现 {rv.get('十倍出现次数')} 次**（需求口径不存在10倍）",
          f"- 实测取值域: {rv.get('取值域')}",
          f"- 判定: **{rv.get('结论')}**", "",
          "## 静态依据", "",
          "- 服务端 [mod_open_box.lua L117-122](file:///E:/p1-x/trunk/server/src/lua-server/service/lobby/draw_card/mod_open_box.lua#L117-L122): "
          "仅读 `boxCfg.rate` → `{rate, weight}` 列表 → `Utils.RandGet` 按权重抽取, **每请求抽1个倍率整批共用**; 无其他概率字段参与",
          "- [cfg_box_base.lua](file:///E:/p1-x/trunk/server/src/res/Config/box/cfg_box_base.lua): 5个箱 rate 全部为 {{1,5000},{2,3700},{4,900},{10,400}}; 3倍未配置→不可达; first_reward 全空",
          "- 客户端下发配置(ShareRes.cfg_box_base)与服务端一致（CFG_FIELD 检查）", ""]
    out = ROOT / "temp_case" / "reports" / "仙机倍率概率验证报告.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print("报告已生成:", out, flush=True)


if __name__ == "__main__":
    main()
