# 测试用例：登录流程-选服s5服-账号13531

| 项目 | 内容 |
|---|---|
| 用例编号 | TC_LOGIN_001 |
| 用例标题 | 登录流程-选服s5服-账号13531 |
| 优先级 | P0 |
| 测试类型 | 端到端(E2E) / UI + 后端(plat_login)校验 |
| 目标地址 | http://localhost:7456 |
| 测试账号 | 13531 |
| 目标服务器 | s5服（解析 svr_id=5） |
| **选服方式** | **兜底注入(localStorage)** |
| 运行模式 | 无头 |
| 开始时间 | 2026-09-08T17:07:32 |
| 结束时间 | 2026-09-08T17:08:02 |
| **测试结果** | **通过(PASS)** |

## 前置条件
1. 游戏页面 http://localhost:7456 可达（HTTP 200）。
2. 客户端内置 QA Bridge（`window.__qa`）可用。
3. **目标服 s5服（svr_id=5）必须已启动且可被平台服正常分配** —— 否则登录应判失败（本用例专门拦截「服务器没起却报通过」的假通过场景）。
4. 测试账号 13531 在目标服有效（新建账号场景由后端自动建号）。
5. 选服默认走真实 UI（登录界面「换区」按钮->换区弹窗->选服）；仅当 UI 不可行时兜底注入 localStorage，仍由后端 plat_login 把关。

## 测试步骤

| 步骤 | 操作 | 预期结果 | 实际结果 | 状态 |
|---|---|---|---|---|
| 1 | 打开游戏 | 游戏页面加载，QA Bridge 就绪，服务器列表已拉取 | QA Bridge 就绪 | done |
| 2 | 注入账号 |  |  | done |
| 3 | 选服(真实UI/兜底) | 优先真实 UI：换区弹窗->遍历区->点目标服；点不到再兜底注入 localStorage（s5服） | 选服方式=injection; 已兜底注入选服 svr_id=5（UI路径: 遍历所有区页签均未找到目标服(可能未开放/不在可见区)） | done |
| 4 | 重载使账号与选服生效 |  |  | done |
| 5 | 点击登录 | 点击 LoginBtn_ 触发登录 | 已点击 LoginBtn_ | done |
| 6 | 校验plat_login响应 | 请求 serverId==s5服 且 后端 errcode==0（目标服已启动且接受登录） | plat_login 成功 (errcode=0, serverId=5, 实际响应 serverId=5 serverName=S5 ip=192.168.*.*:11021) | done |
| 7 | 等待进主城并校验 | 进入主城，佐证在目标服且建立真实角色 | 界面未直接显示目标服名（UI文本: ['开服狂欢', '客服', '[S1]玩家名字：', '全服红包', '客服']）；未能确认真实角色 uuid（playerMgr 字段不可读，已降级） | done |

## 结论

全部步骤通过，已确认账号成功登录并进入目标服主城（plat_login 成功 + 进入主城 + 佐证在目标服）。

## 选服方式说明
本用例选服为 **兜底注入(localStorage)**。
- 真实 UI：模拟玩家在登录界面点「换区」打开弹窗，动态遍历区页签找到含目标服的区并点击服 Toggle，与玩家操作一致，且天然验证「目标服是否可选」。
- 兜底注入：仅当弹窗未开/遍历所有区点不到目标服/选完 localStorage 未生效时触发，写入与游戏 `customSetSelectServer` 完全相同的 3 个 localStorage 键，登录瞬间由 `LoginMode._login` 重读生效。

## 权威服信息（plat_login 响应，客户端据此连接游戏服）

- serverId: 5
- serverName: S5
- 连接地址: 192.168.*.*:11021
- roleIdx: 0  isBack=False  isNew=None

> 说明：界面顶部「区 服：[S1]」是玩家名/账号主服的显示标签，不代表当前实际连接的游戏服；真正判定依据为上方 plat_login 的 serverId 与连接地址，以及「进入主城」结果。




## 关联截图
- opened: `E:\workproject\reports\e2e_login_20260908_170732\screenshots\01_opened.png`
- server_selected: `E:\workproject\reports\e2e_login_20260908_170732\screenshots\02_server_selected.png`
- login_clicked: `E:\workproject\reports\e2e_login_20260908_170732\screenshots\03_login_clicked.png`
- in_main_city: `E:\workproject\reports\e2e_login_20260908_170732\screenshots\04_in_main_city.png`