# -*- coding: utf-8 -*-
"""法宝换皮 异常场景配置校验（v2，按真实 JSON 结构）：
1) cfg_soul_ring_base.gift_id → ring_group 越界/缺失（旧档兼容：所有法宝必须有合法组）
2) cfg_soul_ring_upgrade 组1~10 齐全、level 连续
3) year_color 年份区间覆盖每个组/阶的 year（阶数颜色兜底）
4) cfg_soul_ring_features 解锁 level ≤ 组最高阶
5) cfg_soul_ring_icon 覆盖所有法宝
6) 组别→资源映射 + 法宝 icon/show_res 资源文件存在性
输出: fabao_config_check_report.json
"""
import json
from pathlib import Path

CFG = Path(r"E:\p1-x\trunk\client\assets\resources\cfg\soul_ring")
RES = Path(r"E:\p1-x\trunk\client\assets\resources")

def load(name):
    return json.loads((CFG / name).read_text(encoding="utf-8"))

base = load("cfg_soul_ring_base.json")
upgrade = load("cfg_soul_ring_upgrade.json")
year_color = load("cfg_soul_ring_year_color.json")
features = load("cfg_soul_ring_features.json")
icon = load("cfg_soul_ring_icon.json")

issues = []
def issue(tag, msg):
    issues.append({"tag": tag, "msg": msg})

# ---------- 1) base.ring_group ----------
group_of_ring = {}
bad = []
for rid, e in base.items():
    g = e.get("ring_group")
    group_of_ring[rid] = g
    if not isinstance(g, int) or not (1 <= g <= 10):
        bad.append((rid, e.get("name"), g))
if bad:
    issue("RING_GROUP_BOUNDS", f"ring_group 非法(须1~10): {bad}")
groups_used = sorted({g for g in group_of_ring.values() if isinstance(g, int)})
group_count = {g: sum(1 for v in group_of_ring.values() if v == g) for g in groups_used}

# ---------- 2) upgrade 组齐全、level 连续 ----------
up = {}  # group -> {level: cfg}
for g in range(1, 11):
    node = upgrade.get(str(g))
    if node is None:
        issue("UPGRADE_GROUP_MISSING", f"cfg_soul_ring_upgrade 缺组 {g}")
        continue
    lvls = {}
    for lk, lv in node.items():
        try:
            lvls[int(lk)] = lv
        except Exception:
            pass
    up[g] = lvls
    if lvls:
        lo, hi = min(lvls), max(lvls)
        gaps = sorted(set(range(lo, hi + 1)) - set(lvls))
        if gaps:
            issue("UPGRADE_LEVEL_GAP", f"组{g} level 缺档 {gaps}")

# ---------- 3) year_color 区间覆盖 ----------
bands = []
for k, v in year_color.items():
    bands.append((int(v["minYear"]), int(v["maxYear"]), v.get("color"), k))
bands.sort()
uncovered = []
for g, lvls in up.items():
    for lv, cfg in lvls.items():
        y = cfg.get("year")
        if not isinstance(y, (int, float)):
            continue
        if not any(lo <= y <= hi for lo, hi, _, _ in bands):
            uncovered.append((g, lv, y))
if uncovered:
    issue("YEAR_COLOR_GAP", f"{len(uncovered)} 个 组/阶 的 year 无颜色区间覆盖, 样例: {uncovered[:10]}")

# ---------- 4) features 解锁边界 ----------
feat_bad = []
for rid, flist in features.items():
    g = group_of_ring.get(rid)
    maxlv = max(up[g]) if isinstance(g, int) and up.get(g) else None
    for fe in (flist.values() if isinstance(flist, dict) else flist):
        lv = fe.get("level")
        if maxlv is not None and isinstance(lv, int) and lv > maxlv:
            feat_bad.append((rid, fe.get("id"), lv, f">组{g}最高阶{maxlv}"))
if feat_bad:
    issue("FEATURES_BOUND", f"特性解锁阶超出组最高阶: {feat_bad}")

# ---------- 5) icon 覆盖 ----------
icon_ids = set(icon.keys()) if isinstance(icon, dict) else set()
no_icon = [rid for rid in base if rid not in icon_ids]
if no_icon:
    issue("ICON_MISSING", f"cfg_soul_ring_icon 缺法宝: {no_icon}")

# ---------- 6) 资源存在性 ----------
KUANG = {1: "07", 2: "01", 3: "02", 4: "03", 5: "04", 6: "08", 7: "09", 8: "10", 9: "05", 10: "06"}
GUANGQIU = {1: "7", 2: "1", 3: "2", 4: "3", 5: "4", 6: "8", 7: "9", 8: "10", 9: "5", 10: "6"}
FABAO_FX = {1: 7, 2: 1, 3: 2, 4: 3, 5: 4, 6: 8, 7: 9, 8: 10, 9: 5, 10: 6}
WUPIN = {1: "01", 2: "02", 3: "03", 4: "04", 5: "05", 6: "09", 7: "10", 8: "11", 9: "06", 10: "07"}
SKILL = {2: "hero_img05_white", 3: "hero_img05_yellow", 4: "hero_img05_purple", 5: "hero_img05_black",
         6: "hero_img05_orange", 7: "hero_img05_coral", 8: "hero_img05_pink", 9: "hero_img05_red", 10: "hero_img05_god"}

def exists(stem):
    return any(RES.rglob(stem))

res_miss = []
for g in range(1, 11):
    checks = [
        f"common_item02_wupinkuang{WUPIN[g]}.png",
        f"soul_ring_atlas_panel01_kuang{KUANG[g]}.png",
        f"effect_ui_hunhuanchou_guangqiu{GUANGQIU[g]}.png",
        f"effect_ui_fabao_{FABAO_FX[g]}.skel",
    ]
    if g in SKILL:
        checks.append(SKILL[g] + ".png")
    for c in checks:
        if not exists(c):
            res_miss.append((g, c))
if res_miss:
    issue("RES_MISSING", f"资源缺失: {res_miss}")

# 法宝自身 icon/show_res 抽样（每组抽2个）
icon_miss = []
for rid, e in base.items():
    g = e.get("ring_group")
    if g in (1, 5, 10) and rid in ("6001", "6005", "6100", "6113"):
        ic = e.get("icon", "")
        if ic and not exists(ic + ".png"):
            icon_miss.append((rid, "icon", ic))
        sr = e.get("show_res", "")
        if sr and not (exists(sr + ".png") or exists(sr + ".skel")):
            icon_miss.append((rid, "show_res", sr))
if icon_miss:
    issue("RING_RES_MISSING", f"法宝资源缺失(抽样): {icon_miss}")

# ---------- 汇总 ----------
summary = {
    "total_rings": len(base),
    "groups_used": groups_used,
    "group_count": group_count,
    "upgrade_groups": sorted(up.keys()),
    "year_bands": bands,
    "issue_count": len(issues),
    "issues": issues,
    "pass": len(issues) == 0,
}
out = Path(__file__).parent / "fabao_config_check_report.json"
out.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"法宝数={len(base)} 使用组分布={group_count}")
for t, m in issues:
    print(f"[{t}] {m[:200]}")
print(f"==== {len(issues)} 个问题 ====")
print("报告:", out)
