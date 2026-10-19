# -*- coding: utf-8 -*-
"""生成《法宝UI优化测试用例.xlsx》—— 基于需求 xlsx 解析 + 客户端静态检查结论"""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

OUT = r"E:\workproject\temp_case\cases\法宝UI优化测试用例.xlsx"

HDR_FILL = PatternFill("solid", fgColor="1F4E78")
SEC_FILL = PatternFill("solid", fgColor="DDEBF7")
WARN_FILL = PatternFill("solid", fgColor="FCE4EC")
OK_FONT = Font(color="008000")
BAD_FONT = Font(color="C00000")
HDR_FONT = Font(bold=True, color="FFFFFF")
WRAP = Alignment(vertical="top", wrap_text=True)
CENTER = Alignment(vertical="center", horizontal="center", wrap_text=True)
THIN = Border(*[Side(style="thin", color="B0B0B0")] * 4)

wb = openpyxl.Workbook()

# ============ Sheet1 概览与需求映射 ============
ws = wb.active
ws.title = "概览与需求映射"
ws.append(["法宝UI优化——需求映射与静态检查概览"])
ws["A1"].font = Font(bold=True, size=14)
ws.append([])
ws.append(["需求来源", r"E:\p1-x\planner\换皮需求\界面UI\法宝UI优化.xlsx（3 sheet：规则 / 法宝UI需求 / 法宝UI需求（补）；内嵌图74张已提取至 temp_case\reports\fabao_xlsx_imgs）"])
ws.append(["代码命名", "法宝 = SoulRing；prefab：ui\\prefab\\soulring\\(7个)、soulringdraw\\(9个)；脚本：assets\\scripts\\ui\\soulring、soulringdraw、logic\\soulring"])
ws.append(["检查基线", "按用户确认：只按需求验收当前版本（工作副本），不做修改前 SVN 对比；先静态后运行时"])
ws.append(["总体结论", "美术资源已齐、数据层已就绪（cfg_soul_ring_base 已含 ring_group 1~10 + level + 攻/防/血基础属性字段，SoulRingMgr 已按 ring_group 定位升级表）；但显示层 8 项处理均未或仅部分按 ring_group/阶数改造，详见「静态检查问题清单」"])

r = ws.max_row + 2
ws.cell(r, 1, "一、10 组别资源映射表（处理1 核心，来自需求《规则》sheet）").font = Font(bold=True)
r += 1
map_hdr = ["品质名", "ring_group", "道具框 common_item02_wupinkuangXX", "抽奖光球 effect_ui_hunhuanchou_guangqiuXX", "UI旋转特效(漩涡) effect_ui_fabao_X", "名称色值", "装配技能框 hero_img05_XX", "图鉴框 soul_ring_atlas_panel01_kuangXX"]
for c, v in enumerate(map_hdr, 1):
    cell = ws.cell(r, c, v); cell.font = HDR_FONT; cell.fill = HDR_FILL; cell.alignment = CENTER; cell.border = THIN
QUAL_COLOR = {"灰": "#B4B4B4", "绿": "#00BE6E", "蓝": "#008CFF", "紫": "#A050F0", "黄": "#FFD200", "橙": "#FF9B1E", "珊瑚": "#FF6450", "粉": "#FFB4BE", "红": "#E12832", "彩": "#D21E8C"}
MAP = [
    ("灰", 1, "01", "07", "7", "等美术给", "不需要", "07"),
    ("绿", 2, "02", "01", "1", "等美术给", "white", "01"),
    ("蓝", 3, "03", "02", "2", "等美术给", "yellow", "02"),
    ("紫", 4, "04", "03", "3", "等美术给", "purple", "03"),
    ("黄", 5, "05", "04", "4", "等美术给", "black", "04"),
    ("橙", 6, "09", "08", "8", "等美术给", "orange", "08"),
    ("珊瑚", 7, "10", "09", "9", "等美术给", "coral", "09"),
    ("粉", 8, "11", "10", "10", "等美术给", "pink", "10"),
    ("红", 9, "06", "05", "5", "等美术给", "red", "05"),
    ("彩", 10, "07", "06", "6", "等美术给", "god", "06"),
]
for row in MAP:
    r += 1
    q = row[0]
    vals = [q, row[1], f"common_item02_wupinkuang{row[2]}", f"effect_ui_hunhuanchou_guangqiu{row[3]}", f"effect_ui_fabao_{row[4]}", QUAL_COLOR[q], row[6] if row[6] == "不需要" else f"hero_img05_{row[6]}", f"soul_ring_atlas_panel01_kuang{row[7]}"]
    for c, v in enumerate(vals, 1):
        cell = ws.cell(r, c, v); cell.alignment = CENTER; cell.border = THIN

r = ws.max_row + 2
ws.cell(r, 1, "二、需求界面 → prefab / 脚本 映射（含静态检查现状）").font = Font(bold=True)
r += 1
i_hdr = ["需求界面（需求图出处）", "prefab（候选）", "核心脚本", "涉及处理项", "静态检查现状"]
for c, v in enumerate(i_hdr, 1):
    cell = ws.cell(r, c, v); cell.font = HDR_FONT; cell.fill = HDR_FILL; cell.alignment = CENTER; cell.border = THIN
