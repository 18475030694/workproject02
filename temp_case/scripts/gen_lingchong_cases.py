# -*- coding: utf-8 -*-
"""生成《灵宠年份改等级_测试用例.xlsx》—— v3 执行版：BUG-01/02 已复核修复，移除坐骑/魂环用例（27 条）"""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

OUT = r"E:\workproject\temp_case\cases\灵宠年份改等级_测试用例_v3.xlsx"

HDR_FILL = PatternFill("solid", fgColor="1F4E78")
SEC_FILL = PatternFill("solid", fgColor="DDEBF7")
WARN_FILL = PatternFill("solid", fgColor="FCE4EC")
OK_FONT = Font(color="008000")
BAD_FONT = Font(color="C00000", bold=True)
HDR_FONT = Font(bold=True, color="FFFFFF")
WRAP = Alignment(vertical="top", wrap_text=True)
CENTER = Alignment(vertical="center", horizontal="center", wrap_text=True)
THIN = Border(*[Side(style="thin", color="B0B0B0")] * 4)

wb = openpyxl.Workbook()

# ============ Sheet1 概览与代码检查结论 ============
ws = wb.active
ws.title = "概览与检查结论"
ws.append(["灵宠「年份」表现改为「等级」——代码静态检查概览（v3 执行版，2026-09-10）"])
ws["A1"].font = Font(bold=True, size=14)
ws.append([])
ws.append(["需求口径", "仅限灵宠系统（soul_elf/魂灵）；显示值从 cfg_soul_elf_level 的 year 字段改为读同表 level 字段（真实等级 1~2000）；坐骑/魂环/装备/法宝帮助等年份文案不动"])
ws.append(["检查范围", "工作副本 13 个已改 ts（SoulSpiritMgr + ui/soul_spirit 8 个 + Advance）+ prefab 静态文案 + cfg_sys_help + 全局 .year 残留引用"])
ws.append(["总体结论", "BUG-01（进阶界面读 .year）与 BUG-02（静态文案 5 处）均已复核修复 ✅；动态取值 13 处全改读 level、soul_spirit 脚本 .year 消费清零；用例 27 条（v3 移除坐骑 TC-25/魂环 TC-26，编号保留空洞）"])

r = ws.max_row + 2
ws.cell(r, 1, "一、已改完清单（显示值 year→level）").font = Font(bold=True)
r += 1
h1 = ["#", "文件", "位置", "改动"]
for c, v in enumerate(h1, 1):
    cell = ws.cell(r, c, v); cell.font = HDR_FONT; cell.fill = HDR_FILL; cell.alignment = CENTER; cell.border = THIN
DONE = [
    (1, "logic/soul_spirit/SoulSpiritMgr.ts", "L380-383", "getCurYearByQuality → getCurLevelByQuality，返回 conf.level"),
    (2, "logic/soul_spirit/SoulSpiritMgr.ts", "L386-390", "getMaxYearByQuality → getMaxLevelByQuality，返回 confs.level"),
    (3, "logic/soul_spirit/SoulSpiritMgr.ts", "L408-411", "新增 getMaxLevel(quality)（品质满级 2000）"),
    (4, "logic/soul_spirit/SoulSpiritMgr.ts", "L571-572", "魂师可穿戴推荐排序权重改读 .level"),
    (5, "ui/soul_spirit/UISoulSpiritAdvanceResult.ts", "L41-42", "进阶结果弹窗前后值读 .level"),
    (6, "ui/soul_spirit/UISoulSpiritAtlas.ts", "L111", "图鉴排序权重 → getCurLevelByQuality"),
    (7, "ui/soul_spirit/UISoulSpiritAtlasItem.ts", "L78", "图鉴项等级 → getCurLevelByQuality"),
    (8, "ui/soul_spirit/UISoulSpiritItem.ts", "L60-61", "列表 Item 角标读 .level（变量名 yearCfg 残留）"),
    (9, "ui/soul_spirit/UISoulSpiritMain.ts", "L141-142 / L229-232 / L410-413", "列表排序+进度条+X级/X级 文本全改 level"),
    (10, "ui/soul_spirit/UISoulSpiritNewGet.ts", "L58-60", "新获得弹窗 X级 宠物名 读 .level；属性预览走 calcAttrByLevel"),
    (11, "ui/soul_spirit/UISoulSpiritResonance.ts", "L96-97", "共鸣候选排序读 .level"),
    (12, "ui/soul_spirit/UISoulSpiritResonancePop.ts", "L111-112", "共鸣弹窗排序读 .level"),
    (13, "ui/soul_spirit/UISoulSpiritDescPop.ts", "L132 / L244", "满等级、星级预览改用新增 getMaxLevel()"),
]
for row in DONE:
    r += 1
    for c, v in enumerate(row, 1):
        cell = ws.cell(r, c, v); cell.alignment = WRAP if c > 2 else CENTER; cell.border = THIN
    ws.cell(r, 4).font = OK_FONT

