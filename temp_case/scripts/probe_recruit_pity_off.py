"""招募「200抽必出哪吒」移除 循环验证探针
需求口径: r11043(2026-10-13 17:32) 删除 cfg_recruit_must [200]={5207哪吒} / [300]={5201九尾天狐}
  → 第200抽不再强制必出哪吒(回归普通池 / 神卡保底池随机金)
静态依据:
  - mod_recruit.lua L249-251: 仅当 mustCfg[nNowCount] 存在才强制替换奖励 → 配置无[200]即不强制
  - SVN r11043 diff(已核实): 删除 [200]/[300] 条目; trunk 本地工作副本已同步
  - must_count2=200 神卡保底(若S5已部署 r10649+ 代码): 计数满200 → stageCfg2 全金池(随机金卡, 非指定哪吒)
  - 一键高级号自带 [1000]凡灵召符x9999 (lobby/gm/object.lua L320) → 不依赖 GM HTTP
验证设计(循环):
  - 20 轮 x 200 单抽, 每轮新号(create_and_upgrade, client通道)
  - 轮判定: 第200抽 != 5207 → PASS(不必出生效); == 5207 → SUSPECT
  - 全局: 任一轮 != 5207 → PASS(r11043 已在 S5 生效); 全部==5207 → 自动追加2轮, 仍全==5207 → FAIL(S5疑似未更新)
  - 附带观察: 1-10抽固定序列(账户新鲜度/配置sanity)、200抽前随机金卡、must_count2 字段有无(代码部署状态)
产物: reports/probe_recruit_pity_off_<ts>/data.json + temp_case/reports/招募必出哪吒移除_循环验证报告.md
前置: localhost:7456 预览构建; 游戏服在线(192.168.*.*); GM HTTP(192.168.*.*:6011)可选(不可达时自动跳过补券)
复用: temp_case/scripts/probe_recruit_pity.py (2026-09-24 招募保底机制专项探针) 的登录/采样/重连机制
"""
import json
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, r"E:\workproject\harness")
import e2e_login as base            # noqa: E402
import gm_account                   # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

ROOT = Path("E:/workproject")
SVR_ID, SVR_NAME = 5, "S5"
GM_BASE = "http://192.168.*.*:6011/index"
COST_ITEM = 1000                     # 凡灵召符, 1券/抽
ROUNDS = 20                          # 基础轮数
EXTEND_ROUNDS = 2                    # 全部==5207时的追加轮数上限
DRAWS_PER_ROUND = 200

NEZHA = 5207
MUST_SEQ = [5222, 5101, 5009, 5113, 5114, 5009, 5113, 5013, 5009, 5225]  # mustCfg[1..10] r11043 保留
GOLD_SET = {5201, 5202, 5203, 5204, 5205, 5206, 5207, 5209, 5210, 5213}

JS_HEAD = """
window.__NET = () => { for (const [k, v] of System.entries()) { if (v && v.Network && v.Network.call) return v.Network; } return null; };
window.__G = () => { for (const [k, v] of System.entries()) { if (v && v.Global && v.Global.uiMgr) return v.Global; } return null; };
window.__ITEM = (id) => { try { return SystemModules.knapsackMgr.getItemCount(id); } catch(e) { return -1; } };
window.__NETC = (payload) => new Promise((resolve) => { try { const net = window.__NET(); if (!net) return resolve({ ok: false, resp: { err: 'no Network' } });
  net.call(payload.proto, payload.args || {}, (ok, resp) => resolve({ ok, resp })); setTimeout(() => resolve({ ok: false, resp: { timeout: true } }), 15000); } catch(e) { resolve({ ok: false, resp: { err: String(e) } }); } });
"""

RESULT = {"title": "招募「200抽必出哪吒」移除 循环验证",
          "server": f"{SVR_ID}/{SVR_NAME}",
          "start_time": datetime.now().isoformat(timespec="seconds"),
          "static_evidence": "r11043(2026-10-13)删除 cfg_recruit_must [200]=5207/[300]=5201; mod_recruit.lua L249-251 mustCfg[n]存在才强制; must_count2=200神卡保底池为随机金",
          "rounds": []}
OUT_DIR, DATA_JSON = None, None


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
    print(f"  [{tag}] {key} | {note}"[:230], flush=True)
    return entry


def qa(page, expr, default=None):
    try:
        return page.evaluate(expr)
    except Exception:
        return default


def gm_award(item_id, count):
    url = f"{GM_BASE}/award_item?uuid={RESULT.get('uuid')}&item_id={item_id}&count={count}"
    try:
        return urllib.request.urlopen(url, timeout=10).read(200).decode("utf-8", "ignore")
    except Exception as e:
        return f"ERR {e}"


def draw_once(page):
    r = qa(page, "() => window.__NETC({proto:'c2gs_recruit_draw', args:{count:1}})")
    if not (r and r.get("ok")):
        return {"ok": False, "err": "net_fail", "raw": r}
    resp = r.get("resp") or {}
    if resp.get("errcode") not in (0, None):
        return {"ok": False, "err": f"errcode={resp.get('errcode')}", "resp": resp}
    lst = resp.get("award_list") or []
    first = lst[0] if lst else {}
    return {"ok": True, "id": first.get("id"),
            "mc": resp.get("must_count"), "total": resp.get("total_count"),
            "m2": resp.get("must_count2")}


