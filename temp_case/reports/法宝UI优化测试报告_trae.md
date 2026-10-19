# 法宝 UI 优化测试报告（trae 全量重测 · 2026-09-08 / 二轮复核 · 2026-09-09 / 公告滚屏R3+推送礼包 · 2026-09-09）

- 测试日期：2026-09-08
- 需求文档：`E:\p1-x\planner\换皮需求\界面UI\法宝UI优化.xlsx`（只读）
- 代码基线：`E:\p1-x\trunk\client`
  - 9/7 18:54：UIRingUnlockFeatures.ts / UIRing.ts
  - 9/8 12:04~15:11：Util.ts、UISoulRing、UISoulRingDesc、UISoulRingShow、UISoulRingAtlasDesc、UIRingTipsTemp、RingAltasQualityItem、RingAtlasItem、UIHeroSoulRing 等 7+ 个法宝脚本 + 配置数据化
  - **9/8 17:10（本轮新发现）**：`UISoulRingAtlas.ts`（VList 虚拟滚动 + 分类 ToggleContainer + 锁定提示交互）、`UIHeroSoulItem.ts`（Year_rich 改 formatLevel 富文本）
- 测试账号：1353 @ S5（GM 解锁）/ 1351 @ S5（原生解锁）
- 测试方式：**静态源码/配置核对（权威）** + 运行时 E2E 三轮（Playwright + QA Bridge `http://localhost:7456?qa=1`）
- 交付文件：
  - 用例结论：`temp_case\cases\法宝UI优化测试用例_trae_v2.xlsx`（73/73 回填，含二轮复核+战斗回归；v1 为 09-08 一轮存档）
  - 本报告：`temp_case\reports\法宝UI优化测试报告_trae.md`
  - 运行时取证：`reports\e2e_fabao_v3*_2026090*`（二轮七轮 v3b~v3h）+ `reports\e2e_fabao_battle*_2026090*`（战斗回归三轮 battle1~3，见 ②C）+ `reports\fabao_r3_bulletin_*` / `reports\fabao_pack_ui_evidence_*`（公告滚屏 R3 + 推送礼包，见 ②D）

---

## ⚠️ 0. 环境重要结论：客户端预览新旧 chunk 混杂（D1，仍阻塞部分运行时取证）

**运行时文本证据需区分「新代码已生效」与「旧 chunk 残留」两类**，本轮已用探针实锤：

| 证据 | 结果 | 判定 |
|---|---|---|
| `Util.formatLevel(50,6001)` 运行时直调 | 返回 `50阶`；`formatLevel(150,6031)`→`150阶` | **新 Util 已生效** |
| `Util.formatYear(1000,6001)` 运行时直调 | 返回 `1000灵力`（灵力文案仅在死代码路径） | 处理2 静态结论佐证 |
| 抽奖页『新加入奖池』列表运行时文本 | `1阶` / `5阶`（另有一个残留 `300年`） | 新 chunk 生效 |
| 图鉴 `RingAtlasItem/Year` 运行时文本 | `80万年`（×N，静态源码 L85 已是 formatLevel） | **旧 chunk 残留** |
| 图鉴详情 `初始阶数：1000年` | 标签新（初始阶数）、数值旧（年） | 旧 chunk 残留 |
| packer-driver sourcemap（图鉴 chunk） | 含 `TypeList_toglist`/`RING_QUALITY_ATLAS_FILTER_RES`（旧符号），17:10 新源码为 `TogContent_toglist`/`VList`/`atlas_filter_res` | **图鉴预览 chunk 落后于 17:10 源码** |

**结论：静态核对为权威判定；涉及 17:10 两文件改动的运行时结论（TC044/045/046/020/014）需开发刷新预览后补一轮纯运行时复核。**

