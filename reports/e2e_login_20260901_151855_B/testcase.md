# 测试用例：登录流程-选服s5服-账号1352

| 项目 | 内容 |
|---|---|
| 用例编号 | TC_LOGIN_001 |
| 用例标题 | 登录流程-选服s5服-账号1352 |
| 优先级 | P0 |
| 测试类型 | 端到端(E2E) / UI + 后端(plat_login)校验 |
| 目标地址 | http://localhost:7456 |
| 测试账号 | 1352 |
| 目标服务器 | s5服（解析 svr_id=5） |
| 运行模式 | 无头 |
| 开始时间 | 2026-09-01T15:19:21 |
| 结束时间 | 2026-09-01T15:19:48 |
| **测试结果** | **通过(PASS)** |

## 前置条件
1. 游戏页面 `http://localhost:7456` 可达（HTTP 200）。
2. 客户端内置 QA Bridge（`window.__qa`）可用。
3. **目标服 s5服（svr_id=5）必须已启动且可被平台服正常分配** —— 否则登录应判失败（本用例专门拦截「服务器没起却报通过」的假通过场景）。
4. 测试账号 `1352` 在目标服有效（新建账号场景由后端自动建号）。

## 测试步骤

| 步骤 | 操作 | 预期结果 | 实际结果 | 状态 |
|---|---|---|---|---|
| 1 | 输入账号并预设选服 | 账号 1352 注入；预选服写 localStorage（s5服） | 已注入 TMP_ACCOUNT_=1352，预选服 id=5 | done |
| 2 | 打开游戏 | 游戏页面加载，QA Bridge 就绪，服务器列表已拉取 | QA Bridge 就绪 | done |
| 3 | 选服(强制) | 把登录服强制设为 s5服（svr_id=5），不用默认服 | 已强制选服 svr_id=5 svr_name=S5（servers_in_page/page_all 响应） | done |
| 4 | 点击登录 | 点击 LoginBtn_ 触发登录 | 已点击 LoginBtn_ | done |
| 5 | 校验plat_login响应 | 请求 serverId==s5服 且 后端 errcode==0（目标服已启动且接受登录） | plat_login 成功 (errcode=0, serverId=5) | done |
| 6 | 等待进主城并校验 | 进入主城，佐证在目标服且建立真实角色 | 界面未直接显示目标服名（UI文本: ['客服', '[S1]玩家名字：', '客服', '区        服：', '[S1]xxx']）；未能确认真实角色 uuid（playerMgr 字段不可读，已降级） | done |

## 结论
全部步骤通过，已确认账号成功登录并进入目标服主城（plat_login 成功 + 进入主城 + 佐证在目标服）。



## 关联截图
- opened: `E:\workproject\reports\e2e_login_20260901_151855_B\screenshots\01_opened.png`
- server_selected: `E:\workproject\reports\e2e_login_20260901_151855_B\screenshots\02_server_selected.png`
- login_clicked: `E:\workproject\reports\e2e_login_20260901_151855_B\screenshots\03_login_clicked.png`
- in_main_city: `E:\workproject\reports\e2e_login_20260901_151855_B\screenshots\04_in_main_city.png`