def run_round(idx):
    """单轮: 新号 → 登录 → 200单抽。返回轮记录 dict。"""
    print(f"\n===== ROUND {idx}: 创建新号+一键高级号 ...", flush=True)
    acct = gm_account.create_and_upgrade(SVR_ID, SVR_NAME, headless=True)
    assert acct.get("ok"), f"新号创建/升级失败: {json.dumps(acct, ensure_ascii=False)[:300]}"
    ACCOUNT = acct["account"]
    print(f"[round {idx}] 账号={ACCOUNT}", flush=True)

    rnd = {"round": idx, "account": ACCOUNT, "draws": [], "ok": False}
    RESULT["rounds"].append(rnd)
    save()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
        ])
        page = browser.new_context(viewport={"width": 1280, "height": 720}).new_page()
        try:
            gm_account.login_session(page, ACCOUNT, SVR_ID, SVR_NAME)
            page.wait_for_timeout(3000)
            page.evaluate(JS_HEAD)
            RESULT["uuid"] = qa(page, "() => { const g = window.__G(); return g ? g.playerUuid : null; }")
            assert RESULT["uuid"], "未取到 playerUuid"
            rec(f"R{idx}_LOGIN", True, f"uuid={RESULT['uuid']} account={ACCOUNT}")

            # 券量检查(一键高级号自带9999; 不足且GM HTTP不可达则中止该轮)
            have = int(qa(page, f"() => window.__ITEM({COST_ITEM})", 0) or 0)
            rnd["tickets"] = have
            if have < DRAWS_PER_ROUND:
                gm_award(COST_ITEM, DRAWS_PER_ROUND - have + 50)
                time.sleep(1.5)
                have = int(qa(page, f"() => window.__ITEM({COST_ITEM})", 0) or 0)
            if have < DRAWS_PER_ROUND:
                rec(f"R{idx}_TICKET", False, f"凡灵召符不足: {have}<{DRAWS_PER_ROUND}, 中止该轮")
                return rnd
            rec(f"R{idx}_TICKET", True, f"凡灵召符 持有={have}")

            # 200 单抽(带重连兜底)
            net_fail_burst, reconnects = 0, 0

            def reconnect():
                page.reload(wait_until="domcontentloaded", timeout=90_000)
                base.wait_qa_bridge(page)
                page.wait_for_timeout(4000)
                gm_account.login_session(page, ACCOUNT, SVR_ID, SVR_NAME)
                page.wait_for_timeout(2000)
                page.evaluate(JS_HEAD)

            t0 = time.time()
            while len([x for x in rnd["draws"] if x.get("ok")]) < DRAWS_PER_ROUND:
                d = draw_once(page)
                if not d.get("ok"):
                    net_fail_burst += 1
                    if net_fail_burst >= 5:
                        if reconnects < 2:
                            net_fail_burst = 0
                            rec(f"R{idx}_NET", None, f"连续失败, 重连(第{reconnects + 1}次)")
                            try:
                                reconnect()
                                reconnects += 1
                                continue
                            except Exception as e:
                                rec(f"R{idx}_NET", False, f"重连失败: {e}")
                                return rnd
                        rec(f"R{idx}_NET", False, "连续失败且重连次数用尽, 中止该轮")
                        return rnd
                    page.wait_for_timeout(1000)
                    continue
                net_fail_burst = 0
                rnd["draws"].append(d)
                n = d.get("total") or len([x for x in rnd["draws"] if x.get("ok")])
                if n % 50 == 0:
                    save()
                    print(f"    [round {idx}] n={n} id={d['id']} elapsed={round(time.time() - t0, 1)}s", flush=True)
                if n % 50 == 0:
                    page.wait_for_timeout(100)

            draws_ok = [x for x in rnd["draws"] if x.get("ok")]
            seq10 = [x["id"] for x in draws_ok[:10]]
            early_golds = [{"n": x["total"], "id": x["id"]} for x in draws_ok if x["total"] < DRAWS_PER_ROUND and x["id"] in GOLD_SET]
            d200 = draws_ok[DRAWS_PER_ROUND - 1]
            m2_fields = sum(1 for x in draws_ok if x.get("m2") is not None)

            rnd["seq10"] = seq10
            rnd["early_golds"] = early_golds
            rnd["draw200"] = {"id": d200["id"], "gold": d200["id"] in GOLD_SET, "m2": d200.get("m2")}
            rnd["m2_field_count"] = m2_fields
            rnd["ok"] = True

            rec(f"R{idx}_MUST_1_10_SEQ", seq10 == MUST_SEQ, f"1-10抽序列={seq10}")
            rec(f"R{idx}_EARLY_GOLD", None,
                f"1-199抽随机金卡={early_golds or '无'}(金卡会清零神卡保底计数)", detail=early_golds)
            rec(f"R{idx}_M2_FIELD", None,
                f"must_count2 字段下发抽数={m2_fields}/200 (0=服务端代码未部署r10649+, 仅配置层验证)")
            rec(f"R{idx}_DRAW200_OFF", d200["id"] != NEZHA,
                f"第200抽 id={d200['id']}" + (" (是哪吒→疑似仍必出)" if d200["id"] == NEZHA else
                       f" (金卡={d200['id'] in GOLD_SET}, 非指定哪吒→不必出生效)"))
        except Exception as e:
            rec(f"R{idx}_EXCEPTION", False, f"{type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
        finally:
            save()
            browser.close()
    return rnd


def gen_report():
    rounds = RESULT.get("rounds", [])
    checks = RESULT.get("checks", [])

    def tag(k):
        for c in checks:
            if c["key"] == k:
                return "PASS" if c["passed"] is True else ("FAIL" if c["passed"] is False else "INFO")
        return "SKIP"

    d200_list = [(r["round"], (r.get("draw200") or {}).get("id")) for r in rounds if r.get("ok")]
    nezha_rounds = [n for n, i in d200_list if i == NEZHA]
    verdict = None
    if d200_list and any(i != NEZHA for _, i in d200_list):
        verdict = ("PASS", f"第200抽不再强制哪吒: {d200_list} → r11043 已在 S5 生效")
    elif len(nezha_rounds) >= ROUNDS + EXTEND_ROUNDS:
        verdict = ("FAIL", f"{len(nezha_rounds)}轮第200抽全部=5207哪吒 → S5 疑似仍运行旧配置(未同步/未热更 r11043)")
    elif d200_list:
        verdict = (None, f"样本不足判定: {d200_list}")
    RESULT["verdict"] = {"passed": verdict[0], "note": verdict[1]}

    L = [f"# 招募「200抽必出哪吒」移除 循环验证报告（{ROUNDS}号）", "",
         f"- 时间: {RESULT.get('start_time')}  服务: {RESULT.get('server')}",
         f"- 静态依据: {RESULT.get('static_evidence')}",
         f"- 产物: {RESULT.get('out_dir')}", "",
         "## 结论速览", ""]
    if verdict[0] is True:
        L.append(f"- **[PASS] VERDICT**: {verdict[1]}")
    elif verdict[0] is False:
        L.append(f"- **[FAIL] VERDICT**: {verdict[1]}")
    else:
        L.append(f"- **[INFO] VERDICT**: {verdict[1]}")
    for c in checks:
        L.append(f"- **[{tag(c['key'])}] {c['key']}**: {c['note']}")
    L += ["", "## 每轮第200抽明细", "",
          "| 轮 | 账号 | 第200抽id | 金卡 | 是哪吒 | m2字段覆盖 | 1-199随机金卡 |", "|---|---|---|---|---|---|---|"]
    for r in rounds:
        if not r.get("ok"):
            L.append(f"| {r['round']} | {r.get('account')} | (未完成) | | | | |")
            continue
        d2 = r["draw200"]
        L.append(f"| {r['round']} | {r['account']} | {d2['id']} | {'是' if d2['gold'] else ''} | "
                 f"{'是' if d2['id'] == NEZHA else '否'} | {r['m2_field_count']}/200 | {r['early_golds'] or '无'} |")
    L += ["", "## 判定口径", "",
          "- 移除生效: 任一轮第200抽 != 5207（旧配置下第200抽为确定性哪吒, 不可能偏差）",
          "- 第200抽为随机金卡(非哪吒): 符合 must_count2=200 神卡保底池口径(stageCfg2 全金池, 随机而非指定)",
          "- 第200抽为紫卡/普卡: 说明该轮 1-199 出过金卡清零计数, 且服务端无 isMust2 代码(或未触发), 同样证明无[200]强制", ""]
    out = ROOT / "temp_case" / "reports" / f"招募必出哪吒移除_循环验证报告_{ROUNDS}号.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print("报告已生成:", out, flush=True)


def main():
    global OUT_DIR, DATA_JSON
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    OUT_DIR = ROOT / "reports" / f"probe_recruit_pity_off_{ts}"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DATA_JSON = OUT_DIR / "data.json"
    RESULT["out_dir"] = str(OUT_DIR)
    save()

    done = 0
    total_planned = ROUNDS
    while done < total_planned and done < ROUNDS + EXTEND_ROUNDS:
        try:
            rnd = run_round(done + 1)
        except Exception as e:
            rec(f"R{done + 1}_FATAL", False, f"{type(e).__name__}: {e}")
            done += 1
            continue
        done += 1
        # 全部轮次均==5207时才追加轮数
        ok_rounds = [r for r in RESULT["rounds"] if r.get("ok")]
        if ok_rounds and all((r.get("draw200") or {}).get("id") == NEZHA for r in ok_rounds):
            if done >= ROUNDS and done < ROUNDS + EXTEND_ROUNDS:
                rec("EXTEND", None, f"前{done}轮第200抽全部=5207, 追加验证轮(共{ROUNDS + EXTEND_ROUNDS}轮)")
                total_planned = done + 1
        save()

    gen_report()
    print(f"\n产物: {OUT_DIR}", flush=True)


if __name__ == "__main__":
    main()