> **【二轮更新 09-09】D1 已解决**：09-09 运行时复测（v3b→v3h 七轮）确认预览 chunk 已全部更新为新代码——`formatLevel` 输出 X 阶、图鉴 VList 虚拟滚动生效（实例化 20 项 < 全量 72）、TogContent 分类链路正常、图鉴详情显『初始阶数：1阶』。原 D1 阻塞项已完成复核（见 ⑤）。

---

## ① 静态复核结论（权威，对照 73 条用例，含 17:10 最新改动）

### 处理1 —— 法宝外观按 ring_group（TC001~011）→ 部分实现（数据就绪，代码仍 quality 驱动）
- 10 档资源映射已数据化到 `cfg_soul_ring_quality`（bg/draw_ball_eff_res/eff_res/skill_res/atlas_res/atlas_filter_res 全就位）。
- 代码取用仍按 `quality`：`UISoulRing.ts L51-52/83-84`、`UISoulRingDesc.ts L62/117`、`UISoulRingAtlas.ts L108` 等。
- `cfg_soul_ring_base` 72 条中 `quality == ring_group` 占比 **100%** → 当前数据显示巧合等价；TC007/008 需造 `quality≠ring_group` 数据才能暴露。

### 处理2 —— 年份→阶（TC012~026）→ 文案基本完成（本轮运行时实锤），阶数颜色未按 level
- `Util.formatLevel` 运行时实锤输出 `X阶`；列表项/抽奖 Add 列表/装配 item（17:10 版 Year_rich）均已显阶。
- `formatYear`（灵力文案）在 soulring 业务代码中为死代码；残留 `formatYear2` 仅作图标档位索引（`SoulRingCtl.ts L69` 等，非文案）。
- **阶数颜色未按 level**：仍按 quality 色（noFeatures=true）或灰 `#8999a1`（TC025）。

### 处理3 —— 技能解锁条件文案改 xxx阶（TC027~028）→ 基本完成

### 处理4 —— 未解锁特性显示「未解锁+要求阶数」/「暂无特性」（TC029~033）→ **未实现**
- 17:10 版 `UIHeroSoulItem.ts L156-179` 仍显示全部特性（灰色显实际效果文案，非「未解锁」）；无「暂无特性」逻辑；v2 运行时取证一致。

### 处理5 —— 技能tips法宝页签只显示已激活特性（TC034~036）→ **未实现**
- `UISoulRingDesc.ts L123-151` 显示全部特性（灰/亮区分）。

### 处理6 —— 概率行文字底按组别独立资源（TC037~040）→ **未实现**
- `cfg_soul_ring_pool_lv_desc` 仍 `year`+`color`；`UISoulRingDrawLvDesc.ts L121/146` 未改；v1/v2 运行时均实显「精品/良品」品质名。

### 处理7 —— 法宝列表显示基础属性（TC041~043）→ 部分实现
- 装配 item `UIHeroSoulItem.ts L99-110` 有基础属性；列表项 `UISoulRing` 无 → 两处不一致。

### 处理8 —— 图鉴分类按 ring_group + 卡池条件（TC044~048）→ 部分实现（17:10 有增量）
- 分类仍按 `quality`（`qualityList` 来自 `cfg_soul_ring_quality`），未按 ring_group；v1 运行时图鉴按品质分组（凡/良/精标题）实锤。
- **17:10 增量**：内容列表改 `VList` 虚拟滚动；分类改 `TogContent` ToggleContainer；筛选图数据化 `atlas_filter_res`（L134 引用）。
- **锁定交互已补**：点击最高档未达标 → `showMessageTip("炼宝等级达到7级可查阅")`（`cfg_soul_ring_misc.atlas_red_god_show_cond=7`）+ 勾选回弹（L48-53）；但条件仅 maxQuality（仙品）一档，非「每 ring_group 独立条件」。

### 补需求（TC049~053）→ 资源就绪，6112/6113 图标缺失未修复
- `cfg_soul_ring_icon` 仍缺 `gift_id 6112(筋斗云)`、`6113(锁子黄金甲)` 图标（与 9/7 一致，未修复）。

---

