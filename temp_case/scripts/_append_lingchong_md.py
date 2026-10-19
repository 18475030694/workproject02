# -*- coding: utf-8 -*-
"""一次性：向灵宠用例 MD 追加 E2E 执行结果章节（第六章）"""
MD = r"E:\workproject\temp_case\reports\灵宠年份改等级_测试用例.md"

addition = '''

---

## 六、E2E 执行结果（2026-09-10 16:55，账号4451 @ S5）

> 报告目录：`E:\\workproject\\reports\\e2e_soulspirit_20260910_165528\\`（data.json + screenshots 11 张）
> Excel 回填：`temp_case/cases/灵宠年份改等级_测试用例_v3_已回填.xlsx`（Sheet3 执行概要+检索结论）

### 6.1 结果汇总

| 原始 | 复判后 | 说明 |
|---|---|---|
| PASS 5 | 直接通过 9 | +TC-06（截图佐证显示正确）、TC-18（脚本误报，见 6.3）、TC-28/29（静态验收） |
| FAIL 12 | 待人工复核 8 | TC-01/02/08（抽卡弹窗遮挡致文本读取为空）、TC-03/05/09/15/22（脚本入口未打开） |
| FAIL 12 | 疑似产品问题 1 | **TC-23**：DescPop onShow 抛 `Cannot read properties of null (reading 'quality')`（TC23_descpop.png），需人工从背包→灵宠物品→详情复核 |
| FAIL 12 | 部分通过 1 | TC-24：I18N_LEVEL key 验证通过（「5级」），好友界面脚本未开 |
| N/A 7 | 未执行 10 | TC-04/13/14/17/19/20/21 + TC-10（脚本未覆盖） |

### 6.2 数据准备（GM）

set_mainline_stage=5000 开启灵宠系统；传灵塔 30 连（品5×2/品6×1/品7×1）；uuid47→lv30/ph2、uuid48→lv2000/ph199（满级满阶）、uuid49→lv55/ph5、uuid46 保持 lv1/ph0

### 6.3 错误码佐证（cfg_err_code.json）

- **2312**「灵宠已是当前阶最大等级」→ TC-11 升级上限拦截正确
- **2322**「灵宠图鉴积分已领取」→ TC-18 book_score 报错实为脚本重复领取同一节点，**非产品缺陷**
- **2324**「积分不足，无法升级」→ TC-18 book_level_up 拦截正确
- 灵宠 2312~2325 错误码文案全部为等级表述，无年份

### 6.4 全局「年份」残留检索（灵宠口径清零确认）

| 范围 | 结论 |
|---|---|
| export 配置 / cfg_langs 飘字 | 0 命中 |
| cfg_err_code 错误码 | 灵宠 2312~2325 无年份 |
| server lua（11 处） | 魂环/技能/战斗日志，非灵宠，保留 |
| client ts（15 处） | 魂环 SoulRingMgr/SkillHelper/ItemHelper(showYear 魂环 tips 专用)/Buff/战斗、坐骑 UIMountFeedReset「年份回到初始」、DateTS/SoulBone 注释，非灵宠，保留 |
| resources（6 处） | cfg_sys_help id=23 装备「装备年份」、cfg_sys_help_mix_img+UISystemMixImgHelp.prefab 法宝、UIRingUnlockSkill.prefab 魂环、UIMountFeed* 坐骑，非灵宠，保留 |
| 灵宠道具 tips（cfg_item.json） | 灵宠养料/灵宠印记/共鸣水晶/技能书宝箱/红灵宠宝箱/自选礼包/灵宠卡 desc 全部无「年份」；切图类标题文本抓不到，建议截图抽查 |
| **灵宠体系（代码+prefab+配置）** | **0 残留** |

### 6.5 待人工复核清单

1. **TC-23 详情弹窗**：背包→灵宠物品→详情 人工打开验证是否复现 null.quality
2. TC-01/02/08：关掉「恭喜获得」弹窗复看主界面/角标/满级显示
3. TC-03/04/05/09/15/22：真实入口人工走 进阶→结果→重置→共鸣→装备→玩法说明
4. TC-24：人工抽查宗门/好友/魂兽追击/炼药堂等级文案
5. 礼包/卡片切图标题截图抽查（文本检索盲区）
'''

with open(MD, 'a', encoding='utf-8') as f:
    f.write(addition)
print('appended ok')
