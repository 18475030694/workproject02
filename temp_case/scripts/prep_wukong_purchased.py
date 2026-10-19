"""大圣礼包（530001）点4前置：批量准备「改版前已购买」账号（S5）。

目的：代码更新前，用旧逻辑（购买一次性发奖）造出 N 个"原已购买礼包"的账号，
供改版后验证点4「原已购买礼包的账号，更新修改后的领取情况」。

内网购买链路（RechargeMgr.ts L190-194）：非BUILD/无SDK → sendEditorCharge →
c2gs_execute_instruct(recharge_notifykey, pay_type=GM)，点一次 BtnBuy_ 即完成购买。

单账号流程（复用 harness/gm_account.py 既有函数，不重复造轮子）：
  1. 新建账号 → 登录（gm_account.login_session）
  2. 一键高级号（one_key_help_u，主线推到5000 ≫ 22关 → 礼包满足上架条件）
  3. 会话稳定期：one_key_help_u 后服务端会延迟踢线（2026-10-15 实证：重连回主城
     数秒后掉回登录页）→ 掉线自动重登，连续20s在游戏内且 lv≥8000 才算稳定
  4. 确保大圣礼包 UI 打开（已自动弹出记 auto，否则 openUI 直开；不做弹窗清理——
     清弹窗会误杀战斗UI导致掉线，首跑实证）
  5. dump 礼包文本证据 + 截图 → 点 BtnBuy_ → 以 wuKongGiftMgr.giftData == null
     （gs2c_recharge_fb_gift_down 已同步）判定购买完成
  6. best-effort 探测法宝 6049[玄]紧箍 / 6112[玄]筋斗云 到账
  7. 重登复核：礼包不再弹出、giftData 仍为 null（buy_list 已持久化）

用法：
  python temp_case/scripts/prep_wukong_purchased.py                  # 新备3个号
  python temp_case/scripts/prep_wukong_purchased.py --accounts 1     # 新备1个号
  python temp_case/scripts/prep_wukong_purchased.py --reuse 8017:8589935690 --accounts 1
      # 复用已升级账号（account:uuid，跳过建号+升级，直接买礼包），可多次 --reuse

产物：temp_case/reports/prep_wukong_purchased_<ts>/{report.json, summary.md, screenshots/}
注意：必须在【旧代码部署期间】执行；改后再购买即为新逻辑，无法复现"旧已购"状态。
"""
import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "harness"))
import e2e_login as base  # noqa: E402
import gm_account as gma  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

SVR_ID, SVR_NAME = 5, "S5"
GIFT_UI = "UIWuKongGift"

# 是否在登录页
JS_AT_LOGIN = """() => { try { return window.__qa.findByName('LoginBtn_').length > 0; } catch (e) { return false; } }"""

# 是否已进游戏可操作态（非登录页、非加载页；战斗场景也算——openUI/点击不依赖遮挡）
JS_INGAME = """() => { try {
  if (!window.__qa.isReady()) return false;
  if (window.__qa.uiActive('UILoading')) return false;
  if (window.__qa.findByName('LoginBtn_').length > 0) return false;
  return true;
} catch (e) { return false; } }"""

# 大圣礼包是否在弹（注册名 uiActive）
JS_GIFT_ACTIVE = """() => { try { return window.__qa.uiActive('""" + GIFT_UI + """'); } catch (e) { return false; } }"""

# 礼包数据状态：giftData / fbGiftMap.size
JS_GIFT_STATE = """() => { try {
  const M = window.SystemModules; const m = M && M.wuKongGiftMgr; if (!m) return { err: 'no mgr' };
  const d = m.giftData;
  return { has_gift: !!d, gift: d ? { goods_id: d.goods_id, end_time: d.end_time } : null,
           map_size: m.fbGiftMap ? m.fbGiftMap.size : null };
} catch (e) { return { err: String(e) }; } }"""

# 礼包 UI 文本 dump（标题/价格/奖励/按钮）
JS_DUMP_GIFT = """() => { try {
  const out = window.__qa.dumpUITree('""" + GIFT_UI + """');
  return out.filter(e => e.active !== false && e.text);
} catch (e) { return [{ err: String(e) }]; } }"""

# 点礼包内的购买按钮（prefab 实名 BtnBuy_，带 Button 组件，clickNode 发 Button.CLICK）
JS_CLICK_BUY = """() => { try {
  const cands = ['BtnBuy_', 'BtnBuy'];
  for (const nm of cands) {
    const paths = window.__qa.findByName(nm).filter(p => p.indexOf('""" + GIFT_UI + """') >= 0);
    if (paths.length) {
      const ok = window.__qa.clickNode(paths[0]);
      if (ok) return { ok: true, node: nm, path: paths[0] };
    }
  }
  return { ok: false, err: 'no clickable BtnBuy_ under ' + '""" + GIFT_UI + """' };
} catch (e) { return { ok: false, err: String(e) }; } }"""

