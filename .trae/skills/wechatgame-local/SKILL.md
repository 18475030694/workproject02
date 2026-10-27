---
name: "wechatgame-local"
description: "p1-x 微信小游戏本地化出包与排障手册：构建配置、CLI 构建、构建后五件套（res_version/Version.ts/multTextures远程bundle/特权卡补丁/8080服务）、DevTools 导入、运行时坑速查。凡用户要求微信小游戏出包、重新构建、DevTools 打不开/登录死循环/战斗崩溃排查、构建产物补丁时调用。"
---

# 微信小游戏本地化（p1-x）出包与排障

目标：把 p1-x 客户端（Cocos 3.7.3）构建产物在微信开发者工具本地跑通（连内网 S5）。**游戏源码零改动**，全部动作在构建产物层。完整原理与细节见《微信小游戏本地化_全流程指南》（`temp_case/reports/微信小游戏本地化_全流程指南.md`），卡点史见《微信小游戏本地化_过程与问题修复实录》。

## 1. 环境速记

- 工程 `E:\p1-x\trunk\client`；产物 `client\build\wechatgame`（SVN 未纳管）
- Cocos CLI 构建 ≈6min（skipCompressTexture=true 前提）；本地 Python `D:\python\python3.9\python.exe`
- 测试 appid `wx6ac3f5090a6b99c5`；plat `192.168.*.*:8001`；DevTools 需勾「不校验合法域名」
- 本地资源服务：`python -m http.server 8080 --directory ...\build\wechatgame`（重启后需重起）

## 2. 出包流程（按序，缺一步必踩对应坑）

1. **杀 CocosCreator 进程**（library 锁）→ CLI 构建：
   `CocosCreator.exe --project E:\p1-x\trunk\client --build configPath=E:\workproject\temp_case\reports\buildConfig-local-wechat.json`
   - 禁沙箱执行（沙箱拦写 E:\p1-x）；**中途不可强杀**（tmp_cfg 不还原会毁 cfg 目录）
   - 构建配置关键项：skipCompressTexture=true / server=127.0.0.1:8080 / buildVersion 三段式 / gameDebug=true / sdk_platform=tourist / debug_plat=192.168.*.*:8001
2. **一键后处理**（替代原 res_version/Version.ts/multTextures/特权卡四步手工）：
   `D:\python\python3.9\python.exe E:\workproject\temp_case\scripts\post_build_wechatgame.py`
   - 一次做完：res_version 拷贝 / Version.ts 还原 / multTextures 远程改造（ver 自动从 settings 的 assets.bundleVers 读，适配每次构建的新 hash）/ 特权卡补丁判定与重打（内部调 priv_fix_patch.py）
   - 幂等可反复跑（已做过的自动跳过）；写盘前自动备份 `temp_case/reports/post_build_bak/<时间戳>/`；末尾逐项终检，退出码 0=就绪 1=有缺项
   - `--check` 只巡检不写盘；`--cocos <CocosCreator.exe路径>` 连 CLI 构建一起跑（真一键，约6min）
   - 手工等价步骤（脚本不可用时）：res_version 拷贝 + Version.ts 还原（`export const Version = "BUILD_VERSION"`）+ multTextures 远程 bundle 改造 + 特权卡快照判定补丁，详见《全流程指南》§4.1~4.5
   - multTextures 改造前置：`assets/multTextures.meta` 必须是 SVN 基线（isBundle:true），脚本终检会查
3. 核对根 `game.js` 调试钩子与 `project.config.json`（appid/libVersion/urlCheck）——脚本终检会提示钩子缺否
4. DevTools 指向 `build\wechatgame` → 勾不校验合法域名 → 编译 → 进一次战斗冒烟

## 3. 运行时坑速查（症状 → 根因 → 处理）

| 症状 | 根因 | 处理 |
|---|---|---|
| 登录 VERIFY 死循环/进审核服 | plat 库 `platadmin_config.audit_version` 含旧版本号 | `192.168.*.*:3306 root/***` 库 game_dev 清空该配置 + update_configs 刷新（脚本 `temp_case/scripts/fix_plat_audit_version.py`） |
| 战斗 `createEngine:fail create time_limit` | multTextures 走微信分包，DevTools 分包上下文超时 | 出包流程第 4 步 |
| 战斗崩 + Console `reading 'time_limit'/'sys_id'` at getPrivilegeVal | 构建 cfg 快照缺新加的特权卡（服务端会下发未购卡 buy_time=0） | 第 5 步补丁；`[PRIV-FIX]` 日志会吐出异常 card_id |
| `copyfile:fail` / 资源怪 | DevTools 200MB 缓存配额满 | 清缓存重编译 |
| Console 刷 `[SF-RELEASE]`/裸 `Error` 栈 | gameDebug 伪报错（SF-DECREF 主动打 `(new Error).stack`） | 忽略；真错误看红条目 |
| 网页预览 Error undefined 登录卡死 | Version.ts 被构建写脏 | 第 3 步 |
| 预览 `/assets/multTextures/*` 404 + webAsset render failed | `multTextures.meta` 被写坏 isBundle:false | 还原 meta 至 SVN 基线 |
| 18080 抓不到分包报错 | `useIsolateContext:true` 分包隔离上下文 | 只能 DevTools Console 看 |

## 4. 铁律

- 构建产物 = **快照**：构建之后源码/配置的任何更新，产物不会自动跟上（cfg 表、脚本同理）——「网页正常/微信崩」优先怀疑快照过期
- 每次构建必跑第 2 步一键脚本（post_build_wechatgame.py）；脚本缺位时按《全流程指南》§4.1~4.5 手工补齐
- 构建产物补丁必须带备份与唯一性断言（参考 priv_fix_patch.py 写法），并记入报告
- 修改 E:\p1-x 一律禁沙箱执行；loc_check 相关操作保持只读