IFACE = [
    ("法宝装配主界面（规则 B123/D91/B250：阵容头像+法宝列表+一键装配/卸下，GM/战斗测试按钮）", "prefab\\soulring\\UIHeroSoulRing.prefab", "UIHeroSoulRing.ts", "处理1/2/3/4/7", "列表项道具框/名称色/帧特效仍按 quality（L526/563 等）；攻防血未显示；年份文案未改阶"),
    ("法宝列表项/图标（处理1 道具框、处理7 基础属性）", "prefab\\soulring\\UISoulRing.prefab", "UISoulRing.ts L47-93", "处理1/2/7", "Bg=ITEM_QUALITY_BG[quality]、名称色=RING_YEAR_COLOR[quality]、帧特效=FRAME_EFF_RES[quality]；Year=灵力文案；无攻防血节点逻辑"),
    ("技能tips（D63/B63：[3阶][10阶]解锁条件、魂环页签）", "prefab\\uicommon（技能tips）", "UISkillTipsTemp.ts L73-75、UIRingTipsTemp.ts、UIItemSkill.ts L114", "处理2/3/5", "显示『魂环：灵力文案+名称』；未按阶；特性过滤待运行时验证；UIItemSkill L79 技能框硬编码 hero_img05_god 待查"),
    ("激活效果弹窗（E123/J91：[3阶][15阶]…）", "候选 UIRingUnlockSkill.prefab", "UIRingUnlockSkill.ts L61", "处理2/3", "年份文案未改阶"),
    ("法宝详情弹窗-卸下（D63）", "prefab\\soulring\\UISoulRingShow.prefab", "UISoulRingShow.ts L44-67", "处理1/2/4", "已用 ring_group 部分逻辑；Year=灵力；特性显示待验证"),
    ("法宝介绍弹窗（F63：初始阶数+特性列表）", "prefab\\soulring\\UISoulRingDesc.prefab", "UISoulRingDesc.ts L52-151", "处理1/2/4", "部分用 ring_group；年份/名称色仍 quality 残留（L52-63/110-120）"),
    ("替换弹窗（装配位替换）", "prefab\\soulring\\UISoulRingReplace.prefab", "UISoulRingReplace.ts L113-144", "处理1/2", "部分 ring_group；灵力文案残留"),
    ("炼宝抽奖主界面（J63：抽奖结果+已炼化标记+再来1/10次）", "prefab\\soulringdraw\\UISoulRingDraw.prefab", "UISoulRingDraw.ts", "处理1/2", "光球特效映射待运行时验证（当前 6 档 quality 映射）"),
    ("抽奖光球/ scouting（规则 F20 等）", "prefab\\soulringdraw\\UISoulRingDrawScout.prefab 等", "UISoulRingDrawScout.ts L35-48", "处理1", "MAP_RES/EFF_RES 用 godsoulring_img02_coordinate_*+光柱 guangzhu1~5 按 formatYear2 年份档，与需求『光球 guangqiu 按组别』不符"),
    ("恭喜提升-炼宝升级结果（H91/D219：30阶→100阶激活特性）", "prefab\\soulringdraw\\UISoulRingDrawLvShow.prefab / UISoulRingUpgradeResult.prefab", "UISoulRingDrawLvShow.ts L104、UISoulRingUpgradeResult.ts L112", "处理2/6", "年份文案未改阶"),
    ("概率信息弹窗（B219：LV.1→LV.2 九行品质概率色底）", "prefab\\soulringdraw\\UISoulRingDrawLvDesc.prefab", "UISoulRingDrawLvDesc.ts L51-148", "处理6", "cfg_soul_ring_pool_lv_desc 仍 year 字段（装『凡品』文本）+color 色值；脚本用 YearTxt.color——未改组别独立底图"),
    ("图鉴/法宝总览（I35/B282：已拥有法宝 grid+底部组别筛选按钮可滚动）", "prefab\\soulring\\UISoulRingAtlas.prefab + UISoulRingAtlasDesc.prefab", "UISoulRingAtlas.ts L24-140、RingAtlasItem.ts、RingAltasQualityItem.ts", "处理1/2/8", "分类固定 7 档品质 qualityList；卡池条件仅红神一档（atlas_red_god_show_cond）；item 年份/颜色按 quality；排序按 quality"),
    ("获得/新获得弹窗（H63/B91：前往获取）", "候选 UISoulRingDrawRewards.prefab / UIRingTipsTemp", "UISoulRingDrawRewards.ts、UIRingTipsTemp.ts L75", "处理1/2/4", "年份文案未改阶"),
    ("英雄魂环页签（英雄/伙伴详情）", "prefab\\soulring\\UIHeroSoulRing.prefab、UIHeroSoulItem", "UIHeroSoulItem.ts L88-185", "处理1/2/3", "年份文案/颜色未改阶"),
    ("战斗内法宝（SoulRing）", "prefab\\battle\\SoulRing1/2.prefab", "fight\\component\\SoulRingCtl.ts L69、UIRingAnimation.ts L36", "处理1/2", "formatYear2 年份档资源映射，未改组别"),
    ("奖励飘字（法宝相关）", "-", "UISingleRewardMsg.ts L78", "处理2", "formatYear 灵力文案+色"),
    ("强者之路/试炼之路（补：新增人种袋、混元莲花 2 个法宝入口）", "prefab\\phaseObjectives\\UIPhaseObjectives.prefab", "phaseObjectives 相关 ts + cfg", "补-新增", "图 path_to_strength_img04_title19/20 缺失（现仅 title01~18）；立绘 img01_lihui11/12 缺失；图标 fabao_6020_1/6045_1 已存在"),
    ("孙悟空法宝推送礼包（补：调色/玄品→极品/光晕）", "prefab\\wukong_gift\\UIWuKongGift.prefab", "wukong_gift 相关 ts", "补-修改", "图 wukong_gift_img01_fabao01/02+title01~03 已存在；调色是否落实待运行时比对"),
    ("成长礼包（补：『百万灵力』→『150阶法宝』4处）", "未找到引用 prefab（疑似配置/代码动态加载）", "待查（候选 phaseObjectives/成长礼遇）", "补-修改", "图 completiong_gift_pack_img02_name01~04 存在但无 prefab 引用（uuid 全库无命中）"),
    ("推送礼包（补：灵力→阶数 8+3 处）", "prefab\\pushgiftpack\\UIPushGiftPack.prefab + Item1~9", "pushgiftpack 相关 ts + cfg_push_gift_pack", "补-修改", "item04_hunhuan_* 8张图与 img02_01~03 均存在；Item1 _spriteFrame=null+sizeMode=2 → 动态加载，文案改动需运行时确认"),
    ("个人信息详情（任务5 排查项）", "prefab\\personal\\UIPersonalAttrTotal.prefab 等", "scripts\\ui\\personal", "任务5", "personal 脚本与 prefab 均无法宝/魂环引用 → 无需修改，无遗漏"),
]
for row in IFACE:
    r += 1
    for c, v in enumerate(row, 1):
        cell = ws.cell(r, c, v); cell.alignment = WRAP; cell.border = THIN