## ② 运行时回归结果（三轮）

| 轮次 | 时间 | 账号 | 结果 | 说明 |
|---|---|---|---|---|
| v2（GM解锁链路） | 16:07 | 1353@S5 | 12/17 | `reports/e2e_fabao_v2_20260908_160724` |
| v1（原生解锁） | 17:18 | 1351@S5 | 8/11 | `reports/e2e_fabao_20260908_171824` |
| 探针（Util/图鉴结构） | 17:26 | 1351@S5 | 证据采集 | `reports/e2e_fabao_probe2_20260908_172635` |

两轮主回归一致的运行时结论：

| 用例 | 结果 | 说明 |
|---|---|---|
| TC054 法宝主界面打开 | PASS | 两轮通过 |
| TC024 无「灵力/万灵力」残留 | PASS | 两轮通过 |
| TC040 概率弹窗打开 | PASS | 两轮通过 |
| TC056 图鉴打开 | PASS | 两轮通过 |
| TC057 装配界面打开 | PASS | 两轮通过 |
| TC037 概率行组别底图 | 未改造证据 | 实显「精品/良品」品质名 |
| TC044 分类按组别 | 未达标证据 | 按品质分组（凡/良/精标题） |
| TC014 图鉴详情初始阶数 | 旧chunk残留 | 「初始阶数：1000年」 |
| TC055 炼宝页签 | FAIL | 两轮均未打开（工具上下文限制，建议人工复核） |
| TC046 卡池未达标提示 | 未取证 | 预览为旧 chunk，17:10 静态已补提示交互 |
| TC063 GM面板 | FAIL | 节点名 uiGM 未命中（工具限制） |
| TC029 未解锁特性「未解锁」 | FAIL | 未见「未解锁/暂无特性」（与静态一致） |

探针补充（17:26）：
- `formatLevel/formatYear` 行为实锤（见 §0 表格）；`pool_level=1`、`getInitialLevel(6001)=1` 正常。
- 运行时 JS 报错样本：`cfg_soul_ring_pool 索引为：0`、`cfg_soul_ring_quality 索引为：-1`、`cfg_soul_bone 索引 72xx` 系列缺失、`jump_id=40/57/58/69/106/144/174 配置读取失败` → TC066/TC060 佐证。

---

## ②B 第二轮运行时复核（2026-09-09，D1 解决后七轮 E2E）

复测脚本 `harness/e2e_fabao_v3*.py`（Playwright + QA 桥，账号 1353@S5 + GM 接口造数），轮次：

| 轮次 | 时间 | 修正点 | 结果 |
|---|---|---|---|
| v3b | 11:33 | 基线 23 项 | 17/23 |
| v3c | 11:53 | TC042-note 系统加成、TC043 节点 | TC042-note PASS |
| v3d | 12:14 | TC055 抽奖（GM 造 1007 材料） | **抽奖 1/10 次扣费 20→19→9 精确 PASS** |
| v3e | 12:25 | TC042 当轮造数+一键穿戴、TC043 视口过滤 | **TC042 / TC043 PASS** |
| v3f/g | 12:37/12:45 | 页签真实 label、toggle 派发机制、VList 回收区过滤 | **TC055-tab PASS**；pageerror 源定位 |
| v3h | 12:51 | 外观解耦组件级取证（ItemHelper.getItemQualityCfg 直调） | **TC007/008/009 缺陷复现（FAIL 实锤）** |

### 二轮结论明细

