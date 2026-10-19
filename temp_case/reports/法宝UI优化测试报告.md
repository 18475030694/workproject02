# 法宝 UI 换皮测试报告

- 测试日期：2026-09-07
- 需求文档：`E:\p1-x\planner\换皮需求\界面UI\法宝UI优化.xlsx`（只读）
- 代码基线：`E:\p1-x\trunk\client`（8/24 为最新工作树；tag_new 为 8/10 旧分支，未纳入）
- 测试账号：1351 / 1352（已解锁法宝 + GM 权限），服 S5
- 方式：静态检查（prefab/config/代码 rg）+ 运行时 E2E（Playwright + QA Bridge `http://localhost:7456?qa=1`）
- 判错口径：E2E 以登录后 console.error 为基线统计【新增】错误；环境噪声（资源版本号不匹配、cfg_soul_bone 索引等 31 条）单独归档不计失败

---

## ① 测试用例交付

| 交付物 | 位置 |
|---|---|
| 测试用例（73 条，含映射、检查点、异常用例） | `E:\workproject\temp_case\cases\法宝UI优化测试用例.xlsx` |

## ② 需求图片 → prefab 映射 + 静态检查

映射范围（需求内嵌图 → 界面/prefab）：炼宝主界面（UISoulRingDraw）、概率弹窗（UISoulRingDrawLvDesc）、图鉴（UISoulRingAtlas）、图鉴详情（UISoulRingAtlasDesc）、法宝装配（UIHeroSoulRing）、tips 类（UIRingTipsTemp / UISoulRingDesc）。

静态检查结果（`temp_case\scripts\fabao_config_check.py` → `fabao_config_check_report.json`）：

| 检查项 | 结果 |
|---|---|
| ring_group 合法性 / 资源映射（KUANG、WUPIN、GUANGQIU、FABAO_FX） | 通过（映射表见 `temp_case\reports\fabao_xlsx_dump.txt`） |
| `cfg_soul_ring_icon` 完整性 | **缺 6112、6113 图标**（新档位资源缺失） |
| 文案改造（年份→阶、去灵力） | **代码层大面积未改造**（见⑤） |

## ③ 运行时回归（界面打开 / 按钮点击 / 跳转）

报告：`E:\workproject\reports\e2e_fabao_20260907_112629`（7/11 通过）、探测轮 `e2e_fabao_probe_20260907_112803`。

| 用例 | 结果 | 说明 |
|---|---|---|
| 登录进主城（1351/S5） | PASS | |
| TC040 概率弹窗打开 UISoulRingDrawLvDesc | PASS | 但概率行仍为品质名行（精品/良品…）=未改造证据 |
| TC056 图鉴页签打开 UISoulRingAtlas | PASS | |
| TC044 图鉴分类按钮数量 | PASS(取证) | **当前固定 7 品质档**，未改 10 组别=未达标证据 |
| TC014 图鉴详情打开 | PASS(取证) | 显示"**初始灵力：1000年**"=未改造证据 |
| TC057 法宝装配界面打开 UIHeroSoulRing | PASS | |
| TC063 GM 面板 | FAIL→已澄清 | 节点名为 `uiGM`，探测轮 PASS，非产品问题 |
| TC055 炼宝页签 | FAIL→已澄清 | 脚本断言口径问题；异常轮 EX02 以 openUI+文本双证据 PASS |
| **TC024 全界面无『灵力/万灵力』残留（处理2）** | **FAIL** | 实测发现 "**80万年**" 残留 |
| **TC046 卡池未达标点击分类不可选中+提示** | **FAIL** | 两轮均未捕获提示 |

## ④ 异常场景测试

配置校验（`fabao_config_check_report.json`）+ E2E 异常轮：`E:\workproject\reports\e2e_fabao_exception_20260907_144842`（最终轮；113809 为首版含噪声误判，114130 为修正轮，均存档）。

| 用例 | 结果 | 关键证据 |
|---|---|---|
| EX000 登录 | PASS | |
| EX01 图鉴反复开关 | FAIL | 图鉴可正常开关（open=262/562 节点），但**新增 `cfg_soul_ring_pool 索引0` 配置错误** |
| EX02 炼宝 TabView 打开（子 UI 带出 parent） | PASS | 炼宝文本正常 |
| EX03 图鉴筛选按钮连点 | FAIL | 筛选触发第 2 条 `cfg_soul_ring_pool 索引0` |
| EX04 图鉴点击法宝→详情打开 | FAIL | 详情可打开（42 个 item、44 节点），但触发**未捕获异常**（见缺陷 1） |
| EX05 详情关闭回图鉴 | FAIL | 图鉴恢复（606 节点），失败仅因前序新增异常 |
| EX06 全程无未捕获 JS 异常 | FAIL | **4 条新增**：cfg_soul_ring_pool 索引0 ×3 + `pageerror: Cannot read properties of undefined (reading 'ring_id')` |

