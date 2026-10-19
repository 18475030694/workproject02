# -*- coding: utf-8 -*-
"""将 2026-09-10 E2E 执行结果（data.json + 截图复判）回填到灵宠用例 v3 Excel → 输出「已回填」版本
复判依据：截图肉眼复核（TC-06 显示正确/TC-01,08 弹窗遮挡）+ cfg_err_code 错误码语义（TC-11/18 拦截正确）
"""
import json
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

SRC = r"E:\workproject\temp_case\cases\灵宠年份改等级_测试用例_v3.xlsx"
OUT = r"E:\workproject\temp_case\cases\灵宠年份改等级_测试用例_v3_已回填.xlsx"
DATA = r"E:\workproject\reports\e2e_soulspirit_20260910_165528\data.json"

# 复判（人工依据截图/错误码）：key → (复判结果, 复判说明)
REJUDGE = {
    "TC-01": ("待人工复核", "「恭喜获得」抽卡弹窗遮挡主界面，YearLbl 节点读取为空（脚本断言失效）；截图角标无年份字样，待关弹窗人工复看"),
    "TC-02": ("待人工复核", "同 TC-01 弹窗遮挡，角标节点抓取为空；截图列表角标可见数字（2000 等）无年份"),
    "TC-03": ("待人工复核", "进阶界面脚本入口未打开（showUI 未激活），非显示问题；需人工从主界面点进阶按钮复核"),
    "TC-04": ("未执行", "进阶界面未保持，跳过"),
    "TC-05": ("待人工复核", "重置弹窗脚本入口未打开；prefab 文案静态复核已通过"),
    "TC-06": ("通过（截图佐证）", "截图可见图鉴卡片「55级/2000级/30级/1级」真实等级显示，排序正常；脚本文本 dump 抓取失败（弹窗遮挡+虚拟化节点）"),
    "TC-07": ("通过", None),
    "TC-08": ("待人工复核", "弹窗遮挡致 YearLbl 读取为空；但截图可见「已满阶」按钮文案正确、角标 2000 无年份量级"),
    "TC-09": ("待人工复核", "共鸣界面脚本入口未打开"),
    "TC-10": ("未执行", "本轮脚本未覆盖（推荐排序依赖真实魂师界面入口）"),
    "TC-11": ("通过", "err=2312=「灵宠已是当前阶最大等级」正确拦截（cfg_err_code L3871），文案为等级表述"),
    "TC-12": ("通过", None),
    "TC-13": ("未执行", "onShow 需 RoleSnapInfo 快照，运行时不可构造；与 TC-12 同组件"),
    "TC-14": ("未执行", "需真实阵容编辑入口"),
    "TC-15": ("待人工复核", "装备弹窗脚本入口未打开"),
    "TC-16": ("通过", None),
    "TC-17": ("未执行", "限时活动未开放，静态清单已复核"),
    "TC-18": ("通过（脚本误报）", "err=2322=「灵宠图鉴积分已领取」=脚本重复领取同一节点；err=2324=「积分不足，无法升级」正确拦截（cfg_err_code L3931/L3943）；两条文案均为等级表述、无年份"),
    "TC-19": ("未执行", "战令未开放，静态清单已复核"),
    "TC-20": ("未执行", "需充值触发，静态清单已复核（cfg_charge_push_gift_pack L1623）"),
    "TC-21": ("未执行", "特权入口受限，静态清单已复核"),
    "TC-22": ("待人工复核", "DescBtn 点击未弹出 UISystemHelp（脚本点击方式问题）；cfg_sys_help id=39 文案静态复核已通过"),
    "TC-23": ("疑似问题-待复核", "DescPop onShow 抛 TypeError: Cannot read properties of null (reading 'quality')（UISoulSpiritDescPop.update←onClickToggleGroup←onShow）；可能是脚本 showUI 直调参数口径问题，需人工从背包→灵宠物品→详情入口复核"),
    "TC-24": ("部分通过", "I18N_LEVEL key 验证通过（formatStr→「5级」）；好友界面脚本未打开，宗门/炼药堂等级待人工抽查"),
    "TC-27": ("通过", None),
    "TC-28": ("通过（静态）", "5 处 prefab/配置文案静态复核已通过 ✅；运行时部分待 TC-03/04/05/22 人工复核时一并确认（含切图底图需截图）"),
    "TC-29": ("通过（静态）", "soul_spirit 脚本 .year 消费清零，旧函数名 0 引用（2026-09-10 复核 ✅）"),
}