| 用例 | 一轮结论 | 二轮结论 | 关键证据 |
|---|---|---|---|
| TC055 炼宝页签 | 失败(工具限制) | **通过** | 页签容器 UISoulRingDrawTabView，toggle 走游戏 setToggleList 机制（`node.emit('toggle')`，UIObject L744）；『法宝总览』→图鉴激活、『炼宝』→炼宝激活；抽奖扣费精确（v3d） |
| TC042 属性一致 | 待运行时 | **通过** | GM 发 6001 + 一键穿戴后：面板 `+18/+18/+225` == 公式期望 `[18,18,225]`（御剑符 1 阶 addition=0.6%）；SOUL_RING 系统加成 0.2%×3 |
| TC043 长名布局 | 待运行时 | **通过** | 15 字超长名项（视口内）：名称中心 (379,306) 在图标中心 (150,230) 上方，相交 0 项；截图人工复核通过 |
| TC020 年份残留 | 通过(静态) | **通过(运行时实锤，修正误判)** | v3b/c 的『图鉴内 80万年』系误判：全部年份文本在【未拥有法宝的 year 标签】（RingAtlasItem L85 仅 ringMap 有该法宝才写入，否则保留预制体默认文本且 activeNode 隐藏不渲染）及 active=False 节点；可见项均显 X 阶 |
| TC014 详情初始阶数 | 通过(一轮) | 通过（新 chunk 实显『初始阶数：1阶』） | D1 解决后运行时确认 |
| TC045 图鉴虚拟滚动 | 部分实现 | **通过** | VList 生效：实例化 20 项 < 全量 72，随滚动回收；TogContent 分类链路正常 |
| TC007/008/009 外观解耦 | 无法验证(需造数) | **未实现（缺陷复现）** | 组件级直调 `ItemHelper.getItemQualityCfg`（= RingAtlasItem L77-78 同链路）：①改 6001 quality 1→7 → atlas_res kuang07→kuang08（外观源跟随 quality，TC009 陷）②6002 ring_group 1→5 → 外观源**完全不变**（只认 quality 不认 group，TC007 陷）③同 group 下 6002 quality 1→7 → 外观源变化（TC008 陷）；对照组 patch quality[1].atlas_res→kuang03 生效（补丁链路验证）；图鉴分组键=e.quality（UISoulRingAtlas L132-137） |
| TC044 分类按组别 | 部分实现 | 部分实现（加强） | 运行时实锤 datasMap 按 quality 分组、列表 quality 降序+已拥有置顶排序 |
| TC066 索引防御 | 静态关注 | 静态关注（加强） | 每轮仍报 `cfg_soul_ring_quality 索引-1` 36~46 条、`cfg_soul_ring_pool 索引0` 1~2 条 |

### 新发现：D11 高频空引用 pageerror（与法宝无关，建议单独修复）

`Cannot read properties of null (reading 'x')` 每轮 2800~4600 条（~16 条/秒，CallFunc 每帧重复触发），栈定位：

```
Vec3.copy ← Node.setPosition ← SceneMap.playSceneEff (chunks/46/46697d…js L3800)
  ← UIManHuaPage1.hideCallBack (chunks/a3/a38de4…js L264)
```

漫画页（UIManHuaPage1）关闭回调里 `playSceneEff` 收到空节点持续 setPosition 报错；主城静置为 0 条，任一界面关闭漫画页后开始刷屏。影响全局（不限法宝），建议排期修复。

---

## ②C 战斗表现回归（2026-09-09，battle1~3 三轮）

脚本 `harness/e2e_fabao_battle*.py`（Playwright + QA 桥 + GM HTTP 造数，账号 1353@S5）。前两轮失败根因定位（源码实证）：

- GM 测试按钮真实节点为 `GMRoot` 下的 **GMBTN / BATTLE_TEST / MAIN_BATTLE_TEST**（`UIMgr.ts L224-383` 程序化创建），容器 TESTFight/MAINTESTFight 无 Button 组件，按容器名 emit click 无效；
- `sendWearOneKey(buddy_uuid)` 需有效英雄 uuid（`SoulRingMgr.ts L186-193` getHeroByUuid 后直读 skill_list）；
- **UIMainView 消失不能作进战斗信号**（battle2 截图实锤：UISoulRingShow 获得弹窗覆盖顶层，fightHit 才有效）。

battle3（最终轮）结果：

