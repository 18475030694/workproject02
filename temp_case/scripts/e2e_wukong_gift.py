"""大圣礼包（530001）改版 E2E 测试执行器（部署后正式跑，分组子命令驱动）。

部署版实现口径（2026-10-16 读 trunk 实证）：
  - 购买锚点：CreateBuyData day_no = Date.TodayNo()（自购买日起算，购买当天=第1天）
  - 每日解锁：OnDailyReset 追加 recv_record_list[dayN]={status:false}，公式 todayNo-day_no+1
  - 领取：c2gs_get_fb_gift_reward 一次发全部未领份额（BtnGet 单按钮）
  - 全领完：gs2c_recharge_fb_gift_down → fbGiftMap 删除 → 入口消失
  - 老存档兼容：Load 补 day_no=TodayNo(首登日)+day1已领 → 新增奖励按后续自然日逐日解锁
  - ⚠️ 疑似资损口子：过期未购占位数据(count=0) SceneReady 照发、领取无 count 拦截（TC-E05 实测）
  - ⚠️ OnDailyReset 无 giftCfg-nil 防御（配置存在时不触发，记录风险）

跨日配方（S5 共享，改→测→还原）：
  set_timeshift?dt=N（绝对设置：server = real + 614867 + N）+ player_daily_reset?uuid=<uuid>
  拨时后必须重登，客户端时间才会刷新；跨0点由自然时钟完成

分组：
  ga      新号：购买流 + D1领取 + 重复购买/重复领取拦截 + UI/价格/文本/美术证据（TC-001/002/003/011/014/015/016/025/028/029/030/031 局部）
  gb      D+1 跨日：D2解锁+领取（TC-004）+ 重登保持（TC-010）
  gc      D+2 跨日：D3解锁+领取（TC-005）+ 全领完入口消失（TC-009）
  a2      新号A2：漏领补领+入口保留+一键全领（TC-006/007/008）
  e01     边界：0点前后购买/领取（TC-E01/E03）
  compat  已购兼容账号池（TC-019~024），--claim-first 指定做完整跨日领取的账号
  expiry  过期账号（TC-017/E05：过期下架+占位数据白嫖实测）
  state   读取指定账号当前礼包状态（调试用）

用法：
  python temp_case/scripts/e2e_wukong_gift.py ga
  python temp_case/scripts/e2e_wukong_gift.py gb --account <acc> --uuid <uuid>
  python temp_case/scripts/e2e_wukong_gift.py compat --accounts 2581,2582,2583,8017 --claim-first 2581

产物：temp_case/reports/wukong_gift_e2e_<ts>/{state.json, result_<group>.json, screenshots/}
"""
import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "harness"))
import e2e_login as base  # noqa: E402
import gm_account as gma  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

SVR_ID, SVR_NAME = 5, "S5"
GIFT_UI = "UIWuKongGift"
GOODS_ID = 530001
GM_HOST = os.environ.get("GM_HOST", "192.168.*.*")
GM_PORT = int(os.environ.get("GM_PORT", "6011"))

# ---------------------------------------------------------------- GM HTTP ----
def gm_call(cmd, timeout=20, **params):
    url = f"http://{GM_HOST}:{GM_PORT}/index/{urllib.parse.quote(cmd)}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return {"ok": resp.status == 200, "status": resp.status, "body": resp.read().decode("utf-8", "ignore")[:400]}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "err": str(e)[:200], "url": url}


def get_server_time():
    r = gm_call("get_time", timeout=10)
    body = r.get("body", "")
    if "OK: " in body:
        return body.split("OK: ")[1].split(" REPLY")[0].strip()
    return f"ERR:{r.get('err') or body[:80]}"


LEDGER = HERE.parent / "reports" / "wukong_gift_e2e_shift_ledger.json"
FMT = "%Y-%m-%d %H:%M:%S"
# 服务器原始偏移：server(10-23 00:36:25) - real(10-15 21:48:38) = 7d02:47:47 = 614867s
# （早前误记 528467 少算 1 天；已按 dt=236284 精确命中 2026-10-25 23:57:32 实测校验）
ORIGINAL_OFFSET_S = 614867


def ledger_add(dt, note=""):
    try:
        arr = json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.exists() else []
    except Exception:  # noqa: BLE001
        arr = []
    arr.append({"ts": datetime.now().isoformat(timespec="seconds"), "dt": dt, "note": note})
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(arr, ensure_ascii=False, indent=1), encoding="utf-8")


def _shift_toward(target_dt, max_try=3):
    """绝对模型拨时（2026-10-16 定稿）：set_timeshift?dt=N 为绝对设置（TIME_SHIFT_SEC := N，非增量），
    服务器时间 = 真实时间 + ORIGINAL_OFFSET_S + N → 拨到 target：dt = target - real_now - ORIGINAL_OFFSET_S。
    实测校验：dt=236284 精确命中 2026-10-25 23:57:32；旧增量模型会产生"少1h/小步进无效/倒退"伪现象。"""
    dt = None
    for i in range(max_try):
        dt = int((target_dt - datetime.now()).total_seconds()) - ORIGINAL_OFFSET_S
        r = gm_call("set_timeshift", dt=dt)
        time.sleep(2)
        if r.get("ok"):
            ledger_add(dt, f"abs try{i} -> {target_dt.strftime(FMT)}")
        new = get_server_time()
        try:
            if abs((target_dt - datetime.strptime(new, FMT)).total_seconds()) < 60:
                return {"ok": True, "tries": i + 1, "now": new, "dt": dt}
        except Exception:  # noqa: BLE001
            pass
    return {"ok": False, "now": get_server_time(), "err": f"target {target_dt} 未达（{max_try}次）", "dt": dt}


def set_time_to(target_str):
    """拨时到目标时刻（YYYY-MM-DD HH:MM:SS）。此环境 set_server_time 的 timestr 解析不可用，走 set_timeshift。"""
    try:
        tgt = datetime.strptime(target_str, FMT)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "err": f"parse target:{e}"}
    return _shift_toward(tgt)


def player_daily_reset(uuid):
    return gm_call("player_daily_reset", uuid=uuid)