# best-effort：在 soulRingMgr/itemMgr 等浅层结构里找 6049/6112 或名字
JS_PROBE_REWARDS = """() => { try {
  const M = window.SystemModules; const found = [];
  const wantNames = ['紧箍', '筋斗云'];
  const walk = (obj, depth, seen, tag) => {
    if (depth > 6 || seen.size > 20000) return;
    if (obj === null || typeof obj !== 'object') return;
    if (seen.has(obj)) return; seen.add(obj);
    for (const k in obj) {
      let v; try { v = obj[k]; } catch (e) { continue; }
      if (v === 6049 || v === 6112) found.push({ tag: tag, key: k, val: v });
      else if (typeof v === 'string' && wantNames.some(n => v.indexOf(n) >= 0) && v.length < 40) found.push({ tag: tag, key: k, name: v });
      else if (v && typeof v === 'object') walk(v, depth + 1, seen, tag);
      if (found.length > 40) return;
    }
  };
  const tryMgr = (name) => { try { const m = M[name]; if (m) walk(m, 0, new Set(), name); } catch (e) { } };
  ['soulRingMgr', 'itemMgr', 'bagMgr', 'heroMgr'].forEach(tryMgr);
  return { found: found.slice(0, 40) };
} catch (e) { return { err: String(e) }; } }"""


def attach_console(page):
    logs = []
    page.on("console", lambda m: logs.append(f"[{m.type}] {m.text[:200]}") if m.type in ("error", "warning") or "recharge" in m.text.lower() or "instruct" in m.text.lower() else None)
    return logs


def console_tail(logs, n=25):
    return logs[-n:]


def wait_ingame(page, timeout_s=150, poll=2.0):
    """等客户端进入可操作态（非登录页/加载页）。期间不做任何 UI 关闭操作。"""
    end_t = time.time() + timeout_s
    while time.time() < end_t:
        try:
            if page.evaluate(JS_INGAME):
                return True
        except Exception:
            pass
        page.wait_for_timeout(int(poll * 1000))
    return False


def stabilize_session(page, account, need_lv=8000, steady_s=20, max_wait=240):
    """升级后等待会话稳定：容忍服务端延迟踢线（掉回登录页则重新登录），
    连续 steady_s 秒处于游戏内且等级达标才算稳定。返回 (ok, kicks, role)。"""
    start = time.time()
    ingame_since = None
    kicks = 0
    role = {}
    while time.time() - start < max_wait:
        try:
            at_login = page.evaluate(JS_AT_LOGIN)
            in_game = (not at_login) and page.evaluate(JS_INGAME)
        except Exception:
            at_login, in_game = True, False
        if at_login:
            ingame_since = None
            kicks += 1
            print(f"  [stabilize] 掉回登录页，重登 (kick#{kicks})")
            try:
                gma.login_session(page, account, SVR_ID, SVR_NAME)
                ingame_since = time.time()
            except Exception as e:  # noqa: BLE001
                print(f"  [stabilize] 重登失败: {e}")
            page.wait_for_timeout(3000)
            continue
        if in_game:
            now = time.time()
            if ingame_since is None:
                ingame_since = now
            elif now - ingame_since >= steady_s:
                try:
                    role = gma.read_role(page)
                except Exception as e:  # noqa: BLE001
                    print(f"  [stabilize] 读档失败: {e}")
                    role = {}
                lv = role.get("lv")
                if isinstance(lv, (int, float)) and lv >= need_lv:
                    return True, kicks, role
                print(f"  [stabilize] 等级未达标 lv={lv}，继续等待")
                ingame_since = now  # 等级还没生效，重新计时
            page.wait_for_timeout(2000)
        else:
            ingame_since = None
            page.wait_for_timeout(2000)
    return False, kicks, role


def ensure_gift_ui(page, timeout_s=30):
    """确保大圣礼包 UI 打开：先看是否已自动弹出，否则 openUI 直开（不依赖 autoOpen 队列）。"""
    end_t = time.time() + timeout_s
    while time.time() < end_t:
        try:
            if page.evaluate(JS_GIFT_ACTIVE):
                return True, "auto"
        except Exception:
            pass
        try:
            if page.evaluate("() => window.__qa.openUI('" + GIFT_UI + "')"):
                page.wait_for_timeout(1500)
                if page.evaluate(JS_GIFT_ACTIVE):
                    return True, "openUI"
        except Exception:
            pass
        page.wait_for_timeout(2000)
    return False, "open-fail"


def wait_purchase_done(page, timeout_s=40):
    st = {}
    end_t = time.time() + timeout_s
    while time.time() < end_t:
        try:
            st = page.evaluate(JS_GIFT_STATE)
            if st.get("has_gift") is False and not st.get("err"):
                return True, st
        except Exception:
            pass
        page.wait_for_timeout(1000)
    return False, st


