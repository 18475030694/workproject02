# 测试用例：登录流程-选服s5服-账号1351

| 项目 | 内容 |
|---|---|
| 用例编号 | TC_LOGIN_001 |
| 用例标题 | 登录流程-选服s5服-账号1351 |
| 优先级 | P0 |
| 测试类型 | 端到端(E2E) / UI + 后端(plat_login)校验 |
| 目标地址 | http://localhost:7456 |
| 测试账号 | 1351 |
| 目标服务器 | s5服（解析 svr_id=5） |
| 运行模式 | 无头 |
| 开始时间 | 2026-09-01T15:03:40 |
| 结束时间 | None |
| **测试结果** | **失败(FAIL)** |

## 前置条件
1. 游戏页面 `http://localhost:7456` 可达（HTTP 200）。
2. 客户端内置 QA Bridge（`window.__qa`）可用。
3. **目标服 s5服（svr_id=5）必须已启动且可被平台服正常分配** —— 否则登录应判失败（本用例专门拦截「服务器没起却报通过」的假通过场景）。
4. 测试账号 `1351` 在目标服有效。

## 测试步骤

| 步骤 | 操作 | 预期结果 | 实际结果 | 状态 |
|---|---|---|---|---|
| 1 | 输入账号并预设选服 | 账号 1351 注入；预选服写 localStorage | 已注入 TMP_ACCOUNT_=1351，预选服 id=5 | done |
| 2 | 打开游戏 | 游戏页面加载，QA Bridge 就绪，服务器列表已拉取 | QA Bridge 就绪 | done |
| 3 | 选服(强制s5) | 把登录服强制设为 s5（svr_id=5），不用默认服 | 已强制选服 svr_id=5 svr_name=s5（命名约定推断(未在列表中匹配)） | done |
| 4 | 点击登录 | 点击 LoginBtn_ 触发登录 | 已点击 LoginBtn_ | done |
| 5 | 校验plat_login响应 | 请求 serverId==s5 且 后端 errcode==0（s5 已启动且接受登录） | plat_login 成功 (errcode=0, serverId=5) | done |
| 6 | 等待进主城并校验 | 进入主城，佐证在 s5 且建立真实角色 | 登录未完成/未进入主城。界面提示: 客服 | 区        服： | [S1]xxx | <color=#685745>网络波动，与服务器连接中断，请重新登录！！！！</color> | 网络波动，与服务器连接中断，请重新登 | failed |

## 结论
存在步骤未通过，详见上方状态列与下方错误信息。最常见原因：目标服 s5 未启动 / 平台服未启动 / 账号在 s5 无角色 / 选服未生效。

## 错误信息\n登录未完成/未进入主城。界面提示: 客服 | 区        服： | [S1]xxx | <color=#685745>网络波动，与服务器连接中断，请重新登录！！！！</color> | 网络波动，与服务器连接中断，请重新登（s5 服务器可能未启动或登录链路异常）

## 关联截图
- opened: `E:\workproject\reports\e2e_login_20260901_150340\screenshots\01_opened.png`
- server_selected: `E:\workproject\reports\e2e_login_20260901_150340\screenshots\02_server_selected.png`
- login_clicked: `E:\workproject\reports\e2e_login_20260901_150340\screenshots\03_login_clicked.png`
- error: `E:\workproject\reports\e2e_login_20260901_150340\screenshots\99_error.png`