r = ws.max_row + 2
c1 = ws.cell(r, 1, "二、BUG-01（原漏改）✅ 已修复，2026-09-10 复核"); c1.font = OK_FONT
r += 1
for c, v in enumerate(["文件", "位置", "复核结果"], 1):
    cell = ws.cell(r, c, v); cell.font = HDR_FONT; cell.fill = HDR_FILL; cell.alignment = CENTER; cell.border = THIN
r += 1
for c, v in enumerate(["ui/soul_spirit/UISoulSpiritAdvance.ts", "L70-71",
                       "已改为读 levelConf.level / levelConfNext.level ✅；ConfigDefine ICfgSoulElfLevel 保留 year 字段（配置列保留，可不动）"], 1):
    cell = ws.cell(r, c, v); cell.alignment = WRAP; cell.border = THIN
    if c == 3:
        cell.font = OK_FONT
ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=4)

r = ws.max_row + 2
c1 = ws.cell(r, 1, "三、BUG-02（原静态文案 5 处）✅ 已全部修复，2026-09-10 复核"); c1.font = OK_FONT
r += 1
for c, v in enumerate(["位置", "复核结果"], 1):
    cell = ws.cell(r, c, v); cell.font = HDR_FONT; cell.fill = HDR_FILL; cell.alignment = CENTER; cell.border = THIN
TEXTS = [
    ("UISoulSpiritAdvance.prefab「年份上限:」", "已改 ✅（soul_spirit prefab 目录搜「年份」0 命中）"),
    ("UISoulSpiritAdvanceResult.prefab「年份上限」", "已改 ✅"),
    ("UISoulSpiritMain.prefab「重置年份」", "已改 ✅"),
    ("UISoulSpiritReset.prefab「年份和阶级回到初始」", "已改 ✅"),
    ("cfg_sys_help.json id=39 灵宠玩法说明", "已改为「可重置等级和阶级，返还100%培养材料」✅"),
]
for row in TEXTS:
    r += 1
    for c, v in enumerate(row, 1):
        cell = ws.cell(r, c, v); cell.alignment = WRAP; cell.border = THIN
    ws.cell(r, 2).font = OK_FONT

r = ws.max_row + 2
ws.cell(r, 1, "四、低优先级残留（不影响显示，是否清理由开发定，不设用例）").font = Font(bold=True)
r += 1
ws.cell(r, 1, "局部变量名 yearA/yearB（Main/Resonance/ResonancePop 排序）、yearCfg（Item L60）、curYear/maxYear（Main）；节点/组件名 YearLbl_txt/YearPb_prg/Year_txt/PreYear_txt/NextYear_txt；cfg_soul_elf_level.json 的 year 列保留（soul_spirit 脚本 .year 消费已清零 ✅）").alignment = WRAP
ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)

for col, w in zip("ABCD", [6, 44, 60, 52]):
    ws.column_dimensions[col].width = w

# ============ Sheet2 测试用例 ============
ws2 = wb.create_sheet("测试用例")
h2 = ["用例编号", "分类", "用例标题", "优先级", "前置条件", "操作步骤", "预期结果", "测试方式", "静态检查现状"]
for c, v in enumerate(h2, 1):
    cell = ws2.cell(1, c, v); cell.font = HDR_FONT; cell.fill = HDR_FILL; cell.alignment = CENTER; cell.border = THIN