r = ws.max_row + 2
ws.cell(r, 1, "三、全局受影响调用点（formatYear/formatYear2 全部调用文件——任务5遗漏排查基线）").font = Font(bold=True)
r += 1
CALLERS = "fight/component/SoulRingCtl.ts L69；ui/UISingleRewardMsg.ts L78；ui/commonui/UISkillTipsTemp.ts L74-75；ui/soulring/RingAtlasItem.ts L82、UIHeroSoulItem.ts L88-185、UIHeroSoulRing.ts L526-563、UIRingAnimation.ts L36、UIRingTipsTemp.ts L75-77、UIRingUnlockFeatures.ts L60、UIRingUnlockSkill.ts L61、UISoulRing.ts L51-76、UISoulRingAtlasDesc.ts L49-82、UISoulRingDesc.ts L57-151、UISoulRingReplace.ts L113-144、UISoulRingShow.ts L44-67、UISoulRingUpgradeResult.ts L112、UISourRingAnim.ts L30；ui/soulringdraw/UISoulRingDrawLvShow.ts L104、UISoulRingDrawScout.ts L90-91；ui/widgets/UIItemSkill.ts L114"
cell = ws.cell(r, 1, CALLERS); cell.alignment = WRAP
ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=8)
for col, w in zip("ABCDEFGH", [46, 34, 40, 14, 60, 24, 24, 24]):
    ws.column_dimensions[col].width = w

# ============ Sheet2 测试用例 ============
ws2 = wb.create_sheet("测试用例")
h2 = ["用例编号", "分类", "处理项", "用例标题", "优先级", "前置条件", "操作步骤", "预期结果", "测试方式", "静态检查结论"]
for c, v in enumerate(h2, 1):
    cell = ws2.cell(1, c, v); cell.font = HDR_FONT; cell.fill = HDR_FILL; cell.alignment = CENTER; cell.border = THIN