新增异常明细（`report.json` js_errors）：
- `表中找不到此索引，表名为：cfg_soul_ring_pool 索引为：0`（图鉴打开/筛选/详情均触发）
- `pageerror: Cannot read properties of undefined (reading 'ring_id')`（点击图鉴项打开详情时）

## ⑤ 全局遗漏未修改点清单（法宝相关界面）

| # | 位置 | 问题 |
|---|---|---|
| 1 | `scripts/utils/Util.ts` | `formatYear/formatYear2` 年份体系函数仍为文案主链路 |
| 2 | `ui/soulring/UISoulRingAtlasDesc.ts` | L49 `Year_txt` 年份、L52 "初始灵力："、L51 `RING_YEAR_COLOR[quality]` 按品质取色（应按 ring_group）、L63/90 upgrade 表 `year` 字段 |
| 3 | `ui/soulring/UISoulRingDesc.ts`（技能tips法宝页签） | L120 `YearTxt` 年份、L57/78/82/138/151 formatYear；**处理5：L125-135 仍显示全部特性仅灰/亮区分，未做"只显示已激活"**；L159 已用 ring_group（部分完成） |
| 4 | `ui/soulring/UIHeroSoulRing.ts` | L548 `Util.formatYear(updgradeConf.year, …)` |
| 5 | `ui/soulring/UIHeroSoulItem.ts` | L154 同上 |
| 6 | `ui/soulring/UIRingTipsTemp.ts` | L75 灵力文案 `YearAdd_txt` + formatYear |
| 7 | `ui/widgets/UIItemSkill.ts`（背包/道具tips） | L114 `Year_txt` + formatYear |
| 8 | `fight/component/SoulRingCtl.ts`（战斗内法宝） | L38/67 `skillInfo.year`、L69 formatYear2、L72 `SOULRING_RES[year]` 图标仍按年份索引 |
| 9 | `ui/UISingleRewardMsg.ts`（奖励弹窗） | L78 `formatYear(...).color` 品质色 |
| 10 | 图鉴筛选（UISoulRingAtlas） | 固定 7 品质档，未按 10 组别（ring_group）改造 |
| 11 | 概率弹窗（UISoulRingDrawLvDesc） | 概率行仍为品质名（精品/良品…） |
| 12 | 已核实无遗漏 | 个人信息详情/role/rolegongfa 界面无法宝引用，无需修改 |

## ⑥ 真实缺陷清单

| 级别 | 缺陷 | 复现 | 根因定位 |
|---|---|---|---|
| P0 | 点击图鉴法宝项打开详情触发未捕获异常 `Cannot read properties of undefined (reading 'ring_id')`，详情数据渲染中断风险 | 图鉴→点击任一法宝项（EX04） | `RingAtlasItem.ts:47-48` `ringMap[gift_id]` 取不到数据时传值链 → `UISoulRingAtlasDesc.ts:42` 读 `ringData.ring_id`；与新档位数据链不完整同源 |
| P1 | `cfg_soul_ring_pool` 索引 0 缺失，图鉴打开/筛选/详情均报配置错误 | 打开图鉴即触发（EX01/EX03/EX04） | `UISoulRingAtlasDesc.ts:47` `cfg_soul_ring_pool[pool_level][ringId]`；卡池表 0 档缺失 |
| P1 | 6112、6113 缺 `cfg_soul_ring_icon` 图标 | 静态配置校验 | 新增组别资源未配齐 |
| P2 | "灵力/年份"文案残留（处理1/处理2 未完成）：实测 "80万年"、"初始灵力：1000年" 等 | TC024 / TC014 / 探测轮 | ⑤ #1-#9 全链路 |
| P2 | 图鉴筛选未按 10 组别改造（仍 7 品质档） | TC044 | ⑤ #10 |
| P2 | 概率弹窗按品质名行展示，未按组别独立底图 | TC037/TC040 | ⑤ #11 |
| P2 | 未达标组别点击分类无"不可选中+提示" | TC046（两轮） | 图鉴筛选交互未实现 |

## 结论与建议

1. 换皮改造完成度低：界面打开/跳转主流程正常（EX02、TC056、TC057 等），但**文案体系（年份/灵力→阶）、品质→组别（10 档 ring_group）的 UI 改造基本未落地**，且新档位配置链不完整（卡池索引、图标、详情数据）导致 P0 崩溃。
2. 建议修复顺序：P0 崩溃 → cfg_soul_ring_pool/6112/6113 配置补齐 → 文案全链路替换（Util.formatYear 及 ⑤ 清单）→ 图鉴筛选/概率行按组别改造 → 处理5 特性显示规则。
3. 测试资产：用例 `temp_case\cases\法宝UI优化测试用例.xlsx`；脚本 `harness\e2e_fabao.py`、`harness\e2e_fabao_exception.py`、`temp_case\scripts\fabao_config_check.py`；全部报告与截图在 `E:\workproject\reports\`。