PASS_FILL = PatternFill("solid", fgColor="E2EFDA")
FAIL_FILL = PatternFill("solid", fgColor="FCE4EC")
NA_FILL = PatternFill("solid", fgColor="F2F2F2")
RJ_FONT = Font(bold=True)
OK_FONT = Font(color="008000", bold=True)
BAD_FONT = Font(color="C00000", bold=True)
WARN_FONT = Font(color="BF8F00", bold=True)
HDR_FONT = Font(bold=True, color="FFFFFF")
HDR_FILL = PatternFill("solid", fgColor="1F4E78")
WRAP = Alignment(vertical="top", wrap_text=True)
CENTER = Alignment(vertical="center", horizontal="center", wrap_text=True)
THIN = Border(*[Side(style="thin", color="B0B0B0")] * 4)

wb = openpyxl.load_workbook(SRC)
ws = wb["测试用例"]
data = json.load(open(DATA, encoding="utf-8"))
run = {c["case_id"]: c for c in data["cases"]}

# 追加表头 J..M
heads = ["执行结果", "复判/判定", "执行说明", "证据截图"]
for i, h in enumerate(heads):
    cell = ws.cell(1, 10 + i, h)
    cell.font = HDR_FONT; cell.fill = HDR_FILL; cell.alignment = CENTER; cell.border = THIN

summary = {"通过": 0, "失败": 0, "未执行": 0, "待复核": 0}
for r in range(2, ws.max_row + 1):
    tc = ws.cell(r, 1).value
    if not tc:
        continue
    run_c = run.get(tc)
    if run_c is None:
        exec_res, note, shot = "未执行", REJUDGE.get(tc, ("未执行", None))[1] or "本轮未跑", ""
        rj = REJUDGE.get(tc, ("未执行", ""))[0]
    else:
        p = run_c.get("passed")
        exec_res = "通过" if p is True else ("失败" if p is False else "N/A")
        note = run_c.get("note", "")
        shot = run_c.get("screenshot", "")
        rj, rj_note = REJUDGE.get(tc, (exec_res, None))
        if rj_note:
            note = f"{note} ｜复判: {rj_note}"
    # 颜色
    fill, font = None, None
    if exec_res == "通过" or rj.startswith("通过"):
        fill, font = PASS_FILL, OK_FONT; summary["通过"] += 1
    elif rj.startswith("疑似问题"):
        fill, font = FAIL_FILL, BAD_FONT; summary["失败"] += 1
    elif exec_res == "失败":
        fill, font = FAIL_FILL, WARN_FONT; summary["待复核"] += 1
    else:
        fill, font = NA_FILL, Font(color="808080"); summary["未执行"] += 1
    vals = [exec_res, rj, note, shot]
    for i, v in enumerate(vals):
        cell = ws.cell(r, 10 + i, v)
        cell.alignment = WRAP if i >= 2 else CENTER
        cell.border = THIN
        cell.fill = fill
    ws.cell(r, 10).font = font
    ws.cell(r, 11).font = RJ_FONT if not font else font

for col, w in zip(["J", "K", "L", "M"], [12, 16, 60, 26]):
    ws.column_dimensions[col].width = w

# ============ Sheet3 E2E 执行概要 ============
ws3 = wb.create_sheet("E2E执行概要")
ws3.append(["灵宠年份改等级 E2E 执行概要（2026-09-10 16:55，账号4451 @ S5）"])
ws3["A1"].font = Font(bold=True, size=14)
ws3.append([])
ws3.append(["结论", "PASS 5 / FAIL 12 / N/A 7；经截图与错误码复判：直接通过 8（含 TC-06 截图佐证、TC-18 误报排除），待人工复核 8（多为脚本入口/弹窗遮挡），疑似产品问题 1（TC-23 DescPop 空引用报错），未执行/N-A 10"])
ws3.append(["报告目录", r"E:\workproject\reports\e2e_soulspirit_20260910_165528\（data.json + screenshots\11 张）"])