| 用例 | 结论 | 关键证据 |
|---|---|---|
| TC063 GM面板 | **通过（升级，原失败）** | 真实入口 GMBTN：`clickNode('UIRootCamera/GMRoot/GM/GMBTN')` 打开 → `Global.uiMgr.getUI('UIGM').visible()=True`；再点关闭 → False，开/关 toggle 验证通过。此前两轮 FAIL 系 UI 注册名 'UIGM' 与面板节点名 'uiGM' 不一致导致 findByName 未命中（**工具误判，非产品缺陷**） |
| B030 战斗测试入口 | 通过 | `clickNode('UIRootCamera/GMRoot/TESTFight/BATTLE_TEST')` 生效，UITestFight 战斗界面正常打开（编队/战斗 BtnFight_/重置/x1/伤害流水控件齐全可点） |
| TC024 战斗内无残留 | 通过（补战斗场景覆盖） | 战斗界面文本快照（t1/t2 两帧）无『灵力/万灵力/年份』命中 |
| TC065 战斗内法宝技能释放 | 待人工复核（部分验证） | 战斗阶段 **0 新增 JS 报错**；但技能释放需『已装配法宝+编队英雄』——测试账号 1353 当前编队与 heroMap 均为空（三轮实锤）无法完成装配 → 特效/数值需人工用正常账号复核 |
| B040 JS错误基线 | 通过 | 全程仅 40 条：D9_bone 30、D10_jump_id 7；无 D11 漫画页空引用（本流程未触发漫画页）、无法宝相关新增报错 |

顺带取证：GM 发 6001 触发的 UISoulRingShow 获得弹窗实显『新获得！**1阶** [凡]御剑符 / **20阶解锁**：攻击加成+10.0% / 法宝基础属性 +18/+18/+225』——处理2（年份→阶）与基础属性展示在获得弹窗场景同样正确。

---

## ②D 公告滚屏（R3）+ 法宝推送礼包运行时取证（2026-09-09）

### R3 公告滚屏过滤与品质配色 → **通过（运行时 9/9 全 PASS）**

服务端已实现开服天过滤（`mod_soul_ring.lua L1064-1087` CheckBigReward：serverDayNotice，神 q8=4 / 圣 q9=18 / 仙 q10=-1 恒公告），公告颜色取 `cfg_soul_ring_quality[quality].color`——较 09-08 静态结论（未实现）为**开发新增改动**，本轮运行时验证（脚本 `harness/fabao_r3_bulletin.py`，账号 4451）：

| 开服天 | 抽中 神/圣/仙 | 公告 神/圣/仙 | 判定 |
|---|---|---|---|
| day2（≤4天） | 41 / 6 / 1 | 48 / 6 / 1 | 三品均应公告且已公告 → **PASS×3** |
| day5（5~18天） | 135 / 20 / 1 | 0 / 21 / 1 | 神应静默无公告✓ 圣/仙应公告已公告✓ → **PASS×3** |
| day19（19+天） | 89 / 20 / 1 | 0 / 0 / 1 | 神/圣应静默无公告✓ 仙应公告已公告✓ → **PASS×3** |

颜色取证（公告原文 `<color>` 标记直读）：神 `#de74cc` / 圣 `#de645d` / 仙 `#7c8dd7`，与 cfg_soul_ring_quality 配置全部一致；公告模板『恭喜…在【炼宝】获得：法宝-[品]…』正确。

复现要点（踩坑记录）：
- GM `set_server_day` 切开服天（对账号无要求，已确认），结束复原 101 ✓；
- 抽奖直发协议 `c2gs_soul_ring_draw` 绕过客户端「卡池可升级」拦截（SoulRingMgr.ts L249→L521-536：pool_level≥12 且 draw_times≥21000 且 serverDay≥3 时弹窗不发请求）；
- **卡池等级必须先升到 12 级**：pool_level=1 的权重不含 8/9/10 品（上轮 3×20000 抽全空根因）；连发 `c2gs_get_soul_ring_pool_upgrade` 即可（服务端只校验 draw_times≥cfg need_draw_times=21000，无开服天限制）；
- hook `gs2c_bulletin_update`/`gs2c_chat_info` 捕获公告原文，吞 `gs2c_new_soul_ring_tips` 防获得弹窗遮挡。

