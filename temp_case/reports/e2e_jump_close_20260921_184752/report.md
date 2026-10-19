# cfg_sys_jump 跳转界面 29/43/46/181/182「跳转后无法关闭」修复验收报告

- **测试时间**: 2026-09-21 18:47~18:54（run: e2e_jump_close_20260921_184752）
- **环境**: localhost:7456 预览客户端（QA 注入），账号 4451 / S5
- **执行方式**: Playwright + window.__qa 运行时注入，真实登录主城后按用户指定路径（背包→道具→道具tips获取途径）验证
- **脚本**: temp_case/scripts/e2e_jump_close.py；数据 data.json；截图 screenshots/

## 结论：验收通过 ✅

修复已在测试客户端生效：获取途径中「每日特惠→29」「七天签到→43」跳转入口已被移除，点击后不再跳转（tips 保持打开）；其他获取途径跳转回归正常且目标界面可关闭。

## 一、验收口径（用户确认「两者都验」）

1. **Part A 真实路径**：验证获取途径点「每日特惠/七天签到」不再跳转（修复生效）+ 回归其他获取途径跳转正常且目标界面可关闭。
2. **Part B 直开留证**：模拟旧跳转路径直开 5 个界面，实测关闭行为留证。

## 二、根因与修复方式（已核实）

- **根因**：5 个界面（29 每日特惠/UIRechargeDailyGift、43 七天签到/UISevenDaySign、46 精彩活动/UISevenDailyTaskMain、181 零元购/UIZeroPricePurchase、182 6元狂欢/UIMicroPayment）均为 `UIComIntegrationTabView` 内嵌页签，自身关闭按钮仅 `eventEmit(MSG_ON_INTEGRATION_TABVIEW_CLOSE)`，只有父容器（UIComIntegrationTabView.ts L127）监听该消息执行 uiHide。获取途径直开页签时无父容器 → 点关闭无反应。
- **修复（r10605/r10606，2026-09-21）**：从 cfg_item_source（json+xlsx）移除「每日特惠→29」（道具 5 灵力/1000 凡灵召符/1006 武器零件/1007 炼宝玉佩）与「七天签到→43」（道具 30005 战车突击）的 goWin（置 null）。**修复方式=移除跳转入口**，而非让页签可自关闭。
- 46/181/182：核实从未有任何获取途径条目指向，历史上不可经此路径触发。

## 三、执行结果汇总

| 用例 | 内容 | 结果 |
|---|---|---|
| P0 | 运行时配置确认：5 条修复条目 goWin 全为 null；cfg_sys_jump 29/43/46/181/182 五行 ui_name 齐全 | **PASS** |
| A1 | 获取途径点「每日特惠」→ 不跳转，tips 仍打开（修复生效） | **PASS** |
| A2 | 获取途径点「七天签到」→ 不跳转，tips 仍打开（修复生效） | **PASS** |
| A3 | 回归：灵力 tips 点「挂机奖励」(goWin=10) → UIGuaJi 正常打开，点 CloseBg_ 正常关闭 | **PASS** |
| B29/B43/B46/B181/B182 | 直开 5 个界面留证：点击各自关闭候选（BtnBg_/BtnClose_/BtnBg/BtnBg/CloseBtn）后仍激活 → 直开场景无法关闭 | **FACT×5**（预期留证，非缺陷） |

## 四、关键证据

- **P0**：`fixed goWin全空=True; jumps={'29':'UIRechargeDailyGift','43':'UISevenDaySign','46':'UISevenDailyTaskMain','181':'UIZeroPricePurchase','182':'UIMicroPayment'}` —— 修复配置在运行时生效。
- **A1**（灵力 tips）：条目 `['仙机-紫霄灵币','主线关卡','挂机奖励','每日特惠']`；点击「每日特惠」后 UIRechargeDailyGift 激活=False（预期），tips 仍在=True（goWin=null 时 UIItemTips.ts 直接 return，不隐藏不跳转）。截图 A1_tips_open.png / A1_after_click_daily.png。
  - 注：本轮 A1 经等价直调兜底打开灵力 tips；前一轮（run 184143）已用**真实背包点击路径**（凡灵召符，条目含每日特惠）验证同样 PASS，两轮结论一致。
- **A2**（战车突击 tips）：条目含「七天签到」；点击后 UISevenDaySign 激活=False（预期），tips 仍在=True。截图 A2_after_click_qiandao.png。
- **A3**（回归）：点「挂机奖励」→ UIGuaJi 打开=True；点击 CloseBg_ → 关闭=True。截图 A3_guaji_open.png / A3_guaji_after_close_CloseBg_.png。证明其余获取途径跳转链路未受修复影响。
- **Part B 留证**：5 个界面直开（showUI）后，遍历点击各自关闭候选节点，关闭后仍激活=True —— 直开场景确无法关闭（页签设计依赖父容器）。由于修复已移除全部指向入口，该场景正常玩家不可达；本组为行为留证。截图 B*{open,after_close}.png。

## 五、遗留风险与建议

1. **死条目（体验小瑕疵）**：goWin=null 的「每日特惠/七天签到」条目仍显示在获取途径列表中，点击无任何反应。建议后续：tips 渲染时过滤 goWin 为空的条目，或策划侧从 cfg_item_source 删除这两类条目。
2. **直开不可关闭仍未修**：5 个页签界面的自关闭仍依赖父容器消息，若未来其他入口（如新的获取途径、GM/埋点跳转）再指向 id 29/43/46/181/182，原 bug 会复现。可考虑在页签自身关闭回调中兜底「无父容器时直接 uiHide」。
3. **xlsx 源表**：cfg_item_source 的 xlsx 源表 goWin 已同步置空（r10605/10606 含 json+xlsx），无再导出回退风险。

## 截图清单

00_main_city / A1_tips_open / A1_after_click_daily / A2_after_click_qiandao / A3_guaji_open / A3_guaji_after_close_CloseBg_ / B29_open / B29_after_close / B43_open / B43_after_close / B46_open / B46_after_close / B181_open / B181_after_close / B182_open / B182_after_close（均在 screenshots/ 下）