CASES = [
    # 处理1
    ("TC001", "处理1", "外观按ring_group", "法宝道具框按组别显示（10组遍历）", "P1", "GM将法宝ring_group分别置1~10", "依次查看法宝列表/背包/图鉴中的法宝道具框", "组1灰=wupinkuang01、组2绿=02、组3蓝=03、组4紫=04、组5黄=05、组6橙=09、组7珊瑚=10、组8粉=11、组9红=06、组10彩=07，与映射表一致", "运行时", "未实现：UISoulRing.ts L50/78 用 ITEM_QUALITY_BG[quality]（6档品质）"),
    ("TC002", "处理1", "外观按ring_group", "抽奖光球按组别显示", "P1", "卡池含组1~10法宝；GM置卡池等级达标", "炼宝抽奖1次/10次，观察结算前光球特效", "光球特效按组别显示：组1=guangqiu07、组2=01、组3=02、组4=03、组5=04、组6=08、组7=09、组8=10、组9=05、组10=06", "运行时", "未实现：UIBagConfig L334-339 仅6档quality映射"),
    ("TC003", "处理1", "外观按ring_group", "UI旋转特效（漩涡）按组别显示", "P1", "拥有组1~10法宝", "打开法宝详情/介绍大图观察漩涡特效", "漩涡按组别：组1=fabao_7、组2=1、组3=2、组4=3、组5=4、组6=8、组7=9、组8=10、组9=5、组10=6", "运行时", "未实现：UIBagConfig L300-305 仅6档"),
    ("TC004", "处理1", "外观按ring_group", "装配技能框颜色按组别", "P1", "不同组别法宝已装配到技能", "查看技能图标法宝框颜色", "组2=white、组3=yellow、组4=purple、组5=black、组6=orange、组7=coral、组8=pink、组9=red、组10=god、组1不需要技能框", "运行时", "待验证：UIItemSkill.ts L79 存在硬编码 hero_img05_god"),
    ("TC005", "处理1", "外观按ring_group", "图鉴框按组别显示", "P1", "图鉴收录组1~10法宝", "打开图鉴查看各法宝边框", "组1=kuang07、组2=01、组3=02、组4=03、组5=04、组6=08、组7=09、组8=10、组9=05、组10=06", "运行时", "未实现：UIBagConfig L308-313 仅6档；RingAtlasItem 按 quality"),
    ("TC006", "处理1", "外观按ring_group", "法宝名称色值按组别", "P2", "美术提供名称色值资源后", "查看各组别法宝名称颜色", "名称色值与需求色值表一致（灰#B4B4B4~彩#D21E8C）", "运行时", "阻塞：需求标注『等美术给』，资源未到位"),
    ("TC007", "处理1", "解耦验证", "同品质不同组别→显示不同", "P1", "GM构造两个quality相同、ring_group不同的法宝", "对比两法宝的道具框/图鉴框/光球/漩涡/技能框", "五类外观全部不同（按组别）", "运行时", "未实现（当前外观按quality，同品质必同外观）"),
    ("TC008", "处理1", "解耦验证", "同组别不同品质→显示相同", "P1", "GM构造两个ring_group相同、quality不同的法宝", "对比两法宝五类外观", "外观完全相同", "运行时", "未实现"),
    ("TC009", "处理1", "解耦验证", "修改quality不影响外观", "P1", "GM修改某法宝quality字段", "改前后对比外观", "外观无任何变化（仅ring_group生效）", "运行时", "未实现"),
    ("TC010", "处理1", "资源完整性", "10组特效资源齐全、无缺失/穿模", "P1", "组1~10法宝齐全", "逐一查看道具框/光球/漩涡/图鉴框/技能框显示", "10套资源全部正常加载，无白图/穿模/层级错误", "静态+运行时", "资源文件已齐（wupinkuang01~11/kuang01~10/fabao_1~10/guangqiu1~10/hero_img05_*）；映射代码未接入"),
    ("TC011", "处理1", "兼容", "旧存档quality数据进入新版显示正常", "P1", "使用更新前创建的账号登录", "查看已有法宝各界面外观与文案", "不报错、不白图，外观按ring_group正确显示", "运行时", "cfg同时保留quality与ring_group字段，兼容可行"),
    # 处理2
    ("TC012", "处理2", "年份→阶数", "装配主界面法宝列表项显示『xxx阶』", "P1", "登录有法宝账号", "查看法宝列表项阶数文本", "显示如『200阶』，数值=cfg_soul_ring_base.level相关计算，不出现『灵力/万灵力/年』", "运行时", "未实现：显示灵力文案（Util.formatYear L903-927）"),
    ("TC013", "处理2", "年份→阶数", "法宝详情弹窗阶数显示", "P1", "打开任一法宝详情（卸下弹窗）", "查看名称下方阶数", "如『140阶』，颜色按level档位", "运行时", "未实现"),
    ("TC014", "处理2", "年份→阶数", "法宝介绍弹窗『初始阶数』", "P1", "打开法宝介绍", "查看初始阶数行", "显示『初始阶数：xxx阶』=base.level", "运行时", "未实现（当前显示初始灵力）"),
    ("TC015", "处理2", "年份→阶数", "技能tips解锁条件『[x阶]』", "P1", "查看装配法宝的技能tips", "查看各档解锁条件前缀", "显示[3阶][10阶][50阶]…，不再显示年份/灵力", "运行时", "未实现"),
    ("TC016", "处理2", "年份→阶数", "激活效果弹窗『[x阶]』", "P1", "点击技能查看激活效果", "查看各档文本", "[3阶][15阶][50阶][100阶][150阶]…", "运行时", "未实现"),
    ("TC017", "处理2", "年份→阶数", "获得/新获得弹窗阶数", "P1", "抽奖获得新法宝", "查看获得弹窗标题", "如『3阶[良]济公扇』", "运行时", "未实现"),
    ("TC018", "处理2", "年份→阶数", "抽奖结果列表阶数", "P1", "炼宝抽奖10次", "查看结果网格各item", "显示1阶/6阶等，不显示灵力", "运行时", "未实现"),
    ("TC019", "处理2", "年份→阶数", "炼宝升级结果『30阶→100阶』", "P1", "炼宝升级触发特性激活", "查看恭喜提升弹窗", "如『30阶→100阶』，激活特性文案正确", "运行时", "未实现"),
    ("TC020", "处理2", "年份→阶数", "图鉴item阶数", "P1", "打开图鉴", "查看各法宝item年份位置", "显示阶数", "运行时", "未实现（RingAtlasItem.ts L82 formatYear）"),
    ("TC021", "处理2", "年份→阶数", "推荐法宝条目阶数", "P2", "查看技能tips推荐法宝/装配页推荐", "查看推荐条目", "显示阶数而非灵力", "运行时", "未实现"),
    ("TC022", "处理2", "年份→阶数", "英雄/伙伴魂环页签阶数", "P1", "打开英雄详情法宝页签", "查看魂环信息", "阶数显示正确", "运行时", "未实现（UIHeroSoulItem/UIHeroSoulRing）"),
    ("TC023", "处理2", "年份→阶数", "战斗内法宝文案", "P2", "携带法宝进入战斗", "触发法宝技能/查看战斗内法宝显示", "无年份/灵力残留，阶数正确", "运行时", "未实现（SoulRingCtl.ts L69）"),
    ("TC024", "处理2", "年份→阶数", "全局无『灵力/万灵力/年份』文案残留", "P1", "遍历法宝全部界面", "全界面截图排查", "所有法宝阶数展示处统一为『xxx阶』", "静态+运行时", "未实现：formatYear 全局输出灵力（调用点见概览sheet第三节）"),
    ("TC025", "处理2", "阶数颜色", "阶数文本颜色按level变化", "P1", "GM构造不同level法宝", "对比各档阶数颜色", "颜色按 cfg_soul_ring_year_color 档位（需改造为minLevel/maxLevel后按level取）", "运行时", "未实现：cfg仍minYear/maxYear，颜色硬编码于formatYear"),
    ("TC026", "处理2", "逻辑一致性", "阶数显示与技能加成计算一致", "P1", "构造不同group+level组合", "对比显示阶数与实际技能加成数值", "year字段仍按group+level定位参与计算，显示阶数与加成不冲突", "运行时", "数据层已按ring_group定位升级表（SoulRingMgr L302-328）"),
    # 处理3
    ("TC027", "处理3", "技能特殊效果解锁条件", "解锁条件文案改『xxx阶』", "P1", "查看装配法宝技能的特殊效果", "查看解锁条件文本", "全部为『xxx阶』格式", "运行时", "未实现（依赖formatYear）"),
    ("TC028", "处理3", "解锁状态", "达到阶数即解锁无延迟", "P1", "GM将法宝阶数调至解锁临界", "升阶前后对比技能效果状态", "达到阶数立即生效，无延迟/需重登", "运行时", "待运行时"),
    # 处理4
    ("TC029", "处理4", "特性防剧透", "未解锁特性显示『未解锁+要求阶数』", "P1", "法宝有未达阶数的特性", "查看详情/介绍/获得弹窗特性列表", "未解锁条目仅显示『未解锁』+要求阶数，不显示具体文案", "运行时", "待运行时（UIRingUnlockFeatures 逻辑存在）"),
    ("TC030", "处理4", "特性防剧透", "未达第一条特性门槛显示『暂无特性』", "P1", "法宝阶数低于第一条特性要求", "查看特性区域", "不显示任何特性信息，显示『暂无特性』占位", "运行时", "待运行时"),
    ("TC031", "处理4", "边界", "恰好达到解锁阶数", "P2", "GM调阶数至特性解锁临界值", "查看特性显示", "临界即解锁并显示文案", "运行时", "待运行时"),
    ("TC032", "处理4", "边界", "多条特性部分解锁", "P2", "法宝解锁了部分特性", "查看特性列表", "已解锁显示文案，未解锁脱敏显示", "运行时", "待运行时"),
    ("TC033", "处理4", "一致性", "各界面特性显示规则一致", "P1", "同一法宝", "对比详情/介绍/获得/装配列表/图鉴特性显示", "脱敏规则全界面一致", "运行时", "待运行时"),
    # 处理5
    ("TC034", "处理5", "tips法宝页签", "只显示已激活特性", "P1", "法宝部分特性激活", "打开技能tips法宝页签", "仅列出已激活特性，未激活不出现", "运行时", "待运行时"),
    ("TC035", "处理5", "边界", "无已激活特性时页签表现", "P2", "法宝无激活特性", "打开tips法宝页签", "按设计显示（空态/占位），无异常", "运行时", "待运行时"),
    ("TC036", "处理5", "边界", "全部激活时显示完整", "P2", "法宝全部特性激活", "打开tips法宝页签", "特性完整显示无截断", "运行时", "待运行时"),
    # 处理6
    ("TC037", "处理6", "概率信息UI", "概率行文字底按组别独立资源", "P1", "打开概率信息弹窗", "查看各行底图", "每行使用按ring_group独立配置的底图资源，非色值方案", "运行时", "未实现：cfg仍year字段+color色值，脚本用YearTxt.color"),
    ("TC038", "处理6", "概率信息UI", "10个组别资源全覆盖", "P1", "卡池升至高等级", "逐级查看概率信息", "10个组别行底图全部正确显示", "运行时", "未实现"),
    ("TC039", "处理6", "概率信息UI", "旧色值配置废弃不生效且不异常", "P2", "保留旧color字段数据", "打开概率信息", "色值不再参与显示，无报错", "运行时", "未实现"),
    ("TC040", "处理6", "概率信息UI", "升级预览LV.1→LV.2概率正确", "P2", "查看炼宝升级预览", "对比前后概率数值", "数值与cfg_soul_ring_pool_lv_desc一致", "运行时", "待运行时（数值链路正常）"),
    # 处理7
    ("TC041", "处理7", "列表基础属性", "法宝列表显示攻/防/生命且与配置一致", "P1", "拥有多个法宝", "查看列表项属性数值", "显示攻击/防御/生命，=cfg_soul_ring_base.attr_*Base（含加成计算）", "运行时", "未实现：UISoulRing 列表项无属性显示逻辑（cfg字段已备）"),
    ("TC042", "处理7", "列表基础属性", "属性与角色面板一致", "P1", "装配法宝后", "对比法宝列表属性与角色面板加成", "数值一致无出入", "运行时", "待运行时"),
    ("TC043", "处理7", "布局", "名称移至图标上方+属性长文本不遮挡", "P2", "构造长名称/大数值法宝", "查看列表布局", "名称位于icon上方，文本不遮挡不截断", "运行时", "待运行时"),
    # 处理8
    ("TC044", "处理8", "图鉴分类", "分类按钮数量=ring_group数（10）+全部", "P1", "打开图鉴", "查看分类按钮", "按钮数量按组别动态生成（10个+全部），非固定品质档", "运行时", "部分实现：当前固定7档品质qualityList"),
    ("TC045", "处理8", "图鉴分类", "分类按钮可滚动且流畅", "P2", "按钮超出一屏", "左右滚动分类栏", "可滚动，无卡顿，按钮不重叠", "运行时", "部分实现（TypeList为Toggle容器，滚动待验证）"),
    ("TC046", "处理8", "图鉴筛选", "卡池未达标点击不可选中并有提示", "P1", "GM将卡池等级调低于某组门槛", "点击该组分类按钮", "不可选中，提示『炼宝等级达到xx级可查阅』，保持原选中", "运行时", "部分实现：仅红神一档有atlas_red_god_show_cond条件，需扩展到每档"),
    ("TC047", "处理8", "图鉴筛选", "达标可选中且筛选结果与组别一一对应", "P1", "卡池达标", "逐个点击组别按钮", "选中态正确，列表仅显示该组法宝", "运行时", "部分实现（当前按quality筛选）"),
    ("TC048", "处理8", "图鉴筛选", "切换/取消选中正常+滚动边界", "P2", "反复切换分类", "切到首/尾按钮、取消选中", "显示正确无残留，首尾滚动正常", "运行时", "待运行时"),
    # 补需求
    ("TC049", "补需求", "path_to_strength", "新增人种袋/混元莲花2个法宝入口", "P1", "进入强者之路界面", "查看新增入口图、文案、图标与跳转", "显示title19（人种袋fabao_6020_1）/title20（混元莲花fabao_6045_1），文案『领混元莲花-解锁更多技能效果』，点击跳转正确", "运行时", "阻塞：path_to_strength_img04_title19/20.png、img01_lihui11/12.png 缺失（现仅title01~18）；图标6020/6045已存在"),
    ("TC050", "补需求", "wukong_gift", "孙悟空礼包调色/玄品改极品/光晕调色", "P2", "触发孙悟空法宝推送礼包", "对比需求图查看文字底、品质标志、光晕", "fabao01文字底与品质标志已调色；fabao02『玄品』改『极品』；两者光晕调色正确", "运行时", "待验证：相关图均已存在（wukong_gif目录）"),
    ("TC051", "补需求", "completiong", "『百万灵力』改『150阶法宝』（4处）", "P1", "打开成长礼包界面", "查看4个礼包名称图", "全部显示『150阶法宝』新图（name01~04）", "运行时", "待验证：新图存在但未被任何prefab引用（疑似配置驱动，接入点待运行时确认）"),
    ("TC052", "补需求", "push_gift_pack", "推送礼包8处灵力文案改阶数", "P1", "触发对应推送礼包", "逐一查看礼包图", "六十万灵力→100阶、三十万→80阶、七万→40阶、一万→10阶、一千→5阶、十万→60级、一万→5阶、一万→20阶", "运行时", "待验证：hunhuan图8张已存在，Item1~9为动态加载"),
    ("TC053", "补需求", "push_gift_pack", "img02_01~03 文案改阶数（3处）", "P2", "触发对应推送礼包", "查看3张图", "三十万灵力→80阶、六十万→120阶、八十万→120阶", "运行时", "待验证"),
    # 回归
    ("TC054", "回归", "界面打开", "法宝主界面打开", "P1", "账号1351/1352已解锁法宝", "从主界面点击法宝入口", "界面正常打开，页签完整，无报错", "运行时(e2e)", "可执行"),
    ("TC055", "回归", "按钮点击", "炼宝：抽奖1次/10次/跳过动画", "P1", "炼宝材料足够", "分别点击炼宝1次/10次、跳过动画", "扣费正确、出奖正确、动画可跳过", "运行时(e2e)", "可执行"),
    ("TC056", "回归", "界面打开", "图鉴打开/关闭", "P1", "-", "打开图鉴后返回", "正常开关，数据完整", "运行时(e2e)", "可执行"),
    ("TC057", "回归", "界面打开", "法宝总览打开", "P1", "-", "点击法宝总览", "正常打开，显示已拥有/未拥有", "运行时(e2e)", "可执行"),
    ("TC058", "回归", "按钮点击", "装配/卸下/替换/一键装配/一键卸下/全员升级/灵力优先", "P1", "有可装配法宝与技能", "逐一点击上述按钮", "功能正常，状态同步，无卡死", "运行时(e2e)", "可执行"),
    ("TC059", "回归", "界面打开", "技能tips打开", "P1", "-", "点击已装配技能", "tips正常弹出，法宝页签可切", "运行时(e2e)", "可执行"),
    ("TC060", "回归", "按钮跳转", "『前往获取』跳转（jump_id）", "P1", "未拥有某法宝", "在获得弹窗/图鉴点前往获取", "跳转到cfg配置的目标界面", "运行时(e2e)", "可执行（cfg_soul_ring_base.jump_id/jump_btn_name已配）"),
    ("TC061", "回归", "按钮跳转", "『前往装配』跳转", "P2", "抽奖结果页", "点击前往装配", "跳转到装配界面并定位", "运行时(e2e)", "可执行"),
    ("TC062", "回归", "按钮点击", "概率信息打开/升级按钮", "P1", "炼宝次数/开服天数达标", "打开概率信息并点升级", "正常升级，概率刷新", "运行时(e2e)", "可执行"),
    ("TC063", "回归", "调试入口", "GM面板/战斗测试/主线测试入口正常", "P2", "GM账号", "点击界面GM按钮", "GM面板正常打开可操作", "运行时(e2e)", "可执行"),
    ("TC064", "回归", "界面打开", "英雄/伙伴详情法宝页签打开", "P1", "-", "打开英雄详情切法宝页签", "正常显示魂环信息", "运行时(e2e)", "可执行"),
    ("TC065", "回归", "战斗", "战斗内法宝技能正常释放", "P1", "装配法宝进入战斗", "触发法宝技能", "特效/数值正常，无报错", "运行时(e2e)", "可执行"),
    # 异常
    ("TC066", "异常", "容错", "配置缺字段不崩溃（quality/ring_group缺失）", "P1", "GM临时删配置字段", "打开法宝各界面", "降级显示或跳过，不崩溃不白屏", "静态+运行时", "需关注：当前代码大量直接索引quality"),
    ("TC067", "异常", "容错", "ring_group越界（0/11/负数/超大小数）", "P1", "GM构造越界ring_group", "查看该法宝各界面", "走默认降级资源，不崩溃不串档", "运行时", "待验证"),
    ("TC068", "异常", "特殊逻辑", "组6（彩/神魂灵）特殊逻辑保留正确", "P1", "查看组6法宝", "对比名称后缀/颜色/资源映射", "原『万灵力』特殊分支按新需求处理（组6=fabao_6/guangqiu06/kuang06），无逻辑冲突", "运行时", "注意：Util.formatYear L904 有 ring_group==6 特殊分支，改造时勿破坏"),
    ("TC069", "异常", "兼容", "版本更新前后数据无缝（旧存档/离线数据）", "P1", "更新前账号", "更新后登录查看法宝数据", "阶数/外观/特性/图鉴进度无缝迁移", "运行时", "待验证"),
    ("TC070", "异常", "边界", "卡池等级边界（0级/恰好达标/超高档）", "P2", "GM调卡池等级", "验证图鉴筛选与概率信息", "各边界表现正确", "运行时", "待验证"),
    ("TC071", "异常", "性能", "图鉴滚动帧率/多法宝特效同屏", "P2", "法宝数量较多", "快速滚动图鉴、多特效同屏", "帧率稳定无明显发热", "运行时", "待验证"),
    ("TC072", "异常", "网络", "弱网/断网打开法宝界面", "P2", "代理工具模拟弱网", "打开各法宝界面", "有loading/重试提示，不崩溃不假死", "运行时", "待验证"),
    ("TC073", "异常", "适配", "多分辨率UI不错位", "P2", "多分辨率/刘海屏", "遍历法宝界面截图比对", "无错位/裁切/按钮不可点", "运行时", "待验证"),
]
for i, row in enumerate(CASES, 2):
    for c, v in enumerate(row, 1):
        cell = ws2.cell(i, c, v); cell.alignment = WRAP; cell.border = THIN
    concl = row[-1]
    if any(k in concl for k in ("未实现", "阻塞")):
        ws2.cell(i, 10).font = BAD_FONT
    elif "可执行" in concl or "已齐" in concl:
        ws2.cell(i, 10).font = OK_FONT