产物：`reports/fabao_r3_bulletin_20260909_191601/`（report.json + 09_end_day*/03_bulletin_day* 截图）。

### 法宝相关推送礼包 UI 取证（TC050~053）

5 类礼包 UI 全部可正常打开（账号 4451，脚本 `harness/fabao_pack_ui_evidence.py`）：

| 礼包 | UI | 运行时证据 | 结论 |
|---|---|---|---|
| 推送礼包 140xxx | UIPushGiftPack | 「史诗神器 混天绫」￥30 翻页轮播正常（标题为切图、无 Label 属正常） | 通过 |
| 仙星礼包 390xxx | UIGodStarGift | 打开正常；内容区空——24 档已于前置轮次全部购买（recharge_notifykey 24/24 OK），属状态结果非缺陷 | 上架通过；内容建议新号人工复核（TC053） |
| 孙悟空礼包 530001 | UIWuKongGift | ￥12 / 120 / 倒计时；紫金葫芦、筋斗云标签显示「**极品**」（原『玄品』已改） | 通过（TC050 文案实锤；调色/光晕细节建议人工对比需求图） |
| 魂环推送礼包 480001~4 | UIRechargeSoulRing | **「150阶法宝 [无始钟]」新图实锤生效**（截图 05）；4 档 [圣]无始钟/昆吾人皇剑/番天印/创世鼎 页签齐全；￥98/购买即可获得法宝；全 UI 无『灵力』文本残留 | **通过（TC051 实锤）** |
| 主城入口 | 浮标 | 「特惠法宝」「大圣法宝」入口浮标在位 | 通过 |

注：「150阶法宝」为 res1 切图（`completiong_gift_pack_img02_name01~04`，UIRechargeSoulRing.ts L121 loadSetUIIcon 引用；奖励条目 UIITEM_NO_NAME 不显示名称）——文本 dump 抓不到属正常，以截图为准。TC052 的 8 处灵力文案改阶数：运行时全部 dump 无『灵力』命中，图片内文案细节建议人工复核。

产物：`reports/fabao_pack_ui_evidence_20260909_192734/`（01~05 截图 + report.json）。

---

## ③ 73 条用例结论分布（详见 cases/法宝UI优化测试用例_trae_v2.xlsx，二轮+战斗回归+公告滚屏/礼包后）

| 结果 | 数量 | 占比 | 说明 |
|---|---|---|---|
| 通过 | 29 | 40% | 二轮升级：TC042/043（运行时双证）、TC055（页签+抽奖）、TC045（VList 生效）、TC014/TC020（运行时实锤/误判修正）；战斗回归升级：TC063（GM 面板 toggle，工具误判修正）、TC024（补战斗场景覆盖）；**公告滚屏/礼包升级（②D）：TC050（玄品→极品实锤）、TC051（150阶法宝新图实锤）、TC052（0 灵力残留）** |
| 部分实现 | 10 | 14% | 处理1/7/8 主体：数据就绪但代码 quality 驱动等 |
| 未实现 | 15 | 21% | 处理4/5/6 全部 + TC025/030 + **TC007/008/009（二轮运行时缺陷复现）** |
| 待运行时(阻塞) | 15 | 21% | 未覆盖操作链（TC058~062/064 等）；D1 已解决，纯未覆盖项 |
| 资源就绪 | 1 | 1% | TC049（强者之路入口引用未复核） |
| 待人工复核 | 2 | 3% | TC065（战斗内技能释放；自动化已验证战斗链路 0 报错，账号无英雄无法装配）；TC053（仙星礼包 24 档已购空，内容图需新号复核） |
| 静态关注 | 1 | 1% | TC066（quality 直接索引防御，二轮仍每轮报错） |

