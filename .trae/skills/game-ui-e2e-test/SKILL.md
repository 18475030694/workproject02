---
name: "game-ui-e2e-test"
description: "p1-x 游戏客户端 UI E2E 测试复用资产：Playwright+QA注入、GM命令、UI文本dump、错误码表、常见坑、回填Excel套路。凡是对 p1-x 客户端做运行时UI测试/用例回填/GM数据准备时调用。"
---

# 游戏 UI E2E 测试复用（p1-x 客户端）

对 p1-x 游戏客户端做运行时 UI 测试时，**先复用以下资产，不要从零写**。

## 1. 资产地图

| 用途 | 文件 |
|---|---|
| E2E 模板脚本（QA注入+dump+断言+rec()报告） | `E:\workproject\harness\e2e_soulspirit.py` |
| GM 数据准备模板 | `E:\workproject\harness\prep_soulspirit_data.py` |
| GM 账号/一键高级号 | `E:\workproject\harness\gm_account.py` |
| GM 限时活动（yxact）管理 | `E:\workproject\harness\gm_yxact.py` |
| 用例生成 MD→Excel | `E:\workproject\temp_case\scripts\gen_lingchong_cases.py` |
| 执行结果回填 Excel（复判列+概要Sheet） | `E:\workproject\temp_case\scripts\backfill_lingchong_e2e.py` |
| 概率/数值抽样验证（引用专用 skill） | `.trae/skills/game-prob-verify/SKILL.md` |

文件规范：新脚本放 `temp_case/scripts/`，用例 xlsx 放 `temp_case/cases/`，报告/产物放 `temp_case/reports/` 与 `reports/`。

## 2. 环境与账号

- 预览构建 `localhost:7456`（prefab/配置改动刷新即生效，真机需重新构建）
- 现成 GM 号 **4451**（lv9463 高级号，gm_account.py 可再造）
- 灵宠系统 sys_id=116：开服第4天+主线900关。系统未开启报 errcode 1606 → 先 GM `set_mainline_stage 5000`
- S5 服务器 GM（如 set_server_day）全测试组共享：**必须 改→测→还原**

### GM 限时活动（yxact）管理

- 工具：`python harness/gm_yxact.py list|--kw 天工` / `open|close|reopen <actGroupId> [--server 5] [--beg X --end Y(unix秒)]`；import 双用 `gm_yxact.gm_open(5, 20002)`
- 指令本质：`GET GM_HOST:6011/index/open_yxact?serverId=5&actGroupId=X&totalBegTime=&totalEndTime=&countdownEndTime=`（handlers/yxact.lua）
- 铁律：
  1. **serverId 必传**（不传/传 0 = 全部服下发）
  2. 已开启的活动再 open **静默失败** → 用 `reopen`（close→open）
  3. 时间不传 = 今天 00:00 起、时长取配置；传则 unix 秒，--beg/--end 必须成对
  4. 活动 ID 查 `server/src/res/Config/yxact/cfg_yxact_group_time.lua`（list 子命令可搜）；应答 `OK: nil REPLY: nil` 即派发成功（Rpc 异步），客户端重连后活动面板可见
  5. 测试完 `close_yxact` 还原

## 3. QA 注入要点（见 e2e_soulspirit.py 头部）

- 等 `window.__qa` 就绪再操作；`qa(page, "() => ...", default)` 兜底防异常
- `dumpUITree` 返回的节点用 **path 字段**（不是 node）
- 常用句柄：`__SM()`（SystemModules）、`__G().uiMgr.getUI(name)`、`__SHOWUI(name, arg)`、`__SELECT(uuid)`、`__EXPECT(uuid)`
- 文本抓取用 `live_texts(page, uiName)`；数字含千分位逗号先 `norm_lvl` 去逗号再断言

## 4. UI 操作铁律（踩过的坑）

1. 关 UI 必须按注册名 `getUI(name).uiHide()`；遍历 uis 的通用关闭对部分 UI 无效 → 后续 UI 开在后面、截图被遮挡
2. 抽卡/获得类弹窗（如「恭喜获得」）会遮挡后续用例的文本读取 → 每步先关弹窗再 dump
3. 被遮挡/虚拟化节点文本抓不到 ≠ 显示错误：**先看截图再下结论**（TC-06 文本[]但截图显示正确）
4. 脚本直调 `__SHOWUI` 参数口径可能与真实入口不同，报空引用（如 DescPop null.quality）先怀疑调用方式，人工从真实入口复核
5. UI 打不开先查：系统是否开启（1606）→ 入口按钮是否真实存在 → showUI 参数
6. UIMainView 消失不能当战斗入场信号（弹窗会盖住）
7. GM 测试按钮真实路径 GMRoot/GMBTN/BATTLE_TEST/MAIN_BATTLE_TEST，容器无 Button 组件，emit click 无效
8. Excel 被占用 PermissionError → 换文件名输出（_v2/_v3/已回填）
9. PowerShell 无 heredoc/`&&`；一次性逻辑写 .py 文件再跑

## 5. 常用错误码（cfg_err_code.json：client/assets/resources/cfg/err_code/）

| code | 含义 |
|---|---|
| 1606 | 系统未开启 |
| 60012 | RoleOffline（GM 后重试+延时） |
| 2312/2313/2314 | 灵宠已是当前阶最大等级/最大阶/最大星级 |
| 2319 | 灵宠初始状态无法重置 |
| 2321/2322/2323 | 图鉴不存在/积分已领取/请先升图鉴等级 |
| 2324/2325 | 积分不足无法升级/图鉴不可升级 |

## 6. 标准流程（改文案/数值类需求）

1. **静态检索**：Grep 关键词（如「年份」）扫 export/server lua/client ts/resources（prefab+cfg），按系统过滤保留项 → 结论进 MD
2. **用例**：gen_*.py 生成 MD+Excel（9列：编号/分类/标题/优先级/前置/步骤/预期/方式/静态现状），等用户确认再执行
3. **数据准备**：prep_*.py 走 GM（发道具→抽卡→养成到目标档），产物记入 data.json prep 段
4. **E2E**：复制 e2e_soulspirit.py 改用例函数；rec() 统一记录 + 截图 + data.json；跑完先看 FAIL 截图再判性质（脚本问题/产品问题）
5. **回填**：backfill_*.py 在原 Excel 基础加「执行结果/复判/执行说明/截图」4列 + 概要 Sheet；FAIL 复判要给证据（错误码语义/截图内容）
6. MD 报告追加「执行结果」章节（结果汇总/数据准备/错误码佐证/检索结论/待人工复核清单）
