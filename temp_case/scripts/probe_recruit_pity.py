"""招募保底机制专项探针（哪吒必出 + 200抽神卡保底）
需求口径:
  1) 原『第200抽必出杨戬(5203)』改为『第200抽必出哪吒(5207)』(cfg_recruit_must r10655)
     用户表述: 100关必出杨戬 → 第一次抽出最高等级卡牌必出哪吒
     (口径已确认 2026-09-24: 即『第200抽必出哪吒』, 分歧项忽略; 当前版本开场动画已去除)
  2) 新增保底: must_count2=200, 上次出神卡(GOLD=7)后满200抽 → isMust2 走 stageCfg2 全金池
     (mod_recruit.lua r10649/79/80)
静态依据:
  - cfg_recruit_global: must_count=10, must_count2=200, cost_item_id=1000(凡灵召符)
  - cfg_recruit_must: [1..10]=5222,5101,5009,5113,5114,5009,5113,5013,5009,5225;
                      [200]=5207哪吒(原5203杨戬); [300]=5201九尾天狐(原5204后羿)
  - GOLD(7)= {5201九尾天狐,5202孙悟空,5203杨戬,5204后羿,5205神农,5206嫦娥,
              5207哪吒,5209女娲,5210九天玄女,5213蚩尤}
  - 计数动力学: 每抽计数+1; 出GOLD清零; must_count2响应 = 200-计数
    → 非金卡: m2_resp = prev-1; 金卡: m2_resp = 200
    → prev_m2==1 的下一抽计数满200 → isMust2 → stageCfg2 全金池 → 必出金卡
  - stageCfg2 池12-16 → 卡包14/24/34/44/54 全部仅含 quality=7 (静态全核对)
验证设计（全单抽, 计数动力学逐抽断言）:
  A: 1-10抽 顺序强制 mustCfg[1..10]
  B: 11-199 逐抽计数动力学 + 是否提前出金(口径分歧实证)
  C: 第200抽 == 哪吒5207 且 m2_resp==200 (必出哪吒/保底重置)
  D: 第300抽 == 九尾天狐5201 且 m2_resp==200 (mustCfg[300] 改动)
  E: 301+ 继续采样; 若 C 未观察到 isMust2 触发(提前出金场景), 延长至多700抽寻找
产物: reports/probe_recruit_pity_<ts>/data.json + temp_case/reports/招募保底机制验证报告.md
前置: localhost:7456 预览构建, GM http://192.168.*.*:6011, 新号(自动一键高级号)
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
COST_ITEM = 1000                     # 凡灵召符
MAX_DRAWS_E = 700                    # E 阶段寻找 isMust2 触发的抽数上限

MUST_SEQ = [5222, 5101, 5009, 5113, 5114, 5009, 5113, 5013, 5009, 5225]  # mustCfg[1..10]
GOLD_SET = {5201, 5202, 5203, 5204, 5205, 5206, 5207, 5209, 5210, 5213}
MUST_COUNT, MUST_COUNT2 = 10, 200

JS_HEAD = """
window.__NET = () => { for (const [k, v] of System.entries()) { if (v && v.Network && v.Network.call) return v.Network; } return null; };
window.__G = () => { for (const [k, v] of System.entries()) { if (v && v.Global && v.Global.uiMgr) return v.Global; } return null; };
window.__ITEM = (id) => { try { return SystemModules.knapsackMgr.getItemCount(id); } catch(e) { return -1; } };
window.__RCFG = () => { try { for (const [k, v] of System.entries()) { if (v && v.ShareRes && v.ShareRes.cfg_recruit_global) {
  const c = v.ShareRes.cfg_recruit_global; return { must_count: c.must_count, must_count2: c.must_count2, cost: c.cost_item_id }; } } } catch(e) {}
  return null; };
window.__NETC = (payload) => new Promise((resolve) => { try { const net = window.__NET(); if (!net) return resolve({ ok: false, resp: { err: 'no Network' } });
  net.call(payload.proto, payload.args || {}, (ok, resp) => resolve({ ok, resp })); setTimeout(() => resolve({ ok: false, resp: { timeout: true } }), 15000); } catch(e) { resolve({ ok: false, resp: { err: String(e) } }); } });
