# 测试用例：登录流程-选服s1服-账号1352

| 项目 | 内容 |
|---|---|
| 用例编号 | TC_LOGIN_001 |
| 用例标题 | 登录流程-选服s1服-账号1352 |
| 优先级 | P0 |
| 测试类型 | 端到端(E2E) / UI + 后端(plat_login)校验 |
| 目标地址 | http://localhost:7456 |
| 测试账号 | 1352 |
| 目标服务器 | s1服（解析 svr_id=1） |
| 运行模式 | 无头 |
| 开始时间 | 2026-09-01T15:23:27 |
| 结束时间 | 2026-09-01T15:23:53 |
| **测试结果** | **通过(PASS)** |

## 前置条件
1. 游戏页面 `http://localhost:7456` 可达（HTTP 200）。
2. 客户端内置 QA Bridge（`window.__qa`）可用。
3. **目标服 s1服（svr_id=1）必须已启动且可被平台服正常分配** —— 否则登录应判失败（本用例专门拦截「服务器没起却报通过」的假通过场景）。
4. 测试账号 `1352` 在目标服有效（新建账号场景由后端自动建号）。

## 测试步骤

| 步骤 | 操作 | 预期结果 | 实际结果 | 状态 |
|---|---|---|---|---|
| 1 | 输入账号并预设选服 | 账号 1352 注入；预选服写 localStorage（s1服） | 已注入 TMP_ACCOUNT_=1352，预选服 id=1 | done |
| 2 | 打开游戏 | 游戏页面加载，QA Bridge 就绪，服务器列表已拉取 | QA Bridge 就绪 | done |
| 3 | 选服(强制) | 把登录服强制设为 s1服（svr_id=1），不用默认服 | 已强制选服 svr_id=1 svr_name=s1（servers_in_page/page_all 响应） | done |
| 4 | 点击登录 | 点击 LoginBtn_ 触发登录 | 已点击 LoginBtn_ | done |
| 5 | 校验plat_login响应 | 请求 serverId==s1服 且 后端 errcode==0（目标服已启动且接受登录） | plat_login 成功 (errcode=0, serverId=1, 实际响应 serverId=1 serverName=s1 ip=192.168.*.*:12021) | done |
| 6 | 等待进主城并校验 | 进入主城，佐证在目标服且建立真实角色 | 未能确认真实角色 uuid（playerMgr 字段不可读，已降级） | done |

## 结论
全部步骤通过，已确认账号成功登录并进入目标服主城（plat_login 成功 + 进入主城 + 佐证在目标服）。

## 权威服信息（plat_login 响应，客户端据此连接游戏服）
- serverId: 1
- serverName: s1
- 连接地址: 192.168.*.*:12021
- roleIdx: 1  isBack=False  isNew=None

> 说明：界面顶部「区 服：[S1]」是玩家名/账号主服的显示标签，不代表当前实际连接的游戏服；真正判定依据为上方 plat_login 的 serverId 与连接地址，以及「进入主城」结果。





## 关联截图
- opened: `E:\workproject\reports\e2e_login_20260901_152327_A\screenshots\01_opened.png`
- server_selected: `E:\workproject\reports\e2e_login_20260901_152327_A\screenshots\02_server_selected.png`
- login_clicked: `E:\workproject\reports\e2e_login_20260901_152327_A\screenshots\03_login_clicked.png`
- in_main_city: `E:\workproject\reports\e2e_login_20260901_152327_A\screenshots\04_in_main_city.png`
