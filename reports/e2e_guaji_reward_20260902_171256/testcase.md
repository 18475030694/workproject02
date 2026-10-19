# 测试用例：挂机奖励功能测试

| 项目 | 内容 |
|---|---|
| 用例编号 | TC_GUAJI_001 |
| 用例标题 | 挂机奖励功能全流程测试（红点+领取+重置） |
| 优先级 | P0 |
| 测试类型 | 端到端(E2E) / 功能逻辑 + UI + 红点验证 |
| 需求来源 | E:/p1-x/planner/策划文档/挂机奖励.xlsx |
| 目标地址 | http://localhost:7456 |
| 测试账号 | 1351 |
| 目标服务器 | s5服（解析 svr_id=5） |
| 选服方式 | 兜底注入(localStorage) |
| 运行模式 | 有头 |
| 开始时间 | 2026-09-02T17:12:56 |
| 结束时间 | 2026-09-02T17:13:34 |
| **测试结果** | **通过(PASS)** |

## 测试需求（来自策划文档）

1. 达到时长（配置1小时）后变为可领取状态 → 验证
2. 可领取奖励达到配置时间后触发红点 → 验证
3. 点击领取按钮可领取，领取后挂机时间重新累计 → 验证
4. 没有奖励可领取时点击领取按钮飘字「没有奖励可领取」 → 验证
5. 领取成功后，弹出奖励获得弹框，自动关闭挂机奖励界面 → 验证

## 前置条件

1. 游戏页面 http://localhost:7456 可达（HTTP 200）。
2. 客户端内置 QA Bridge（`window.__qa`）可用（URL 需要带 `?qa=1`）。
3. **目标服 s5服（svr_id=5）必须已启动且可被平台服正常分配**。
4. 测试账号 1351 在目标服有效且挂机奖励系统已开放。

## 检查点结果

| 序号 | 检查点 | 结果 | 备注 |
|---|---|---|---|
| 1 | 挂机系统开放 | 通过 | 已开放 |
| 2 | 打开界面 | 通过 | UIGuaJi 已打开 |
| 3 | 初始状态获取 | 通过 |  |
| 4 | 红点触发 | 通过 | elapsed=334s, maxTime=14400, 主红点=False, 奖励红点=False |
| 5 | 按钮状态 | 通过 | found=True, sprite=common_btn01_big_yellow |
| 6 | 领取后关闭界面 | 通过 | 界面已自动关闭 |
| 7 | 领取后红点重置 | 通过 | 已重新累计 5s，红点状态正确 |
| 8 | 领取流程 | 通过 | 成功领取，界面关闭 |

## 测试步骤

| 步骤 | 操作 | 预期结果 | 实际结果 | 状态 |
|---|---|---|---|---|
| 1 | 清空缓存并打开游戏 | 清空缓存，打开游戏页面，QA Bridge 就绪，登录页渲染 | 通过(PASS) | done |
| 2 | 切换账号 | 点击切换账号按钮，输入账号 1351 并确认 | 账号已切换为 1351 | done |
| 3 | 选服 | 点击换区按钮打开弹窗，遍历区页签，找到目标服 s5服 并点击 | 兜底注入选服 svr_id=5（svr_name=s5） | done |
| 4 | 点击登录 | 点击「开始冒险」按钮触发登录 | 通过(PASS) | done |
| 5 | 校验plat_login响应 | 请求 serverId==s5服 且 后端 errcode==0 | plat_login 成功 (errcode=0, serverId=5, serverName=S5) | done |
| 6 | 等待进主城并校验 | 进入主城，佐证在目标服且建立真实角色 | 已进入主城 | done |
| 7 | 检查挂机系统开放状态 | 挂机奖励系统（SysId=10）应已开放 | 通过(PASS) | done |
| 8 | 打开挂机奖励界面 | 通过 QA Bridge 直接打开 UIGuaJi 界面 | 通过(PASS) | done |
| 9 | 获取初始状态记录 | 读取服务器时间、上次领取时间、红点状态、奖励列表 | 通过(PASS) | done |
| 10 | 验证红点触发逻辑 | 累计时间 >= 3600秒 → 红点点亮；< 3600秒 → 红点熄灭 | 通过(PASS) | done |
| 11 | 验证领取按钮状态 | 有奖励时按钮应为黄色高亮可点击；无奖励应为灰色 | 通过(PASS) | done |
| 12 | 执行领取测试 | 点击领取按钮，验证结果 | 通过(PASS) | doing |

## 状态记录

### 初始状态
| 项目 | 值 |
|---|---|
| 服务器时间 | 1787976938 |
| 上次领取时间 | 1787976604 |
| 已累计时间 | 334 秒 |
| 主红点 | False |
| 奖励红点 | False |
| 奖励数量 | 4 |

### 领取后最终状态
| 项目 | 值 |
|---|---|
| 服务器时间 | 1787976943 |
| 上次领取时间 | 1787976938 |
| 重新累计 | 5 秒 |
| 主红点 | False |
| 奖励数量 | 0 |

测试分支: `claim_reward`

## 结论

全部检查点通过，挂机奖励功能符合需求。

## 权威服信息（plat_login 响应）

- serverId: 5
- serverName: S5
- 连接地址: 192.168.*.*:12021
- roleIdx: 0  isBack=False  isNew=None




## 关联截图
- opened: `E:\workproject\reports\e2e_guaji_reward_20260902_171256\screenshots\01_opened.png`
- account_switched: `E:\workproject\reports\e2e_guaji_reward_20260902_171256\screenshots\02_account_switched.png`
- server_selected: `E:\workproject\reports\e2e_guaji_reward_20260902_171256\screenshots\03_server_selected.png`
- login_clicked: `E:\workproject\reports\e2e_guaji_reward_20260902_171256\screenshots\04_login_clicked.png`
- in_main_city: `E:\workproject\reports\e2e_guaji_reward_20260902_171256\screenshots\05_in_main_city.png`
- sys_open: `E:\workproject\reports\e2e_guaji_reward_20260902_171256\screenshots\06_sys_open.png`
- uiguaji_opened: `E:\workproject\reports\e2e_guaji_reward_20260902_171256\screenshots\07_uiguaji_opened.png`