for col, w in zip("ABCDEFGHIJ", [9, 9, 15, 30, 7, 20, 30, 40, 12, 42]):
    ws2.column_dimensions[col].width = w
ws2.freeze_panes = "A2"
ws2.auto_filter.ref = f"A1:J{ws2.max_row}"

# ============ Sheet3 静态检查问题清单 ============
ws3 = wb.create_sheet("静态检查问题清单")
h3 = ["编号", "严重程度", "违反需求", "问题描述", "证据（文件:行号）", "建议"]
for c, v in enumerate(h3, 1):
    cell = ws3.cell(1, c, v); cell.font = HDR_FONT; cell.fill = HDR_FILL; cell.alignment = CENTER; cell.border = THIN
ISSUES = [
    ("Q01", "严重", "处理1", "漩涡特效映射仍为6档品质（fabao_1~6），需求为10组别（组1=fabao_7…组6=fabao_8、组7=9、组8=10、组9=5、组10=6）", "UIBagConfig.ts L300-305（FRAME_EFF_RES quality→fabao_1~6）", "新建 ring_group→资源 10 档映射表并替换读取点"),
    ("Q02", "严重", "处理1", "图鉴框映射仍为6档品质（kuang01~06），需求10组别（组1=kuang07、组6=08、组7=09、组8=10）", "UIBagConfig.ts L308-313", "同上"),
    ("Q03", "严重", "处理1", "抽奖光球映射仍为6档品质（guangqiu1~6），需求10组别（组1=guangqiu07、组6=08、组7=09、组8=10）", "UIBagConfig.ts L334-339", "同上"),
    ("Q04", "严重", "处理1", "法宝列表项道具框/名称色/帧特效仍按quality读取", "UISoulRing.ts L50/55/57、L78/82/84（ITEM_QUALITY_BG/RING_YEAR_COLOR/FRAME_EFF_RES[quality]）", "改为按 ring_group 读取新映射"),
    ("Q05", "严重", "处理2", "formatYear 输出『灵力/万灵力』文案且颜色硬编码，未改『xxx阶』；全局30+调用点受影响", "Util.ts L903-927（含 ring_group==6 特殊分支 L904-907）；调用点见概览sheet第三节", "改造为读 base.level 输出『xxx阶』，颜色走 cfg_soul_ring_year_color（字段改 minLevel/maxLevel）"),
    ("Q06", "中", "处理2", "cfg_soul_ring_year_color 仍为 minYear/maxYear 字段，需求改 minLevel/maxLevel", "cfg\\soul_ring\\cfg_soul_ring_year_color.json", "策划导出表结构同步修改，代码取值点同步"),
    ("Q07", "严重", "处理6", "cfg_soul_ring_pool_lv_desc 仍用 year 字段（装『凡品』文本）+color 色值；需求改 ring_group+独立底图资源+色值废弃", "cfg\\soul_ring\\cfg_soul_ring_pool_lv_desc.json；UISoulRingDrawLvDesc.ts L51-148（YearTxt.color 赋值）", "导出表 year→ring_group；UI 行渲染改为加载独立底图 sprite"),
    ("Q08", "中", "处理8", "图鉴分类按钮固定7档品质 qualityList，需求按 ring_group 动态10档+可滚动；卡池解锁条件仅红神一档，需求每档都有", "UISoulRingAtlas.ts L24-31（qualityList）、L60-64（atlas_red_god_show_cond 仅 RED_GOD）", "分类键改 ring_group，按钮资源 RING_QUALITY_ATLAS_FILTER_RES 扩展10档，逐档配置卡池条件（cfg_soul_ring_misc）"),
    ("Q09", "中", "处理1/8", "图鉴item与分类按钮组件仍按quality取资源/颜色/排序", "RingAtlasItem.ts L70-82（formatYear+quality色）、RingAltasQualityItem.ts L41-45、UISoulRingAtlas.ts initTypeList 排序", "同步改 ring_group"),
    ("Q10", "中", "处理1", "抽奖 scouting 资源映射用光柱 guangzhu1~5+coordinate 按 formatYear2 年份档，与需求『光球 guangqiu 按组别』不一致", "UISoulRingDrawScout.ts L35-48、L90-91", "确认该套资源是否保留；若废弃则切换为组别→guangqiu 映射"),
    ("Q11", "严重", "处理7", "法宝列表项无攻击/防御/生命基础属性显示逻辑（cfg字段 attr_AttackBase/attr_DefenseBase/attr_MaxHpBase 已配好）", "UISoulRing.ts setData 全文无属性节点；需求图 B250 列表项含属性", "列表模板增加属性节点并取值渲染"),
    ("Q12", "中", "处理1", "技能框存在硬编码 hero_img05_god，未按组别", "UIItemSkill.ts L79", "改为按装配法宝 ring_group 映射"),
    ("Q13", "阻塞", "补需求", "path_to_strength_img04_title19/20.png 缺失（现有 title01~18）", "images\\phase_objectives\\ 目录", "催美术补图后再接入 prefab/配置"),
    ("Q14", "阻塞", "补需求", "path_to_strength_img01_lihui11/12.png 缺失（仅 god_star_gift 下同名前缀不同资源）", "全库搜索无 path_to_strength_img01_lihui1x", "催美术补立绘"),
    ("Q15", "待查", "补需求", "completiong_gift_pack_img02_name01~04.png 无任何 prefab 引用（uuid 全库无命中）——疑似配置/代码动态加载，接入点未确认", "uuid be5e2066-2058-4a90-8f3e-b1f6eceb883c 全 prefab 目录无命中", "运行时确认成长礼包界面取图路径后验证新图是否生效"),
    ("Q16", "阻塞", "处理1", "名称色值『等美术给』未到位", "需求《规则》G10-G19", "外部依赖，到位后补验 TC006"),
    ("Q17", "低", "处理2/3", "soulring 全部脚本无『阶』文案字符串——佐证阶数改造未开始", "scripts\\ui\\soulring*、logic\\soulring 全文 grep 无『阶』", "改造时统一走 formatYear/新格式化函数，避免散落硬编码"),
]
for i, row in enumerate(ISSUES, 2):
    for c, v in enumerate(row, 1):
        cell = ws3.cell(i, c, v); cell.alignment = WRAP; cell.border = THIN
    sev = row[1]
    if sev == "严重":
        ws3.cell(i, 2).font = BAD_FONT
    elif sev == "阻塞":
        ws3.cell(i, 2).font = Font(bold=True, color="7030A0")
for col, w in zip("ABCDEF", [7, 9, 11, 52, 52, 40]):
    ws3.column_dimensions[col].width = w
ws3.freeze_panes = "A2"
ws3.auto_filter.ref = f"A1:F{ws3.max_row}"

wb.save(OUT)
print("saved:", OUT)
print("cases:", len(CASES), "issues:", len(ISSUES))
