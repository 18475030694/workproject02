# 测试用例：登录流程-选服s5服-账号1351

| 项目 | 内容 |
|---|---|
| 用例编号 | TC_LOGIN_001 |
| 用例标题 | 登录流程-选服s5服-账号1351 |
| 优先级 | P0 |
| 测试类型 | 端到端(E2E) / UI + 后端校验 |
| 目标地址 | http://localhost:7456 |
| 测试账号 | 1351 |
| 目标服务器 | s5服（解析 svr_id=None） |
| 运行模式 | 无头 |
| 开始时间 | 2026-09-01T14:58:49 |
| 结束时间 | None |
| **测试结果** | **失败(FAIL)** |

## 前置条件
1. 游戏页面 `http://localhost:7456` 可达（HTTP 200）。
2. 客户端内置 QA Bridge（`window.__qa`）可用。
3. **目标服 s5服（svr_id=None）必须已启动且可被平台服正常分配** —— 否则登录应判失败（这正是本用例要拦截的「假通过」场景）。
4. 测试账号 `1351` 在目标服有效。

## 测试步骤

| 步骤 | 操作 | 预期结果 | 实际结果 | 状态 |
|---|---|---|---|---|
| 1 | 输入账号 | 账号 1351 注入 localStorage | 已注入 TMP_ACCOUNT_=1351 | done |
| 2 | 打开游戏 | 游戏页面加载，QA Bridge 就绪，服务器列表已获取 | QA Bridge 就绪 | failed |

## 结论
存在步骤未通过，详见上方状态列与下方错误信息。常见原因：目标服 s5 未启动 / 平台服未启动 / 账号在 s5 无角色。

## 错误信息
Page.wait_for_function: ReferenceError: Global is not defined
    at eval (eval at predicate (eval at evaluate (:311:30)), <anonymous>:1:36)
    at predicate (eval at evaluate (:311:30), <anonymous>:13:29)
    at next (eval at evaluate (:311:30), <anonymous>:29:33)
    at eval (eval at evaluate (:311:30), <anonymous>:42:13)
    at UtilityScript.evaluate (<anonymous>:313:16)
    at UtilityScript.<anonymous> (<anonymous>:1:44)

## 关联截图
- opened: `E:\workproject\reports\e2e_login_20260901_145849\screenshots\01_opened.png`
- error: `E:\workproject\reports\e2e_login_20260901_145849\screenshots\99_error.png`