---

## ④ 缺陷/问题清单（trae 全量重测）

| # | 严重度 | 位置 | 问题 | 状态 vs 9/7 |
|---|---|---|---|---|
| D1 | 高 | 运行环境 | 预览新旧 chunk 混杂，17:10 改动未编译进预览 | **已解决（09-09 复测确认新 chunk 全部生效）** |
| D2 | 高 | cfg_soul_ring_icon | 6112(筋斗云)/6113(锁子黄金甲) 图标缺失 | **未修复** |
| D3 | 中 | 处理1 | 外观映射代码仍按 quality 驱动（当前配置巧合等价，语义未达标） | **未修复（09-09 运行时缺陷复现实锤，TC007/008/009）** |
| D4 | 中 | 处理2 | 阶数颜色未按 level（仍按 quality 或灰） | 未修复 |
| D5 | 高 | 处理4/5 | 未解锁特性未按「未解锁+要求阶数」/「暂无特性」实现；tips 未做「只显示已激活」 | 未修复 |
| D6 | 中 | 处理6 | 概率行仍品质名+色值，未按组别独立底图 | 未修复 |
| D7 | 低 | 处理7 | 法宝列表项无基础属性（装配 item 已有） | 未修复 |
| D8 | 中 | 处理8 | 图鉴分类仍按 quality（运行时实锤 datasMap 按 quality 分组）；卡池条件仅仙品一档（锁定提示交互 17:10 已补） | 部分改善 |
| D9 | 低 | 运行时 | `cfg_soul_ring_pool 索引0`/`cfg_soul_ring_quality 索引-1` 直接索引报错（TC066 佐证，二轮每轮 36~46 条） | 存续 |
| D10 | 低 | 配置 | `jump_id=40/57/58/69/106/144/174 配置读取失败` 告警（TC060 相关），建议复核 jump 配置 | 存续 |
| D11 | 中 | 运行环境 | UIManHuaPage1.hideCallBack→SceneMap.playSceneEff 空引用，每轮 2800~4600 条 pageerror（~16条/秒）；与法宝无关，全局影响 | **新增（09-09，源已定位）** |

---

## ⑤ 下一步建议

1. ~~开发刷新/重建客户端预览，消除 D1~~ → **已完成（09-09 复测确认新 chunk 生效，原阻塞项 TC014/020/042/043/045 已全部复核）**
2. 优先复核三处高优先级缺陷：D2（6112/6113 图标）、D3（代码改读 ring_group，**二轮已运行时实锤缺陷**）、D5（未解锁特性文案）。
3. ~~TC007/008 需 GM 造 quality≠ring_group 数据验证~~ → **已完成（09-09 v3h 运行时 patch 造数，解耦未实现缺陷复现）**
4. ~~TC055（炼宝页签）~~ → **已通过**；~~TC063（GM 面板）~~ → **已通过（battle2/3 GMBTN toggle 开/关验证，此前失败系工具误判，非产品缺陷）**。
5. D11（UIManHuaPage1 空引用刷屏）与法宝无关但影响全局日志/性能，建议随下次修复单独排期；D9/D10 建议随下次修复一并处理（防御性索引 + jump 配置补全）。
6. 待运行时未覆盖项（TC058 装配操作链 / TC059 技能tips / TC064 英雄详情法宝页签等）建议下一轮覆盖；**TC065 战斗内法宝技能释放需人工用正常账号复核**（自动化已验证战斗测试入口/界面/控件可用且 0 报错，但测试账号 1353 无英雄无法装配法宝）。
7. **R3 公告滚屏已运行时验证通过（②D，9/9 PASS + 颜色一致）**；TC050/051/052 升级通过。剩余人工项：TC053 仙星礼包内容图（24 档在账号 4451 已购空，需新号或未购账号复核）、TC050 调色/光晕与需求图逐项对比、TC049 强者之路入口引用。