def prep_one_account(pw_browser, idx, out_dir, reuse=None):
    rec = {"idx": idx, "server": f"{SVR_ID}/{SVR_NAME}",
           "start": datetime.now().isoformat(timespec="seconds"), "ok": False}
    ctx = pw_browser.new_context(viewport={"width": 1280, "height": 720})
    page = ctx.new_page()
    logs = attach_console(page)
    try:
        if reuse:
            account, uuid0 = reuse
            rec["account"], rec["uuid"] = account, uuid0
            rec["reused"] = True
            print(f"\n========== 账号#{idx} {account}（复用已升级号）==========")
            gma.login_session(page, account, SVR_ID, SVR_NAME)
            role = gma.read_role(page)
            lv = role.get("lv")
            if not (isinstance(lv, (int, float)) and lv >= 8000):
                raise RuntimeError(f"复用账号等级异常 lv={lv}")
            rec["after_upgrade"] = role
        else:
            account = base._gen_new_account()
            rec["account"] = account
            print(f"\n========== 账号#{idx} {account} ==========")
            # 1. 登录（新号 lv1）
            gma.login_session(page, account, SVR_ID, SVR_NAME)
            role0 = gma.read_role(page)
            rec["before"] = role0
            base.screenshot(page, out_dir, f"{idx:02d}_01_new_account")
            print(f"[role0] {json.dumps(role0, ensure_ascii=False)}")

            # 2. 一键高级号（client 通道，失败自动回退 esc），最多重试2次
            rec["after_upgrade"] = {}
            for attempt in range(1, 3):
                gma.one_key_help_u(page, via="client")
                gma.wait_relogin(page, account, SVR_ID, SVR_NAME)
                ok, kicks, role1 = stabilize_session(page, account)
                rec["after_upgrade"] = role1
                rec["kicks"] = rec.get("kicks", 0) + kicks
                print(f"[role1] attempt{attempt} kicks={kicks} {json.dumps(role1, ensure_ascii=False)}")
                lv = role1.get("lv")
                if ok and isinstance(lv, (int, float)) and lv >= 8000:
                    break
                print(f"[upgrade] 第{attempt}次未生效，重试")
            rec["uuid"] = rec["after_upgrade"].get("uuid")
            lv = rec["after_upgrade"].get("lv")
            if not (isinstance(lv, (int, float)) and lv >= 8000):
                raise RuntimeError(f"一键高级号未生效 lv={lv}")
        base.screenshot(page, out_dir, f"{idx:02d}_02_after_upgrade")

        # 3. 确保礼包 UI 打开（不做弹窗清理，避免误杀战斗UI）
        popped, via = ensure_gift_ui(page)
        rec["popup"] = {"popped": popped, "via": via}
        if not popped:
            base.screenshot(page, out_dir, f"{idx:02d}_99_no_popup")
            raise RuntimeError(f"大圣礼包 UI 打开失败: {via}")
        page.wait_for_timeout(1500)
        rec["popup_texts"] = page.evaluate(JS_DUMP_GIFT)[:40]
        base.screenshot(page, out_dir, f"{idx:02d}_03_gift_popup")
        print(f"[popup] via={via}, texts={len(rec['popup_texts'])}")

        # 4. 点购买（内网 c2gs_execute_instruct 直接购买）
        rec["buy_click"] = page.evaluate(JS_CLICK_BUY)
        print(f"[buy] click={rec['buy_click']}")
        if not rec["buy_click"].get("ok"):
            base.screenshot(page, out_dir, f"{idx:02d}_99_click_fail")
            raise RuntimeError(f"点击购买失败: {rec['buy_click']}")

        # 5. 等购买完成（giftData → null）
        page.wait_for_timeout(2000)
        done, st = wait_purchase_done(page)
        rec["purchase_state"] = st
        rec["server_time"] = page.evaluate("() => { try { return window.__qa.getServerTime(); } catch (e) { return null; } }")
        base.screenshot(page, out_dir, f"{idx:02d}_04_after_buy")
        print(f"[buy] done={done} state={st} server_time={rec['server_time']}")
        if not done:
            rec["console_tail"] = console_tail(logs)
            raise RuntimeError(f"购买未完成（giftData 未清空）: {st}")

        # 6. best-effort 奖励到账探测
        rec["rewards_probe"] = page.evaluate(JS_PROBE_REWARDS)
        print(f"[rewards] {json.dumps(rec['rewards_probe'], ensure_ascii=False)[:300]}")

        # 7. 重登复核：不再弹礼包、giftData 仍为 null
        page.reload(wait_until="domcontentloaded", timeout=60_000)
        base.wait_qa_bridge(page)
        page.wait_for_timeout(6000)
        gma.login_session(page, account, SVR_ID, SVR_NAME)
        ok2, kicks2, _ = stabilize_session(page, account, steady_s=8, max_wait=120)
        ever_popped = False
        end_t = time.time() + 25
        while time.time() < end_t:
            if page.evaluate(JS_GIFT_ACTIVE):
                ever_popped = True
                break
            page.wait_for_timeout(2000)
        rec["relogin"] = {"gift_popped_again": ever_popped,
                          "state": page.evaluate(JS_GIFT_STATE)}
        base.screenshot(page, out_dir, f"{idx:02d}_05_relogin_clean")
        print(f"[relogin] popped_again={ever_popped} state={rec['relogin']['state']}")
        clean = (not ever_popped) and rec["relogin"]["state"].get("has_gift") is False
        rec["ok"] = bool(done and clean)
        rec["note"] = "PREP_OK" if rec["ok"] else ("PARTIAL: bought but relogin-abnormal" if done else "FAIL")
    except Exception as e:  # noqa: BLE001
        rec["error"] = str(e)
        rec["note"] = "FAIL"
        rec["console_tail"] = console_tail(logs)
        print(f"[flow] ❌ {e}")
        try:
            base.screenshot(page, out_dir, f"{idx:02d}_99_error")
        except Exception:
            pass
    finally:
        rec["end"] = datetime.now().isoformat(timespec="seconds")
        ctx.close()
    return rec