PRE = "开服≥4天、主线900关；GM号4451（lv9463）；S5 调 serverDay 需改→测→还原"
CASES = [
    ("TC-01", "P0-核心展示", "灵宠主界面-选中态等级显示", "P0", PRE + "，拥有不同品质/等级灵宠",
     "打开灵宠主界面 → 依次选中紫5/橙6/红7、不同等级/阶级灵宠",
     "进度条与 X级/X级 文案显示真实 level（如 1级/10级）；无「年份」字样；无 1000/200万 年份量级数字；进度条为阶级内分段进度",
     "运行时", "已改（Main L229-232/L410-413）"),
    ("TC-02", "P0-核心展示", "灵宠列表 Item 等级角标", "P0", PRE,
     "查看主界面列表所有灵宠 Item",
     "角标显示真实等级 X级；未拥有灵宠角标为空（Item L99）",
     "运行时", "已改（Item L60-61）"),
    ("TC-03", "P0-核心展示", "灵宠进阶-前后等级对比", "P0", PRE + "，有可进阶灵宠",
     "选择可进阶灵宠 → 打开进阶界面查看 PreYear/NextYear 两栏",
     "文案为等级表述（如「等级上限:」）；前后数值=当前阶级 level_limit 与下一阶级 level_limit（如 10级→20级）",
     "运行时", "已改（Advance.ts L70-71 读 .level；prefab 文案已改）"),
    ("TC-04", "P0-核心展示", "进阶成功结果弹窗", "P0", PRE + "，同 TC-03 灵宠",
     "执行进阶 → 查看结果弹窗；与进阶界面数值对比",
     "数值=新旧阶级 level_limit；文案为等级表述；与 TC-03 同灵宠数值一致",
     "运行时", "已改（AdvanceResult L41-42；prefab 文案已改）"),
    ("TC-05", "P0-核心展示", "灵宠重置", "P0", PRE + "，有 phase>0 或 level>1 灵宠",
     "对可重置灵宠点重置按钮 → 确认弹窗 → 执行重置",
     "按钮文案与确认弹窗均为等级表述（如「等级和阶级回到初始」）；重置后等级/阶级回初始、材料返还 100%",
     "运行时", "已改（2 处 prefab 文案已改）"),
    ("TC-06", "P0-核心展示", "灵宠图鉴", "P0", PRE,
     "打开图鉴页签，查看已激活/未激活项",
     "每项显示真实等级 X级；排序（Atlas L111 按 getCurLevelByQuality）与改版前一致",
     "运行时", "已改（Atlas L111 / AtlasItem L78）"),
    ("TC-07", "P0-核心展示", "获得新灵宠弹窗", "P0", PRE + "，传灵塔可抽",
     "通过传灵塔孵化获得新灵宠（GM/模拟充值抽卡）",
     "弹窗标题 X级 宠物名，X=获得时真实等级（初始通常 1级）；等级属性预览区数值=calcAttrByLevel(当前等级) 口径，与详情页同等级属性一致",
     "运行时", "已改（NewGet L58-60）；v2 补充属性预览断言"),
    ("TC-08", "P1-数值边界", "全品质最大等级显示", "P1", PRE + "，品质5/6/7各有高等级灵宠",
     "分别查看品质5/6/7灵宠升至最大等级2000/最大阶级 level_limit=2000 的显示",
     "最大值显示 2000级；不再出现 200万级 年份量级数字",
     "运行时", "已改"),
    ("TC-09", "P1-排序回归", "共鸣排序", "P1", PRE + "，有多只不同品质/等级灵宠",
     "打开共鸣选择与共鸣弹窗，检查候选列表排序",
     "仍按培养度（quality+等级权重）从高到低，选中主宠后从列表剔除；两个弹窗排序一致",
     "运行时", "已改（Resonance L96-97 / ResonancePop L111-112）"),
    ("TC-10", "P1-排序回归", "魂师可穿戴灵宠推荐排序", "P1", PRE + "，魂师未穿戴灵宠",
     "魂师养成-装备灵宠，查看推荐列表顺序",
     "SoulSpiritMgr L556-586 排序（空闲>穿戴>等级权重）与改版前一致",
     "运行时", "已改（L571-572）"),
    ("TC-11", "P1-数值边界", "灵宠升级/降级边界", "P1", PRE,
     "升到当前阶级 level_limit → 提示进阶；重置后回到 level=1",
     "等级文案全程一致；进度条 0%/100% 边界正确",
     "运行时", "已改"),
    ("TC-12", "P1-嵌入复用", "魂师养成-灵宠位", "P1", PRE,
     "查看 UIHeroDevelop 灵宠位角标；点击跳转灵宠系统",
     "灵宠 Item 等级角标新表现；跳转正常",
     "运行时", "随 Item 自动生效（UIHeroDevelop L82/L519）"),
    ("TC-13", "P1-嵌入复用", "魂师查看", "P1", PRE,
     "查看 UIHeroLookUp 中灵宠 Item",
     "同 TC-12",
     "运行时", "随 Item 自动生效（UIHeroLookUp L69）"),
    ("TC-14", "P1-嵌入复用", "阵容编辑-灵宠槽", "P1", PRE,
     "查看 UILineUpEditFormation 灵宠槽",
     "同 TC-12",
     "运行时", "随 Item 自动生效（L205-207）"),
    ("TC-15", "P1-嵌入复用", "灵宠装备/装备魂师弹窗", "P1", PRE,
     "查看 UISoulSpiritEquip / EquipHero 列表",
     "列表 Item 等级角标新表现",
     "运行时", "随 Item 自动生效（EquipHero L191/Equip L40）"),
    ("TC-16", "P1-抽卡活动", "传灵塔孵化", "P1", PRE + "，传灵塔已开启（sys_open 118）",
     "单抽/十连，覆盖获得重复与新增灵宠",
     "新增时 A6 弹窗新表现（含属性预览）；跑马灯公告「孵化获得灵宠-%s」无年份字样",
     "运行时", "已改；公告文案无年份（cfg_bulletin_msg BigSoulLottery）"),
    ("TC-17", "P1-抽卡活动", "yxact 灵宠抽奖活动", "P1", "活动开启期内",
     "进入 3 变体皮肤（new_year_rebate/thanksgivingday/spring_outing）抽卡",
     "抽卡流程正常；灵宠展示新表现",
     "运行时", "无直接 year 引用，回归"),
    ("TC-18", "P1-抽卡活动", "灵宠图鉴评分/加成", "P1", PRE,
     "图鉴激活/升级流程（AtlasLvUp/AtlasScore）",
     "图鉴等级提升流程正常，评分/加成数值正确",
     "运行时", "bookLevel 体系与 year 无关，回归"),
    ("TC-19", "P2-礼包特权", "灵宠追击基金", "P2", PRE,
     "查看战令成本页（UIWarOrderCost L970）/条件充值礼包（UIYxActCondChargeGift L1017）",
     "礼包名/图标正常，无年份文案",
     "运行时", "无直接 year 引用，回归"),
    ("TC-20", "P2-礼包特权", "灵宠礼包朱厌", "P2", PRE,
     "充值推送礼包（cfg_charge_push_gift_pack L1623）购买→发货",
     "购买发货正常",
     "运行时", "回归"),
    ("TC-21", "P2-礼包特权", "灵宠特权卡", "P2", PRE,
     "特权界面（cfg_privilege_card id=8）查看与领取",
     "界面与领取正常",
     "运行时", "回归"),
    ("TC-22", "P2-杂项回归", "灵宠玩法说明", "P2", PRE,
     "打开灵宠帮助弹窗（cfg_sys_help id=39）",
     "文案为等级表述（「可重置等级和阶级」）；显示正确",
     "运行时", "已改（cfg_sys_help 已改「可重置等级和阶级」）"),
    ("TC-23", "P2-杂项回归", "灵宠详情-满级预览", "P2", PRE,
     "背包灵宠物品-灵宠详情（UIItemTips L118 → DescPop）",
     "「满等级、星级预览」显示 2000级（getMaxLevel 新路径 L132/L244），属性为满级口径；不出现 2000000",
     "运行时", "已改；v2 补充满级预览断言"),
    ("TC-24", "P2-边界确认", "I18N_LEVEL 共享回归", "P2", PRE,
     "抽查宗门等级、好友等级、魂兽追击关卡等级、炼药堂等级",
     "均仍显示 X级 且数值正确（共享 key 未被误改）",
     "运行时", "key 未动（cfg_langs id=360）"),
    ("TC-27", "P2-边界确认", "战斗回归", "P2", PRE,
     "携带灵宠打一场战斗",
     "属性/被动技能生效正常（年份加成属魂环体系，不读灵宠 year/level 显示值）",
     "运行时", "回归"),
    ("TC-28", "P2-交付验收", "静态文案清零验收", "P2", "文案修复后（已满足）",
     "全局搜索 prefab/配置「年份」残留；运行时核查 TC-03/04/05/22 界面",
     "5 处全部改为等级表述（静态复核已通过 ✅）；运行时界面无「年份」字样（含切图底图，文本 dump 抓不到的需截图确认）",
     "静态+运行时", "已改（5 处复核通过，静态部分 ✅）"),
    ("TC-29", "P2-交付验收", "year 字段消费方清零验收", "P2", "任意代码节点（已满足）",
     "全局搜索 cfg_soul_elf_level 相关 .year 取值引用；比对 getCurYearByQuality/getMaxYearByQuality 旧函数名无残留调用",
     "灵宠体系内无任何 .year 消费（例外：配置列保留）；旧函数名 0 引用",
     "静态", "已清零（2026-09-10 复核 0 命中 ✅）"),
]
for i, row in enumerate(CASES, 2):
    for c, v in enumerate(row, 1):
        cell = ws2.cell(i, c, v); cell.alignment = WRAP if c > 3 else CENTER; cell.border = THIN
    st = ws2.cell(i, 9)
    if ("BUG" in str(st.value)) or ("未改" in str(st.value)) or ("必挂" in str(st.value)):
        st.font = BAD_FONT
        for c in range(1, 10):
            ws2.cell(i, c).fill = WARN_FILL
    elif str(st.value).startswith("已改") or "已清零" in str(st.value):
        st.font = OK_FONT

for col, w in zip("ABCDEFGHI", [9, 12, 22, 7, 24, 32, 44, 10, 34]):
    ws2.column_dimensions[col].width = w
ws2.freeze_panes = "A2"

wb.save(OUT)
print("saved:", OUT)