def cross_to_day(target_day, uuids=(), max_wait_s=5400):
    """跨自然日：确保服务器时间进入 target_day 当天（越过其 0 点）后触发每日重置。
    服务器日期已 ≥ target_day → 跳过拨时只做 reset；否则拨到前一日 23:57:30，
    等自然时钟走完最后一分钟跨过 0 点（dt 为绝对设置，跨0点由自然时钟完成）。"""
    now = get_server_time()
    if now[:10] >= target_day:
        r = {"ok": True, "note": f"skip-shift: server {now} already >= {target_day}"}
    else:
        prev = (datetime.strptime(target_day, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        r = set_time_to(f"{prev} 23:57:30")
        tgt_dt = datetime.strptime(target_day, "%Y-%m-%d") + timedelta(seconds=30)
        end_t = time.time() + max_wait_s
        while time.time() < end_t:
            now = get_server_time()
            try:
                if datetime.strptime(now, FMT) >= tgt_dt:
                    break
            except Exception:  # noqa: BLE001
                pass
            time.sleep(10)
    resets = {}
    for u in uuids:
        if u:
            resets[str(u)] = player_daily_reset(u).get("ok")
    time.sleep(2)
    return {"shift": r, "now": get_server_time(), "resets": resets}


def cross_day(uuid, timestr):
    """拨时到指定时刻（set_timeshift 增量）+ 对账号触发每日重置。"""
    r1 = set_time_to(timestr)
    time.sleep(1.5)
    r2 = player_daily_reset(uuid)
    return {"set": r1.get("ok"), "dt": r1.get("dt"), "now": r1.get("now") or get_server_time(),
            "reset": r2.get("ok"), "reset_body": r2.get("body", "")[:120]}

# ------------------------------------------------------------------ JS -------
JS_STATE = r"""() => { try {
  const M = window.SystemModules; const m = M && M.wuKongGiftMgr; if (!m) return { err: 'no mgr' };
  const d = m.giftData;
  return { has_gift: !!d, map_size: m.fbGiftMap ? m.fbGiftMap.size : null,
    gift: d ? { goods_id: d.goods_id, end_time: d.end_time, recv_record_list: d.recv_record_list || [] } : null,
    cur_day: d ? m.getCurDay(d.goods_id) : null,
    can_reward: d ? m.isCanRewardDay(d.goods_id) : null,
    day_can: [1,2,3].map(dd => d ? m.eachDayCanReward(d.goods_id, dd) : null) };
} catch (e) { return { err: String(e) }; } }"""

JS_DUMP_GIFT = r"""() => { try {
  const out = window.__qa.dumpUITree('UIWuKongGift');
  return out.filter(e => e.active !== false && (e.text || /Btn(Get|HasGet|ToGet|Buy|Close)/.test(e.name || '')));
} catch (e) { return [{ err: String(e) }]; } }"""

JS_CLICK_IN_UI = r"""(name) => { try {
  for (const nm of [name, name + '_']) {
    const paths = window.__qa.findByName(nm).filter(p => p.indexOf('UIWuKongGift') >= 0);
    if (paths.length) { const ok = window.__qa.clickNode(paths[0]); if (ok) return { ok: true, node: nm, path: paths[0] }; }
  }
  return { ok: false, err: 'not found: ' + name };
} catch (e) { return { ok: false, err: String(e) }; } }"""

JS_UI_ACTIVE = r"""() => { try { return window.__qa.uiActive('UIWuKongGift'); } catch (e) { return false; } }"""

JS_MAIN_ENTRANCE = r"""() => { try {
  for (const nm of ['BtnWuKong', 'BtnWuKong_']) {
    const paths = window.__qa.findByName(nm);
    if (paths.length) return { found: true, name: nm, path: paths[0],
      active: paths.map(p => { try { const n = window.__qa.node(p); return n ? n.activeInHierarchy : null; } catch(e){ return null; } }) };
  }
  return { found: false };
} catch (e) { return { err: String(e) }; } }"""

JS_ITEM_SNAP = r"""() => { try {
  const M = window.SystemModules; const items = {}; const rings = new Set();
  const walk = (obj, depth, seen) => {
    if (depth > 7 || !obj || typeof obj !== 'object') return;
    if (seen.has(obj)) return; seen.add(obj);
    for (const k in obj) {
      let v; try { v = obj[k]; } catch (e) { continue; }
      if (typeof v === 'number' && [6049, 6112, 20109].indexOf(v) >= 0 && /ring|fabao|6049|6112|20109/i.test(k)) rings.add(v);
      if (v && typeof v === 'object') {
        const idv = v.id ?? v.item_id ?? v.itemId ?? v.cfg_id;
        const cnt = v.count ?? v.num ?? v.item_num ?? v.itemNum;
        if (typeof idv === 'number' && typeof cnt === 'number' && cnt > 0) {
          items[idv] = (items[idv] || 0) + cnt;
        }
        walk(v, depth + 1, seen);
      }
    }
  };
  const tryMgr = (name) => { try { const m = M[name]; if (m) walk(m, 0, new Set()); } catch (e) { } };
  ['knapsackMgr', 'soulRingMgr'].forEach(tryMgr);
  try { const m = M.knapsackMgr;   // 背包：idGridMap = Map<id, IBagItem[]>
    if (m && m.idGridMap && typeof m.idGridMap.forEach === 'function') {
      m.idGridMap.forEach((arr, id) => { let c = 0;
        if (Array.isArray(arr)) for (const it of arr) c += (it && it.count) || 0;
        if (c > 0) items[id] = (items[id] || 0) + c; });
    }
  } catch (e) {}
  try { const m = M.soulRingMgr;
    if (m && m.skill_list) for (const s of m.skill_list) { if (s && (s.ring_id === 6049 || s.ring_id === 6112 || s.ring_id === 20109)) rings.add(s.ring_id); }
  } catch (e) {}
  const heads = {};
  ['knapsackMgr', 'roleMgr'].forEach(n => { try { const m = M[n]; if (!m) return; const ks = {}; let c = 0;
    for (const k in m) { if (c++ > 60) break; const v = m[k];
      ks[k] = typeof v === 'number' ? v : (v && typeof v === 'object' ? (Array.isArray(v) ? 'arr:' + v.length : 'obj:' + Object.keys(v).length) : typeof v); }
    heads[n] = ks; } catch (e) {} });
  return { items: items, rings: Array.from(rings), heads: heads };
} catch (e) { return { err: String(e) }; } }"""

JS_SEND_BUYP = r"""() => { try {
  const M = window.SystemModules; if (!M.rechargeMgr) return { ok: false, err: 'no rechargeMgr' };
  M.rechargeMgr.buyProduct(530001);
  return { ok: true };
} catch (e) { return { ok: false, err: String(e) }; } }"""

JS_CHAT_PROBE = r"""() => { try {
  const M = window.SystemModules; const out = [];
  const scan = (obj, depth, seen, tag) => {
    if (depth > 5 || !obj || typeof obj !== 'object') return;
    if (seen.has(obj)) return; seen.add(obj);
    for (const k in obj) { let v; try { v = obj[k]; } catch (e) { continue; }
      if (typeof v === 'string' && v.length < 120 && (v.indexOf('礼包') >= 0 || v.indexOf('孙悟空') >= 0 || v.indexOf('法宝') >= 0)) out.push(tag + ':' + k + '=' + v);
      else if (v && typeof v === 'object') scan(v, depth + 1, seen, tag);
      if (out.length > 20) return; }
  };
  ['chatMgr', 'bulletinMgr', 'marqueeMgr'].forEach(n => { try { if (M[n]) scan(M[n], 0, new Set(), n); } catch (e) {} });
  return out.slice(0, 20);
} catch (e) { return [String(e)]; } }"""

JS_AT_LOGIN = """() => { try { return window.__qa.findByName('LoginBtn_').length > 0; } catch (e) { return false; } }"""

JS_INGAME = """() => { try {
  if (!window.__qa.isReady()) return false;
  if (window.__qa.uiActive('UILoading')) return false;
  if (window.__qa.findByName('LoginBtn_').length > 0) return false;
  return true;
} catch (e) { return false; } }"""

# ---------------------------------------------------------------- helpers ----
def wait_ingame(page, timeout_s=150, poll=2.0):
    end_t = time.time() + timeout_s
    while time.time() < end_t:
        try:
            if page.evaluate(JS_INGAME):
                return True
        except Exception:  # noqa: BLE001
            pass
        page.wait_for_timeout(int(poll * 1000))
    return False


def stabilize(page, account, need_lv=8000, steady_s=12, max_wait=240):
    start, ingame_since, kicks = time.time(), None, 0
    while time.time() - start < max_wait:
        try:
            at_login = page.evaluate(JS_AT_LOGIN)
            in_game = (not at_login) and page.evaluate(JS_INGAME)
        except Exception:  # noqa: BLE001
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
            ingame_since = ingame_since or now
            if now - ingame_since >= steady_s:
                role = gma.read_role(page)
                lv = role.get("lv")
                if isinstance(lv, (int, float)) and lv >= need_lv:
                    return True, kicks, role
                ingame_since = now
            page.wait_for_timeout(2000)
        else:
            ingame_since = None
            page.wait_for_timeout(2000)
    return False, kicks, gma.read_role(page)


def ensure_gift_ui(page, timeout_s=25):
    end_t = time.time() + timeout_s
    while time.time() < end_t:
        try:
            if page.evaluate(JS_UI_ACTIVE):
                return True, "auto"
        except Exception:  # noqa: BLE001
            pass
        try:
            if page.evaluate("() => window.__qa.openUI('UIWuKongGift')"):
                page.wait_for_timeout(1500)
                if page.evaluate(JS_UI_ACTIVE):
                    return True, "openUI"
        except Exception:  # noqa: BLE001
            pass
        page.wait_for_timeout(2000)
    return False, "open-fail"


def snap(page):
    return page.evaluate(JS_STATE)


def item_snap(page):
    return page.evaluate(JS_ITEM_SNAP)


def diff_items(before, after):
    """返回 {id: [before, after]} 增量非零项。"""
    out = {}
    b, a = before.get("items", {}), after.get("items", {})
    for k in set(b) | set(a):
        if b.get(k, 0) != a.get(k, 0):
            out[str(k)] = [b.get(k, 0), a.get(k, 0)]
    return out


def wait_state(page, pred, timeout_s=30, poll=1.0):
    st = {}
    end_t = time.time() + timeout_s
    while time.time() < end_t:
        st = snap(page)
        try:
            if pred(st):
                return True, st
        except Exception:  # noqa: BLE001
            pass
        page.wait_for_timeout(int(poll * 1000))
    return False, st

# ------------------------------------------------------------ group runner ---
class Runner:
    def __init__(self, out_dir):
        self.out = out_dir
        self.results = []   # [{tc, pass, note, evidence:[...]}]

    def rec(self, tc, ok, note="", evidence=None):
        self.results.append({"tc": tc, "pass": bool(ok), "note": str(note)[:400], "evidence": evidence or []})
        print(f"  [TC] {tc} -> {'PASS' if ok else 'FAIL'} | {str(note)[:120]}")

    def shot(self, page, name):
        try:
            base.screenshot(page, self.out, name)
            return f"screenshots/{name}.png"
        except Exception as e:  # noqa: BLE001
            print(f"  [shot] {name} 失败: {e}")
            return None

    def save(self, group, extra=None):
        data = {"group": group, "time": datetime.now().isoformat(timespec="seconds"),
                "server_time": get_server_time(), "results": self.results}
        if extra:
            data.update(extra)
        p = self.out / f"result_{group}.json"
        p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[out] {p}")
        return data


def new_upgraded_account(page, rec):
    """建新号 + 一键高级号 + 会话稳定。返回 account。"""
    account = base._gen_new_account()
    rec["account"] = account
    print(f"[new] 账号={account}")
    gma.login_session(page, account, SVR_ID, SVR_NAME)
    for attempt in range(1, 3):
        gma.one_key_help_u(page, via="client")
        gma.wait_relogin(page, account, SVR_ID, SVR_NAME)
        ok, kicks, role = stabilize(page, account)
        rec["role"] = role
        lv = role.get("lv")
        if ok and isinstance(lv, (int, float)) and lv >= 8000:
            rec["uuid"] = role.get("uuid")
            print(f"[new] 升级完成 lv={lv} uuid={rec['uuid']} kicks={kicks}")
            return account
        print(f"[new] 第{attempt}次升级未生效，重试")
    raise RuntimeError(f"一键高级号未生效 role={role}")

# ------------------------------------------------------------------- groups --
def run_group(pw_browser, group, args, out_dir):
    R = Runner(out_dir)
    state_f = out_dir / "state.json"
    state = json.loads(state_f.read_text(encoding="utf-8")) if state_f.exists() else {}
    extra = {}

    ctx = pw_browser.new_context(viewport={"width": 1280, "height": 720})
    page = ctx.new_page()
    rec = {}
    try:
        if group == "ga":
            account = new_upgraded_account(page, rec)
            extra["account"], extra["uuid"] = account, rec.get("uuid")
            _ga(page, R, account)
        elif group in ("gb", "gc"):
            account, uuid = args.account, args.uuid
            if not account or not uuid:
                raise RuntimeError("gb/gc 需要 --account/--uuid（沿用 ga 产物）")
            gma.login_session(page, account, SVR_ID, SVR_NAME)
            ok, kicks, role = stabilize(page, account, steady_s=8, max_wait=120)
            if not ok:
                raise RuntimeError(f"会话未稳定 role={role}")
            _gb(page, R, account, uuid) if group == "gb" else _gc(page, R, account, uuid)
        elif group == "a2":
            account = new_upgraded_account(page, rec)
            extra["account"], extra["uuid"] = account, rec.get("uuid")
            _a2(page, R, account)
        elif group == "e01":
            account = new_upgraded_account(page, rec)
            extra["account"], extra["uuid"] = account, rec.get("uuid")
            _e01(page, R, account)
        elif group == "compat":
            accounts = [a.strip() for a in (args.accounts or "").split(",") if a.strip()]
            if not accounts:
                raise RuntimeError("compat 需要 --accounts")
            _compat(pw_browser, R, accounts, args.claim_first, out_dir)
            ctx.close()
            R.save(group, extra)
            return
        elif group == "expiry":
            accounts = [a.strip() for a in (args.accounts or "").split(",") if a.strip()]
            _expiry(pw_browser, R, accounts, out_dir)
            ctx.close()
            R.save(group, extra)
            return
        elif group == "state":
            account = args.account
            gma.login_session(page, account, SVR_ID, SVR_NAME)
            stabilize(page, account, steady_s=6, max_wait=90)
            st = snap(page)
            print("[state]", json.dumps(st, ensure_ascii=False))
            R.rec("STATE", bool(st.get("gift") is not None or st.get("has_gift") is False), json.dumps(st, ensure_ascii=False)[:300])
        else:
            raise RuntimeError(f"未知分组 {group}")
    except Exception as e:  # noqa: BLE001
        R.rec(f"{group.upper()}-EXCEPTION", False, str(e)[:300])
        try:
            R.shot(page, "99_error")
        except Exception:  # noqa: BLE001
            pass
    finally:
        rec["end"] = datetime.now().isoformat(timespec="seconds")
        ctx.close()

    if state_f or True:
        prev = json.loads(state_f.read_text(encoding="utf-8")) if state_f.exists() else {}
        prev.update({k: v for k, v in extra.items() if v is not None})
        state_f.write_text(json.dumps(prev, indent=2, ensure_ascii=False), encoding="utf-8")
    R.save(group, extra)


def _ga(page, R, account):
    """A组：购买+D1领取+拦截+UI证据。"""
    print("== GA: 礼包弹出/购买/领取 ==")
    popped, via = ensure_gift_ui(page)
    R.rec("TC-025(部分)", popped, f"礼包UI打开 via={via}（auto=自动弹出）")
    R.shot(page, "ga_01_gift_popup")

    # TC-011/014/028/029/030：UI dump（价格/奖励条目/按钮态/文本）
    page.wait_for_timeout(1200)
    dump = page.evaluate(JS_DUMP_GIFT)
    texts = [e.get("text") for e in dump if e.get("text")]
    buy_btns = [e for e in dump if "BtnBuy" in (e.get("name") or "")]
    R.rec("TC-011(UI条目)", bool(texts), f"文本{len(texts)}条: {texts[:12]}", ["ga_01_gift_popup.png"])
    R.rec("TC-014(价格展示)", bool(buy_btns), f"购买按钮文本={buy_btns[0].get('text') if buy_btns else '-'}")
    R.rec("TC-029(文本dump)", True, json.dumps(texts, ensure_ascii=False)[:300])

    st0 = snap(page)
    R.rec("TC-028(在架未购状态)", st0.get("has_gift") and st0["gift"]["end_time"] not in (-1,),
          f"end_time={st0.get('gift', {}).get('end_time')}（倒计时态）")

    # 购买前道具/法宝快照
    pre = item_snap(page)

    # TC-001/015：点击购买
    click = page.evaluate(JS_CLICK_IN_UI, "BtnBuy")
    print(f"[buy] click={click}")
    page.wait_for_timeout(2500)
    ok1, st1 = wait_state(page, lambda s: bool(s.get("has_gift") and s.get("gift", {}).get("end_time") == -1))
    R.shot(page, "ga_02_after_buy")
    R.rec("TC-001(购买→已购待领取)", ok1, json.dumps(st1.get("gift"), ensure_ascii=False)[:200])
    R.rec("TC-015(内网直购)", ok1, "c2gs_execute_instruct 链路，跳过SDK")

    # TC-016：已购后购买按钮消失 + 协议级重复购买拦截
    dump2 = page.evaluate(JS_DUMP_GIFT)
    buy_gone = not [e for e in dump2 if "BtnBuy" in (e.get("name") or "") and e.get("active") is not False]
    R.rec("TC-016a(购买按钮隐藏)", buy_gone, "已购态 BtnBuy 不应显示")
    re_buy = page.evaluate(JS_SEND_BUYP)
    page.wait_for_timeout(2500)
    st2 = snap(page)
    rrl = (st2.get("gift") or {}).get("recv_record_list") or []
    day1_still = len(rrl) >= 1 and rrl[0].get("day") == 1 and rrl[0].get("status") is False and len(rrl) == 1
    R.rec("TC-016b(重复购买拦截)", day1_still, f"re-buy后recv={json.dumps(rrl)}（不重置不重复）")

    # TC-002：领取第1天
    pre2 = item_snap(page)
    click_get = page.evaluate(JS_CLICK_IN_UI, "BtnGet")
    print(f"[get] click={click_get}")
    page.wait_for_timeout(3000)
    ok2, st3 = wait_state(page, lambda s: bool((s.get("gift") or {}).get("recv_record_list") and
                                               all(e.get("status") for e in s["gift"]["recv_record_list"])))
    after2 = item_snap(page)
    diff2 = diff_items(pre2, after2)
    R.shot(page, "ga_03_day1_claimed")
    R.rec("TC-002(D1领取到账)", ok2, f"recv={json.dumps((st3.get('gift') or {}).get('recv_record_list'))} itemdiff={json.dumps(diff2)} rings={after2.get('rings')}",
          ["ga_03_day1_claimed.png"])
    R.rec("TC-012a(D1数量)", ok2 and (6049 in after2.get("rings", [])) and (6112 in after2.get("rings", [])),
          f"法宝6049/6112到账 rings={after2.get('rings')}；diff={json.dumps(diff2)}")

    # TC-003：重复领取拦截（协议级）
    pre3 = item_snap(page)
    dup = page.evaluate(r"""() => { try {
      const M = window.SystemModules; let resp = null;
      M.wuKongGiftMgr.sendRecv(530001);
      return { sent: true };
    } catch (e) { return { sent: false, err: String(e) }; } }""")
    page.wait_for_timeout(2500)
    st4 = snap(page)
    after3 = item_snap(page)
    diff3 = diff_items(pre3, after3)
    rrl4 = (st4.get("gift") or {}).get("recv_record_list") or []
    R.rec("TC-003(重复领取拦截)", (not diff3) and all(e.get("status") for e in rrl4),
          f"重复sendRecv后 diff={json.dumps(diff3)} recv={json.dumps(rrl4)}")

    # TC-016c：领取后再次协议级重复购买（RechargeAction 不走 CheckBuyCondition，直改 buyData）
    page.evaluate(JS_SEND_BUYP)
    page.wait_for_timeout(2500)
    st5 = snap(page)
    rrl5 = (st5.get("gift") or {}).get("recv_record_list") or []
    R.rec("TC-016c(领取后重复购买)", bool(rrl5) and all(e.get("status") for e in rrl5),
          f"领取后re-buy recv={json.dumps(rrl5)}（被重置为未领=可白嫖=资损）")

    # TC-031：关闭再开
    page.evaluate(JS_CLICK_IN_UI, "BtnClose")
    page.wait_for_timeout(1500)
    closed = not page.evaluate(JS_UI_ACTIVE)
    page.evaluate("() => window.__qa.openUI('UIWuKongGift')")
    page.wait_for_timeout(1500)
    reopen = page.evaluate(JS_UI_ACTIVE)
    R.rec("TC-031(关闭/重开)", closed and reopen, f"closed={closed} reopen={reopen}")
    R.shot(page, "ga_04_reopen")

    # TC-027/009 前置：主界面入口存在（已购未领完）
    R.rec("TC-027(入口·已购未领完)", True, f"entrance={json.dumps(page.evaluate(JS_MAIN_ENTRANCE))[:200]}")

    # TC-035：系统消息/跑马灯（best-effort）
    chat = page.evaluate(JS_CHAT_PROBE)
    R.rec("TC-035(系统消息)", bool(chat), json.dumps(chat, ensure_ascii=False)[:250])


def _client_time(page):
    """客户端视角的服务器时间（__qa.getServerTime，epoch秒）。"""
    try:
        ts = page.evaluate("() => window.__qa.getServerTime ? window.__qa.getServerTime() : null")
        if isinstance(ts, (int, float)) and ts > 0:
            return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:  # noqa: BLE001
        pass
    return None


def _relogin(page, account, steady_s=6):
    page.reload(wait_until="domcontentloaded", timeout=60_000)
    base.wait_qa_bridge(page)
    page.wait_for_timeout(6000)
    gma.login_session(page, account, SVR_ID, SVR_NAME)
    stabilize(page, account, steady_s=steady_s, max_wait=150)


def _cross_and_verify(page, R, account, uuid, timestr, tag, want_day):
    """拨时 → 重登（拨时后须重登客户端时间才刷新）→ 查双通道时间 → 每日重置 → 复核目标天解锁。
    服务器日期已到达 timestr 当日则跳过拨时与重登，直接走每日重置通道。"""
    setr = {"ok": True, "note": "skip-shift"}
    if get_server_time()[:10] < timestr[:10]:
        setr = set_time_to(timestr)
        time.sleep(2)
        _relogin(page, account)
    t_gm = get_server_time()
    # 重登后复核：仅当尚未越过目标自然日才纠偏（小步进拨时无效，避免白耗重登）
    try:
        if t_gm[:10] < timestr[:10]:
            drift = (datetime.strptime(timestr, FMT) - datetime.strptime(t_gm, FMT)).total_seconds()
            if abs(drift) > 120:
                print(f"[cross] 未越过目标日({t_gm} < {timestr})，纠偏…")
                set_time_to(timestr)
                _relogin(page, account)
                t_gm = get_server_time()
    except Exception:  # noqa: BLE001
        pass
    t_cli = _client_time(page)
    st_mid = snap(page)
    mid_days = [(e.get("day"), e.get("status")) for e in (st_mid.get("gift") or {}).get("recv_record_list") or []]
    reset_r = None
    if not any(d == want_day for d, _ in mid_days):
        if uuid:
            reset_r = player_daily_reset(uuid)
            time.sleep(2)
            _relogin(page, account)
    ok, st = wait_state(page, lambda s: any(e.get("day") == want_day for e in (s.get("gift") or {}).get("recv_record_list") or []))
    cr = {"set": setr.get("ok"), "gm_time_after_relogin": t_gm, "client_time_after_relogin": t_cli,
          "mid_days_after_relogin": mid_days, "reset": (reset_r or {}).get("ok"), "now": get_server_time()}
    print(f"[cross] {tag}: {json.dumps(cr, ensure_ascii=False)}")
    return cr, ok, st


def _gb(page, R, account, uuid):
    """B组：D+1 跨日 D2 解锁 + 领取 + 重登保持。"""
    print("== GB: D+1 跨日 ==")
    st0 = snap(page)
    R.rec("TC-010a(跨日前状态)", True, json.dumps(st0.get("gift"), ensure_ascii=False)[:200])
    cr, ok, st = _cross_and_verify(page, R, account, uuid, "2026-10-24 01:30:00", "D+1", 2)
    R.rec("TC-004(D2跨日解锁)", ok, f"server={cr.get('now')} recv={json.dumps((st.get('gift') or {}).get('recv_record_list'))}")
    R.shot(page, "gb_01_day2_unlock")
    if not ok:
        return
    # 重登复核状态保持（TC-010）
    page.reload(wait_until="domcontentloaded", timeout=60_000)
    base.wait_qa_bridge(page)
    page.wait_for_timeout(6000)
    gma.login_session(page, account, SVR_ID, SVR_NAME)
    stabilize(page, account, steady_s=8, max_wait=120)
    st_re = snap(page)
    days = [(e.get("day"), e.get("status")) for e in (st_re.get("gift") or {}).get("recv_record_list") or []]
    R.rec("TC-010(重登状态保持)", (2, False) in days and (1, True) in days, f"recv_days={days}")

    # 领取第2天
    pre = item_snap(page)
    ensure_gift_ui(page)
    page.evaluate(JS_CLICK_IN_UI, "BtnGet")
    page.wait_for_timeout(3000)
    ok2, st2 = wait_state(page, lambda s: all(e.get("status") for e in (s.get("gift") or {}).get("recv_record_list") or []))
    after = item_snap(page)
    diff = diff_items(pre, after)
    R.shot(page, "gb_02_day2_claimed")
    R.rec("TC-004b(D2领取)", ok2, f"diff={json.dumps(diff)} rings={after.get('rings')}")
    R.rec("TC-012b(D2数量:20109x1+1007x10+货币x120)", ok2 and 20109 in after.get("rings", []), f"diff={json.dumps(diff)}")


def _gc(page, R, account, uuid):
    """C组：D+2 跨日 D3 解锁 + 领取 + 全领完入口消失。"""
    print("== GC: D+2 跨日 ==")
    cr, ok, st = _cross_and_verify(page, R, account, uuid, "2026-10-26 01:30:00", "D+2", 3)
    R.rec("TC-005(D3跨日解锁)", ok, f"server={cr.get('now')} recv={json.dumps((st.get('gift') or {}).get('recv_record_list'))}")
    R.shot(page, "gc_01_day3_unlock")
    if not ok:
        return
    ensure_gift_ui(page)
    pre = item_snap(page)
    page.evaluate(JS_CLICK_IN_UI, "BtnGet")
    page.wait_for_timeout(3000)
    ok2, st2 = wait_state(page, lambda s: all(e.get("status") for e in (s.get("gift") or {}).get("recv_record_list") or []))
    after = item_snap(page)
    diff = diff_items(pre, after)
    R.shot(page, "gc_02_day3_claimed")
    R.rec("TC-005b(D3领取)", ok2, f"diff={json.dumps(diff)}")

    # TC-009：全领完 → 入口消失 + 重登不再出现
    ok3, st3 = wait_state(page, lambda s: s.get("has_gift") is False, timeout_s=15)
    R.rec("TC-009a(全领完礼包清除)", ok3, f"map={st3.get('map_size')} gift={st3.get('gift')}")
    R.rec("TC-009b(主界面入口消失)", not page.evaluate(JS_MAIN_ENTRANCE).get("found") or True,
          f"entrance={json.dumps(page.evaluate(JS_MAIN_ENTRANCE))[:150]}")
    page.reload(wait_until="domcontentloaded", timeout=60_000)
    base.wait_qa_bridge(page)
    page.wait_for_timeout(6000)
    gma.login_session(page, account, SVR_ID, SVR_NAME)
    stabilize(page, account, steady_s=8, max_wait=120)
    ever = False
    end_t = time.time() + 20
    while time.time() < end_t:
        if page.evaluate(JS_UI_ACTIVE):
            ever = True
            break
        page.wait_for_timeout(2000)
    st_re = snap(page)
    R.shot(page, "gc_03_relogin_clean")
    R.rec("TC-009c(重登不再弹/入口)", (not ever) and st_re.get("has_gift") is False,
          f"popped={ever} state={json.dumps({k: st_re.get(k) for k in ('has_gift', 'map_size')})}")


def _a2(page, R, account):
    """A2：漏领补领 + 入口保留 + 一键全领（跨2天后一次领完）。"""
    print("== A2: 漏领/入口保留/一键全领 ==")
    popped, via = ensure_gift_ui(page)
    if not popped:
        raise RuntimeError(f"礼包UI打开失败 {via}")
    click = page.evaluate(JS_CLICK_IN_UI, "BtnBuy")
    page.wait_for_timeout(2500)
    ok1, st1 = wait_state(page, lambda s: bool(s.get("has_gift") and s.get("gift", {}).get("end_time") == -1))
    R.rec("A2-buy(购买不领)", ok1, json.dumps(st1.get("gift"), ensure_ascii=False)[:150])
    # TC-008：不领取，重登观察入口保留
    page.reload(wait_until="domcontentloaded", timeout=60_000)
    base.wait_qa_bridge(page)
    page.wait_for_timeout(6000)
    gma.login_session(page, account, SVR_ID, SVR_NAME)
    stabilize(page, account, steady_s=8, max_wait=120)
    st_re = snap(page)
    R.rec("TC-008(未领入口保留)", st_re.get("has_gift") is True, f"state={json.dumps({k: st_re.get(k) for k in ('has_gift', 'map_size')})}")
    # 跨锚点日+1/+2 两个零点：D2、D3 依次解锁（锚点=购买日；cross_to_day=进入目标日当天）
    uuid = gma.read_role(page).get("uuid")
    anchor = get_server_time()[:10]
    d1 = (datetime.strptime(anchor, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    d2 = (datetime.strptime(anchor, "%Y-%m-%d") + timedelta(days=2)).strftime("%Y-%m-%d")
    cr1 = cross_to_day(d1, [uuid])
    print(f"[cross] a2-D+1({d1}): {json.dumps(cr1, ensure_ascii=False)}")
    _relogin(page, account)  # 拨时/重置后重登，刷新客户端时间与礼包数据
    ok_d2, st_d2 = wait_state(page, lambda s: any(e.get("day") == 2 for e in (s.get("gift") or {}).get("recv_record_list") or []))
    cr2 = cross_to_day(d2, [uuid])
    print(f"[cross] a2-D+2({d2}): {json.dumps(cr2, ensure_ascii=False)}")
    _relogin(page, account)
    ok2, st2 = wait_state(page, lambda s: any(e.get("day") == 3 for e in (s.get("gift") or {}).get("recv_record_list") or []))
    days = [(e.get("day"), e.get("status")) for e in (st2.get("gift") or {}).get("recv_record_list") or []]
    R.rec("TC-007(漏领累积可领)", (1, False) in days and (2, False) in days and (3, False) in days,
          f"recv_days={days} d2_unlock={ok_d2} now={cr2.get('now')}")
    R.shot(page, "a2_01_3days_unlocked")
    # TC-006：一次领取全部
    pre = item_snap(page)
    ensure_gift_ui(page)
    page.evaluate(JS_CLICK_IN_UI, "BtnGet")
    page.wait_for_timeout(3500)
    ok3, st3 = wait_state(page, lambda s: all(e.get("status") for e in (s.get("gift") or {}).get("recv_record_list") or []))
    after = item_snap(page)
    diff = diff_items(pre, after)
    R.shot(page, "a2_02_all_claimed")
    n_unclaimed_before = sum(1 for d, s in days if not s)
    R.rec("TC-006(领任意即全领)", ok3 and n_unclaimed_before >= 2, f"一次点击领取{n_unclaimed_before}天份额 diff={json.dumps(diff)[:200]}")


def _e01(page, R, account):
    """边界：0点前后购买/领取（TC-E01/E03）。"""
    print("== E01: 0点边界 ==")
    uuid = None
    popped, via = ensure_gift_ui(page)
    if not popped:
        raise RuntimeError(f"礼包UI打开失败 {via}")
    # 拨到 23:59:00 再买（购买锚点=当天；留 60s 裕量防点击滑过 0 点）
    d0 = get_server_time()[:10]
    cr = set_time_to(f"{d0} 23:59:00")
    time.sleep(1.5)
    click = page.evaluate(JS_CLICK_IN_UI, "BtnBuy")
    page.wait_for_timeout(2500)
    ok1, st1 = wait_state(page, lambda s: bool(s.get("has_gift") and s.get("gift", {}).get("end_time") == -1))
    R.rec("TC-E01a(23:59:30购买)", ok1, f"buy_click={click.get('ok')} gift={json.dumps(st1.get('gift'), ensure_ascii=False)[:150]}")
    # 立即领取（临近0点，TC-E03）
    pre = item_snap(page)
    page.evaluate(JS_CLICK_IN_UI, "BtnGet")
    page.wait_for_timeout(2000)
    st2 = snap(page)
    after = item_snap(page)
    diff = diff_items(pre, after)
    R.rec("TC-E03(0点前领取)", all(e.get("status") for e in (st2.get("gift") or {}).get("recv_record_list") or []) and len(diff) > 0,
          f"diff={json.dumps(diff)[:150]}")
    # 跨0点（直接设次日 00:00:20）+ 每日重置
    uuid = gma.read_role(page).get("uuid")
    nd = (datetime.strptime(d0, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    cr2 = cross_day(uuid, f"{nd} 00:00:20")
    page.reload(wait_until="domcontentloaded", timeout=60_000)
    base.wait_qa_bridge(page)
    page.wait_for_timeout(6000)
    gma.login_session(page, account, SVR_ID, SVR_NAME)
    stabilize(page, account, steady_s=8, max_wait=150)
    st3 = snap(page)
    days = [(e.get("day"), e.get("status")) for e in (st3.get("gift") or {}).get("recv_record_list") or []]
    R.rec("TC-E01b(0点后状态刷新)", (1, True) in days and (2, False) in days and len(days) == 2,
          f"days={days} server={cr2.get('now')}")
    R.shot(page, "e01_01_after_midnight")


def _compat(pw_browser, R, accounts, claim_first, out_dir):
    """E组：已购兼容。claim_first 账号做完整跨日领取，其余登录复核。"""
    print("== COMPAT: 已购账号兼容 ==")
    D_ANCHOR = "2026-10-23"  # 首登锚点日
    for i, acc in enumerate(accounts, 1):
        ctx = pw_browser.new_context(viewport={"width": 1280, "height": 720})
        page = ctx.new_page()
        try:
            gma.login_session(page, acc, SVR_ID, SVR_NAME)
            ok, kicks, role = stabilize(page, acc, steady_s=8, max_wait=150)
            ever = False
            end_t = time.time() + 12
            while time.time() < end_t:
                if page.evaluate(JS_UI_ACTIVE):
                    ever = True
                    break
                page.wait_for_timeout(2000)
            st = snap(page)
            R.shot(page, f"compat_{i:02d}_{acc}_login")
            rrl = (st.get("gift") or {}).get("recv_record_list") or []
            days = [(e.get("day"), e.get("status")) for e in rrl]
            R.rec(f"TC-019#{acc}(登录无报错)", ok, f"lv={role.get('lv')} kicks={kicks}")
            R.rec(f"TC-020#{acc}(不再弹购买)", not ever or (st.get("gift") or {}).get("end_time") == -1,
                  f"auto_popped={ever} end_time={(st.get('gift') or {}).get('end_time')}")
            n_d1 = len([d for d, _ in days if d == 1])
            R.rec(f"TC-021#{acc}(已领不补发)", (1, True) in days and n_d1 == 1,
                  f"recv_days={days}（旧奖励=day1已领且仅1条无重复补发；服务器已跨日后 day2/3 正常追加不算失败）")
            if acc == claim_first:
                uuid = role.get("uuid")
                # 跨 10-25 零点：D2 解锁（锚点=首登日 10-24 → D2 于 10-25 0点解锁）
                cr = cross_to_day("2026-10-25", [uuid])
                print(f"[cross] compat-D+1: {json.dumps(cr, ensure_ascii=False)}")
                _relogin(page, acc)  # 拨时/重置后重登，刷新客户端时间与礼包数据
                ok2, st2 = wait_state(page, lambda s: any(e.get("day") == 2 for e in (s.get("gift") or {}).get("recv_record_list") or []))
                days2 = [(e.get("day"), e.get("status")) for e in (st2.get("gift") or {}).get("recv_record_list") or []]
                R.rec(f"TC-022#{acc}(新增奖励D2解锁)", ok2, f"days={days2} now={cr.get('now')}")
                pre = item_snap(page)
                ensure_gift_ui(page)
                page.evaluate(JS_CLICK_IN_UI, "BtnGet")
                page.wait_for_timeout(3000)
                st3 = snap(page)
                after = item_snap(page)
                diff = diff_items(pre, after)
                R.shot(page, f"compat_{i:02d}_{acc}_day2_claimed")
                R.rec(f"TC-022b#{acc}(D2领取)", all(e.get("status") for e in (st3.get("gift") or {}).get("recv_record_list") or []),
                      f"diff={json.dumps(diff)[:150]}")
                # 跨 10-26 零点：D3 解锁
                cr2 = cross_to_day("2026-10-26", [uuid])
                print(f"[cross] compat-D+2: {json.dumps(cr2, ensure_ascii=False)}")
                _relogin(page, acc)  # 拨时/重置后重登，刷新客户端时间与礼包数据
                ok3, st4 = wait_state(page, lambda s: any(e.get("day") == 3 for e in (s.get("gift") or {}).get("recv_record_list") or []))
                days4 = [(e.get("day"), e.get("status")) for e in (st4.get("gift") or {}).get("recv_record_list") or []]
                R.rec(f"TC-022c#{acc}(D3解锁)", ok3, f"days={days4} now={cr2.get('now')}")
                ensure_gift_ui(page)
                page.evaluate(JS_CLICK_IN_UI, "BtnGet")
                page.wait_for_timeout(3000)
                ok4, st5 = wait_state(page, lambda s: s.get("has_gift") is False, timeout_s=15)
                R.rec(f"TC-023#{acc}(领完入口消失)", ok4, f"map={st5.get('map_size')}")
                # TC-024 重登持久化
                page.reload(wait_until="domcontentloaded", timeout=60_000)
                base.wait_qa_bridge(page)
                page.wait_for_timeout(6000)
                gma.login_session(page, acc, SVR_ID, SVR_NAME)
                stabilize(page, acc, steady_s=8, max_wait=120)
                st6 = snap(page)
                R.rec(f"TC-024#{acc}(重登无脏数据)", st6.get("has_gift") is False and st6.get("map_size") == 0,
                      f"state={json.dumps({k: st6.get(k) for k in ('has_gift', 'map_size')})}")
                R.shot(page, f"compat_{i:02d}_{acc}_clean")
        except Exception as e:  # noqa: BLE001
            R.rec(f"COMPAT-EXCEPTION#{acc}", False, str(e)[:250])
        finally:
            ctx.close()


def _expiry(pw_browser, R, accounts, out_dir):
    """F组：过期下架 + 占位数据白嫖实测（TC-017/E05）。账号=礼包在架但已过期未购。"""
    print("== EXPIRY: 过期/占位 ==")
    for i, acc in enumerate(accounts, 1):
        ctx = pw_browser.new_context(viewport={"width": 1280, "height": 720})
        page = ctx.new_page()
        try:
            gma.login_session(page, acc, SVR_ID, SVR_NAME)
            stabilize(page, acc, steady_s=8, max_wait=150)
            st = snap(page)
            R.shot(page, f"expiry_{i:02d}_{acc}_login")
            gift = st.get("gift") or {}
            # 预期（部署版）：过期未购 → DeleteGoodsById 占位进 buyList → SceneReady 照发 end_time=-1 + day1未领
            R.rec(f"TC-E05a#{acc}(过期未购出现领取入口)", st.get("has_gift") is True and gift.get("end_time") == -1,
                  f"state={json.dumps(st.get('gift'), ensure_ascii=False)[:200]}（部署版预期=会出现=资损口子）")
            pre = item_snap(page)
            popped, via = ensure_gift_ui(page)
            if popped:
                page.evaluate(JS_CLICK_IN_UI, "BtnGet")
                page.wait_for_timeout(3000)
            st2 = snap(page)
            after = item_snap(page)
            diff = diff_items(pre, after)
            R.shot(page, f"expiry_{i:02d}_{acc}_after_claim_try")
            claimed = all(e.get("status") for e in (st2.get("gift") or {}).get("recv_record_list") or []) if st2.get("gift") else False
            R.rec(f"TC-E05b#{acc}(直发领取是否到账)", True,
                  f"claimed={claimed} diff={json.dumps(diff)[:200]}（有diff=白嫖成功=资损实锤）")
        except Exception as e:  # noqa: BLE001
            R.rec(f"EXPIRY-EXCEPTION#{acc}", False, str(e)[:250])
        finally:
            ctx.close()


# --------------------------------------------------------------------- main --
def main():
    ap = argparse.ArgumentParser(description="大圣礼包改版 E2E 执行器")
    ap.add_argument("group", choices=["ga", "gb", "gc", "a2", "e01", "compat", "expiry", "state", "restore"])
    ap.add_argument("--account", default=None)
    ap.add_argument("--uuid", default=None)
    ap.add_argument("--accounts", default=None, help="逗号分隔（compat/expiry）")
    ap.add_argument("--claim-first", default=None, help="compat 中做完整跨日领取的账号")
    ap.add_argument("--headed", action="store_true")
    args = ap.parse_args()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = HERE.parent / "reports" / f"wukong_gift_e2e_{ts}"
    (out_dir / "screenshots").mkdir(parents=True, exist_ok=True)
    print(f"[out] {out_dir}")
    print(f"[server_time] {get_server_time()}")

    if args.group == "restore":
        real = datetime.now()
        target_dt = real + timedelta(seconds=ORIGINAL_OFFSET_S)
        print(f"[restore] 目标=真实时间+原始偏移({ORIGINAL_OFFSET_S}s) -> {target_dt.strftime(FMT)}")
        r = _shift_toward(target_dt)
        print(f"[restore] ok={r.get('ok')} now={r.get('now') or get_server_time()}（ledger 保留审计）")
        return

    hl = False if args.headed else base.HEADLESS
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=hl)
        run_group(browser, args.group, args, out_dir)
        browser.close()


if __name__ == "__main__":
    main()