def main():
    ap = argparse.ArgumentParser(description="大圣礼包点4前置：批量准备改版前已购账号")
    ap.add_argument("--accounts", type=int, default=0, help="新建账号数量（默认0，仅用 --reuse）")
    ap.add_argument("--reuse", action="append", default=[], metavar="ACCOUNT:UUID",
                    help="复用已升级账号（可多次）")
    ap.add_argument("--headed", action="store_true", help="有头浏览器")
    args = ap.parse_args()

    reuse_list = []
    for r in args.reuse:
        acc, _, uid = r.partition(":")
        reuse_list.append((acc, uid or None))

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = HERE.parent / "reports" / f"prep_wukong_purchased_{ts}"
    (out_dir / "screenshots").mkdir(parents=True, exist_ok=True)
    print(f"[out] {out_dir}")

    report = {"time": ts, "server": f"{SVR_ID}/{SVR_NAME}",
              "purpose": "大圣礼包(530001)改版前已购账号", "accounts": []}
    hl = False if args.headed else base.HEADLESS
    idx = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=hl)
        for acc, uid in reuse_list:
            idx += 1
            rec = prep_one_account(browser, idx, out_dir, reuse=(acc, uid))
            report["accounts"].append(rec)
            print(f"[summary] #{idx} {acc} -> {rec['note']}")
        for _ in range(args.accounts):
            idx += 1
            rec = prep_one_account(browser, idx, out_dir)
            report["accounts"].append(rec)
            print(f"[summary] #{idx} {rec['account']} -> {rec['note']}")
        browser.close()

    ok_list = [a for a in report["accounts"] if a.get("ok")]
    part_list = [a for a in report["accounts"] if a.get("note", "").startswith("PARTIAL")]
    report["ok_count"] = len(ok_list)
    report["partial_count"] = len(part_list)
    (out_dir / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# 大圣礼包（530001）改版前已购账号准备报告",
        "",
        f"- 时间: {ts}  服务器: {SVR_ID}/{SVR_NAME}",
        f"- 结果: 成功 {len(ok_list)} / 部分成功 {len(part_list)} / 共 {len(report['accounts'])}",
        "",
        "| # | 账号 | uuid | 等级 | 购买 | 重登复核 | 备注 |",
        "|---|---|---|---|---|---|---|",
    ]
    for a in report["accounts"]:
        lines.append(f"| {a['idx']} | {a['account']} | {a.get('uuid') or '-'} | {a.get('after_upgrade', {}).get('lv', '-')} "
                     f"| {'✅' if a.get('purchase_state', {}).get('has_gift') is False else '❌'} "
                     f"| {'✅' if a.get('relogin', {}).get('gift_popped_again') is False else '⚠️'} | {a.get('note')} |")
    lines += ["", "## 使用说明", "",
              "- 以上账号已在旧代码下完成 530001 购买（旧逻辑一次性发奖）。", "- 改版后直接用于点4测试：登录验证领取情况。", ""]
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"\n===== 汇总: 成功 {len(ok_list)} / 部分 {len(part_list)} / 共 {len(report['accounts'])} =====")
    for a in report["accounts"]:
        print(f"  #{a['idx']} account={a['account']} uuid={a.get('uuid')} -> {a.get('note')}")
    print(f"[out] {out_dir / 'summary.md'}")
    sys.exit(0 if len(ok_list) == len(report["accounts"]) and len(ok_list) > 0 else 1)


if __name__ == "__main__":
    main()