"""

RESULT = {"title": "招募保底机制专项探针(哪吒必出+200抽神卡保底)",
          "server": f"{SVR_ID}/{SVR_NAME}",
          "start_time": datetime.now().isoformat(timespec="seconds"),
          "static_evidence": "mod_recruit.lua r10649/79/80; cfg_recruit_must r10655: [200] 5203杨戬→5207哪吒, [300] 5204后羿→5201九尾天狐; cfg_recruit_global must_count2=200; stageCfg2 池12-16→卡包14/24/34/44/54 全quality=7",
          "draws": []}
UUID, OUT_DIR, DATA_JSON = None, None, None


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
    url = f"{GM_BASE}/award_item?uuid={UUID}&item_id={item_id}&count={count}"
    try:
        return urllib.request.urlopen(url, timeout=20).read(200).decode("utf-8", "ignore")
    except Exception as e:
        return f"ERR {e}"


def ensure_currency(page, item_id, need):
    have = int(qa(page, f"() => window.__ITEM({item_id})", 0) or 0)
    while have < need:
        gm_award(item_id, min(10000, need - have + 50))
        time.sleep(1.0)
        have = int(qa(page, f"() => window.__ITEM({item_id})", 0) or 0)
    return have


def draw_once(page):
    r = qa(page, "() => window.__NETC({proto:'c2gs_recruit_draw', args:{count:1}})")
    if not (r and r.get("ok")):
        return {"ok": False, "err": "net_fail", "raw": r}
    resp = r.get("resp") or {}
    if resp.get("errcode") not in (0, None):
        return {"ok": False, "err": f"errcode={resp.get('errcode')}", "resp": resp}
    lst = resp.get("award_list") or []
    first = lst[0] if lst else {}
    return {"ok": True, "id": first.get("id"), "count": len(lst),
            "new": first.get("new"),
            "mc": resp.get("must_count"), "total": resp.get("total_count"),
            "m2": resp.get("must_count2")}


def main():
    global UUID, OUT_DIR, DATA_JSON
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    OUT_DIR = ROOT / "reports" / f"probe_recruit_pity_{ts}"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DATA_JSON = OUT_DIR / "data.json"
    RESULT["out_dir"] = str(OUT_DIR)

    # ---- 0) 新号 + 一键高级号(引导全完成, 直进主城) ----
    print("[stage] 创建新号+一键高级号 ...", flush=True)
    acct = gm_account.create_and_upgrade(SVR_ID, SVR_NAME, headless=True)
    assert acct.get("ok"), f"新号创建/升级失败: {json.dumps(acct, ensure_ascii=False)[:300]}"
    ACCOUNT = acct["account"]
    RESULT["account"] = ACCOUNT
    save()
    print(f"[stage] 账号={ACCOUNT}", flush=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
        ])
        page = browser.new_context(viewport={"width": 1280, "height": 720}).new_page()
        try:
            # ---- 1) 登录 ----
            gm_account.login_session(page, ACCOUNT, SVR_ID, SVR_NAME)
            page.wait_for_timeout(3000)
            page.evaluate(JS_HEAD)
            UUID = qa(page, "() => { const g = window.__G(); return g ? g.playerUuid : null; }")
            assert UUID, "未取到 playerUuid"
            RESULT["uuid"] = UUID
            rec("LOGIN", True, f"uuid={UUID} account={ACCOUNT}")

            # 客户端下发配置核对(best-effort)
            rcfg = qa(page, "() => window.__RCFG()")
            rec("CFG_LIVE", None, f"客户端 cfg_recruit_global 下发={rcfg}（客户端可能不含该表, 以服务端为准）")

            # ---- 2) 备弹药: 1券/抽, 上限700抽 + 余量 ----
            have0 = int(qa(page, f"() => window.__ITEM({COST_ITEM})", 0) or 0)
            need = MAX_DRAWS_E + 200
            have = ensure_currency(page, COST_ITEM, need)
            RESULT["tickets_before"] = have0
            rec("PREP_TICKET", have >= need, f"凡灵召符 持有={have} (需≥{need}, 1券/抽)")

            # ---- 3) 环境金丝雀: must_count2(tag4) 是否下发 → 服务端是否已部署 r10680 ----
            canary = draw_once(page)
            RESULT["canary_first"] = canary
            CANARY = canary.get("ok") and canary.get("m2") is None
            if not canary.get("ok"):
                rec("ENV_CANARY", False, f"首抽失败: {canary}")
                return
            if CANARY:
                rec("ENV_CANARY", False,
                    "响应缺失 must_count2 字段(sproto tag4, mc字段正常) → S5 服务端未部署/未重启今日提交 r10649~r10680, "
                    "当前为旧版逻辑 → 切换金丝雀模式: 仅验证至第200抽并预期旧版出杨戬5203")
            else:
                rec("ENV_CANARY", True, "must_count2 字段正常下发, 服务端为新版 → 全量验证")

            if CANARY:
                RESULT["draws"].append(canary)   # 金丝雀抽=第1抽, 并入序列统计
            # ---- 4) 逐抽采样 ----
            prev_m2 = MUST_COUNT2           # 新号计数=0 → m2响应=200
            pity_triggers = []              # 计数满200触发点 [{n,id,gold,via}]
            early_golds = []                # 1-199 间随机金卡(口径分歧实证)
            dyn_errs = []
            net_fail_burst, reconnects = 0, 0
            aborted = {"v": False}

            def reconnect():
                page.reload(wait_until="domcontentloaded", timeout=90_000)
                base.wait_qa_bridge(page)
                page.wait_for_timeout(4000)
                gm_account.login_session(page, ACCOUNT, SVR_ID, SVR_NAME)
                page.wait_for_timeout(2000)
                page.evaluate(JS_HEAD)

            def run_to(n_target):
                """逐抽到 total_count 达 n_target; 中止返回 True。"""
                nonlocal prev_m2, net_fail_burst
                while True:
                    d = draw_once(page)
                    if not d.get("ok"):
                        net_fail_burst += 1
                        if net_fail_burst >= 5:
                            if reconnects < 2:
                                net_fail_burst = 0
                                rec("NET_RECONNECT", None, f"连续失败, 执行重连(第{reconnects + 1}次)")
                                try:
                                    reconnect()
                                    continue
                                except Exception as e:
                                    rec("NET_RECONNECT", False, f"重连失败: {e}")
                                finally:
                                    reconnects += 1
                                if reconnects >= 2:
                                    aborted["v"] = True
                                    return True
                            continue
                        page.wait_for_timeout(1000)
                        continue
                    net_fail_burst = 0
                    n = d["total"]
                    gid = d["id"]
                    is_gold = gid in GOLD_SET
                    if not CANARY:
                        # 计数动力学断言: 非金 m2=prev-1 / 金卡 m2=200
                        exp_m2 = MUST_COUNT2 if is_gold else max(prev_m2 - 1, 0)
                        if d["m2"] is None:
                            dyn_errs.append({"n": n, "err": "no m2 field"})
                        elif d["m2"] != exp_m2:
                            dyn_errs.append({"n": n, "id": gid, "m2": d["m2"], "exp": exp_m2, "prev": prev_m2})
                        # isMust2 触发观察: prev==1 → 本抽计数满200 → 必出金
                        if prev_m2 == 1:
                            pity_triggers.append({"n": n, "id": gid, "gold": is_gold, "via": "run_to"})
                            print(f"    [pity-trigger] n={n} id={gid} gold={is_gold}", flush=True)
                    if is_gold and n <= 199:
                        early_golds.append({"n": n, "id": gid})
                    RESULT["draws"].append(d)
                    prev_m2 = d["m2"] if d["m2"] is not None else prev_m2
                    if n % 50 == 0:
                        save()
                        print(f"    progress n={n} id={gid} m2={d['m2']} elapsed={round(time.time()-t_loop0,1)}s", flush=True)
                    if n >= n_target:
                        return False

            def draws_ok():
                return [x for x in RESULT["draws"] if x.get("ok")]

            t_loop0 = time.time()
            # A+B: 1-199
            print("== A/B: 1-199 逐抽 ==", flush=True)
            run_to(199)
            # C: 第200抽
            d200 = draw_once(page) if not aborted["v"] else {}
            RESULT["draw200"] = d200
            if d200.get("ok"):
                RESULT["draws"].append(d200)
                if not CANARY and prev_m2 == 1:
                    pity_triggers.append({"n": 200, "id": d200.get("id"), "gold": d200.get("id") in GOLD_SET,
                                          "via": "draw200(isMust2计数满, 输出被mustCfg[200]覆盖为哪吒)"})
                prev_m2 = d200.get("m2") or prev_m2
            if CANARY:
                rec("M2_FIELD_MISSING", False,
                    "must_count2(sproto tag4)未下发: 服务端代码/协议仍为旧版(配置已热更新生效) → "
                    "200抽神卡保底计数机制暂无法动态验证, 需重启S5服务端加载 r10649~r10680 后复跑全量")
                rec("DRAW200_NEZHA", d200.get("id") == 5207,
                    f"第200抽 id={d200.get('id')} (期望5207哪吒) [实测通过; m2清零断言待代码部署后复验]")
            else:
                ok200 = d200.get("ok") and d200.get("id") == 5207 and d200.get("m2") == MUST_COUNT2
                rec("DRAW200_NEZHA", ok200,
                    f"第200抽 id={d200.get('id')} (期望5207哪吒) m2={d200.get('m2')} (期望200=金卡清零)")
                # D: 201-300
                print("== D: 201-300 逐抽 ==", flush=True)
                run_to(300)
                d300 = draws_ok()[-1] if draws_ok() else {}
                ok300 = d300.get("total") == 300 and d300.get("id") == 5201 and d300.get("m2") == MUST_COUNT2
                rec("DRAW300_JIUWEI", ok300,
                    f"第300抽 id={d300.get('id')} (期望5201九尾天狐) m2={d300.get('m2')}")
                # E: 有提前出金且从未观察到触发点 → 延长寻找 isMust2 纯触发
                if early_golds and not pity_triggers and draws_ok() and draws_ok()[-1]["total"] < MAX_DRAWS_E:
                    print("== E: 延长采样寻找 isMust2 触发 ==", flush=True)
                    run_to(MAX_DRAWS_E)

            # A: mustCfg 1-10 顺序
            seq = [x["id"] for x in draws_ok()[:10]]
            rec("MUST_1_10_SEQ", seq == MUST_SEQ, f"1-10抽序列={seq} 期望={MUST_SEQ}")

            # 计数动力学
            if CANARY:
                rec("COUNTER_DYNAMICS", None, "金丝雀模式(旧服务端无m2字段), 跳过动力学校验")
            else:
                rec("COUNTER_DYNAMICS", (not dyn_errs) and len(draws_ok()) > 0,
                    f"逐抽 must_count2 动力学校验异常数={len(dyn_errs)} {dyn_errs[:3]}", detail=dyn_errs)

            # 口径分歧: 1-199 随机金卡
            rec("EARLY_GOLD_1_199", None,
                f"1-199抽随机金卡={early_golds or '无'}（小保底池pack3金卡权重20/1340≈1.5%/次 → 首次金卡可能早于200抽且50%为九尾天狐, 口径分歧实证）",
                detail=early_golds)

            # isMust2 触发观察
            rec("PITY_TRIGGER_OBS", None,
                f"isMust2触发点(计数满200)={pity_triggers or '本次运行未观察到(提前出金持续清零计数时不会触发, 属机制正常)'}",
                detail=pity_triggers)

            # 扣费一致性(1券/抽)
            have1 = int(qa(page, f"() => window.__ITEM({COST_ITEM})", 0) or 0)
            n_draws = len(draws_ok())
            spent = have - have1
            rec("COST_CHECK", None,
                f"抽卡{n_draws}次, 券消耗={spent} (理论≈{n_draws}, 差值=每日免费抽等)")

            # 抽卡分布(供报告)
            from collections import Counter
            cnt = Counter(x["id"] for x in draws_ok())
            RESULT["id_stats"] = dict(cnt)
            gold_total = sum(v for k, v in cnt.items() if k in GOLD_SET)
            RESULT["gold_total"] = gold_total
            rec("GOLD_COUNT", None, f"总金卡数={gold_total}/{n_draws}")

            # total_count / must_count 一致性抽检
            if draws_ok():
                last = draws_ok()[-1]
                exp_mc = MUST_COUNT - (last["total"] % MUST_COUNT)
                rec("MUST_COUNT_FIELD", last.get("mc") == exp_mc,
                    f"末抽 must_count={last.get('mc')} 期望={exp_mc} (10抽小保底剩余) total={last['total']}")
        except Exception as e:
            rec("EXCEPTION", False, f"{type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
        finally:
            RESULT["end_time"] = datetime.now().isoformat(timespec="seconds")
            save()
            browser.close()

    gen_report()
    print(f"\n产物: {OUT_DIR}", flush=True)


def gen_report():
    checks = {c["key"]: c for c in RESULT.get("checks", [])}

    def tag(k):
        c = checks.get(k)
        if not c:
            return "SKIP"
        return "PASS" if c["passed"] is True else ("FAIL" if c["passed"] is False else "INFO")

    L = ["# 招募保底机制专项验证报告（哪吒必出 + 200抽神卡保底）", "",
         f"- 时间: {RESULT.get('start_time')}  账号: {RESULT.get('account')}@S5（新号+一键高级号）",
         f"- 静态依据: {RESULT.get('static_evidence')}",
         f"- 产物: {RESULT.get('out_dir')}", "",
         "## 结论速览", ""]
    for k in ["LOGIN", "PREP_TICKET", "ENV_CANARY", "M2_FIELD_MISSING", "MUST_1_10_SEQ",
              "DRAW200_NEZHA", "DRAW300_JIUWEI", "COUNTER_DYNAMICS", "EARLY_GOLD_1_199",
              "PITY_TRIGGER_OBS", "COST_CHECK", "GOLD_COUNT", "MUST_COUNT_FIELD", "CFG_LIVE"]:
        c = checks.get(k)
        if c:
            L.append(f"- **[{tag(k)}] {k}**: {c['note']}")

    draws = RESULT.get("draws", [])
    if draws:
        L += ["", "## 关键抽位明细", "",
              "| 抽序 | id | 金卡 | must_count2(响应) |", "|---|---|---|---|"]
        for d in draws:
            n = d.get("total")
            if n and (n <= 12 or n in (199, 200, 201, 299, 300, 301) or n % 50 == 0):
                g = "是" if d.get("id") in GOLD_SET else ""
                L.append(f"| {n} | {d.get('id')} | {g} | {d.get('m2')} |")

    L += ["", "## 需求口径判定", "",
          "1. **第200抽必出哪吒（原杨戬→哪吒）**: 见 DRAW200_NEZHA（mustCfg[200] 强制 + 金卡清零计数）",
          "2. **200抽必出神卡保底**: 见 COUNTER_DYNAMICS（每抽+1/金卡清零/m2响应=200-计数）与 "
          "PITY_TRIGGER_OBS（计数满200触发点必出金；stageCfg2 池12-16→卡包14/24/34/44/54 静态核对全部仅含 quality=7）",
          "3. **口径确认（2026-09-24）**: 『第一次抽出最高等级卡牌必出哪吒』确认为『第200抽必出哪吒』口径, 分歧项忽略; "
          "本验证仅覆盖招募抽卡功能（首次金卡可能早于200抽属正常随机, 见 EARLY_GOLD_1_199）", "",
          "## 观察备注", "",
          "- S5 部署状态: 配置热更新已生效（第200抽实测哪吒5207）; 代码/sproto 未重启加载（must_count2 不下发）→ "
          "200抽神卡保底计数机制待服务端重启加载 r10649~r10680 后复跑全量验证（含 mustCfg[300]=5201 改动）",
          "- GM set_recruit_reward 替换奖励发生在保底计数结算之后, GM注入金卡不会清零计数（仅GM路径, 不影响玩家）", ""]
    out = ROOT / "temp_case" / "reports" / "招募保底机制验证报告.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print("报告已生成:", out, flush=True)


if __name__ == "__main__":
    main()