r = ws3.max_row + 2
ws3.cell(r, 1, "数据准备（GM）").font = Font(bold=True); r += 1
for k, v in [("set_mainline_stage 5000", "系统开启（sys_id=116 灵宠）"),
             ("抽卡 30 连", "by_q {品5:2, 品6:1, 品7:1}，共 4 只灵宠"),
             ("uuid47 品5", "升至 lv30/ph2"),
             ("uuid48 品6", "升至 lv2000/ph199（满级满阶）"),
             ("uuid49 品7", "升至 lv55/ph5"),
             ("uuid46 品5", "保持初始 lv1/ph0")]:
    ws3.cell(r, 1, k); ws3.cell(r, 2, v); r += 1

r = ws3.max_row + 2
ws3.cell(r, 1, "全局「年份」残留检索（2026-09-10，灵宠口径清零确认）").font = Font(bold=True); r += 1
for c, v in enumerate(["范围", "结论"], 1):
    cell = ws3.cell(r, c, v); cell.font = HDR_FONT; cell.fill = HDR_FILL; cell.border = THIN
r += 1
for row in [
    ("export 配置（服务端配置文档）", "0 命中 ✅"),
    ("飘字/错误码 cfg_err_code.json", "灵宠 2312~2325 全部为等级/阶级/星级表述，无年份 ✅（2312=已是当前阶最大等级/2313=最大阶/2319=无法重置/2324=积分不足）"),
    ("cfg_langs（I18N 飘字）", "0 命中 ✅"),
    ("server lua 11 处", "全部为魂环/技能/战斗日志（mod_soul_ring、buff、skill_set 等），非灵宠，属保留项 ✅"),
    ("client ts 15 处", "魂环 SoulRingMgr/SkillHelper/ItemHelper(showYear 魂环tips专用)/Buff/EffectFunction、坐骑 UIMountFeedReset（年份回到初始）、DateTS 日期注释、UISoulBone 注释 —— 非灵宠，保留 ✅"),
    ("resources 6 处", "cfg_sys_help.json id=23 装备「装备年份」、cfg_sys_help_mix_img+UISystemMixImgHelp.prefab 法宝、UIRingUnlockSkill.prefab 魂环、UIMountFeedReset/UIMountFeed.prefab 坐骑 —— 非灵宠，保留 ✅"),
    ("灵宠道具 tips（cfg_item.json）", "灵宠养料/灵宠印记/共鸣水晶/技能书宝箱/红灵宠宝箱/自选礼包/灵宠卡（typeName=灵宠）desc 全部无「年份」✅；注意：礼包类切图标题（res 图）文本检索覆盖不到，需截图抽查"),
    ("灵宠体系（soul_spirit 代码+prefab+配置）", "0 残留 ✅（TC-29 静态验收通过）"),
]:
    ws3.cell(r, 1, row[0]).alignment = WRAP
    ws3.cell(r, 2, row[1]).alignment = WRAP
    r += 1

r = ws3.max_row + 2
ws3.cell(r, 1, "待人工复核清单").font = Font(bold=True); r += 1
for line in [
    "1. TC-23 灵宠详情弹窗：背包→灵宠物品→详情 入口人工打开（脚本直调报 null.quality，见 screenshots/TC23_descpop.png 错误弹窗）",
    "2. TC-01/02/08：关闭抽卡「恭喜获得」弹窗后复看主界面 X级/X级、列表角标、满级显示（截图被遮挡）",
    "3. TC-03/04/05/09/15/22：从真实 UI 入口人工走一遍 进阶→结果弹窗→重置→共鸣→装备→玩法说明",
    "4. TC-24：人工抽查 宗门/好友/魂兽追击/炼药堂 等级文案仍为 X级",
    "5. 礼包类切图标题（灵宠卡/礼包头图）为 res 切图，文本检索覆盖不到，建议截图抽查",
]:
    ws3.cell(r, 1, line).alignment = WRAP
    ws3.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
    r += 1

ws3.column_dimensions["A"].width = 40
ws3.column_dimensions["B"].width = 100
wb.save(OUT)
print("saved:", OUT)
print("summary:", json.dumps(summary, ensure_ascii=False))
