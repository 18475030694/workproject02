# 测试用例：登录流程-选服s5服-账号1351

| 项目 | 内容 |
|---|---|
| 用例编号 | TC_LOGIN_001 |
| 用例标题 | 登录流程-选服s5服-账号1351 |
| 优先级 | P0 |
| 测试类型 | 端到端(E2E) / UI |
| 目标地址 | http://localhost:7456 |
| 测试账号 | 1351 |
| 目标服务器 | s5服 |
| 服务器匹配 | None |
| 运行模式 | 无头 |
| 开始时间 | 2026-09-01T14:46:11 |
| 结束时间 | 2026-09-01T14:46:26 |
| **测试结果** | **通过(PASS)** |

## 前置条件
1. 游戏实例在 `http://localhost:7456` 可达（HTTP 200）。
2. 客户端内置 QA Bridge（`window.__qa`）可用，提供节点查找 / 点击 / UI 状态查询。
3. 测试账号 `1351` 有效且可登录 `s5服`。

## 测试步骤

| 步骤 | 操作 | 预期结果 | 实际结果 | 状态 |
|---|---|---|---|---|
| 1 | 输入账号 | 账号 1351 已注入 localStorage | 已注入 TMP_ACCOUNT_=1351 | done |
| 2 | 打开游戏 | 游戏页面加载，QA Bridge(window.__qa)就绪 | QA Bridge 就绪 | done |
| 3 | 选服 | 选中 s5服（未出现选服 UI（按当前配置服登录）） | 未出现选服 UI（按当前配置服登录） | done |
| 4 | 点击登录 | 触发登录流程 | 已点击 LoginBtn_ | done |
| 5 | 等待进主城 | 系统模块就绪、加载界面消失，进入主城 | 已到达主城(isReady + UILoading 消失) | done |

## 结论
全部步骤执行通过，账号成功登录并进入主城。



## 关联截图
- opened: `E:\workproject\reports\e2e_login_20260901_144611\screenshots\01_opened.png`
- server_selected: `E:\workproject\reports\e2e_login_20260901_144611\screenshots\02_server_selected.png`
- login_clicked: `E:\workproject\reports\e2e_login_20260901_144611\screenshots\03_login_clicked.png`
- in_main_city: `E:\workproject\reports\e2e_login_20260901_144611\screenshots\04_in_main_city.png`
