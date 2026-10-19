---
name: "game-prob-verify"
description: "p1-x 概率/数值生效抽样验证：协议级大样本采样、z检验/3σ判定、取值域需求口径判定、GM分批发币。凡用户要求验证概率生效/概率字段/掉率/期望频率/随机数值口径时调用；UI功能测试仍走 game-ui-e2e-test。"
---

# 概率/数值生效抽样验证（p1-x）

验证「配置概率是否真实生效」「实测频率是否符合需求口径」类问题时，**复用以下方法论与模板，不要从零写**。UI 功能断言类测试走 `game-ui-e2e-test` skill（QA注入/GM铁律/登录流程均引用它，本文不重复）。

## 1. 资产地图

| 用途 | 文件 |
|---|---|
| 概率探针模板（登录+采样+统计+报告全套） | `E:\workproject\temp_case\scripts\probe_mibao_rate.py` |
| UI E2E 基础库（wait_qa_bridge/force_select_server） | `E:\workproject\harness\e2e_login.py` |
| GM 发道具（本模板内置 gm_award 直调 HTTP） | `E:\workproject\harness\gm_account.py` |

产物规范：data.json 放 `reports/probe_*_<ts>/`，MD 报告放 `temp_case/reports/`。

## 2. 核心方法论（五步）

1. **静态依据先行**：先 Grep 服务端 lua，确认概率实现读哪个配置字段、怎么抽（如 mod_open_box.lua L117-122 仅读 `boxCfg.rate` → `Utils.RandGet` 按权重抽取）。配置基线（如 CFG_RATE 万分比）写进脚本常量，结论必须引静态依据。
2. **协议级直发采样**：`Network.call('c2gs_xxx', args)` 直发，绕过客户端拦截弹窗（如卡池可升级拦截）。注入句柄见 §3。
3. **统计判定（字段生效）**：单开采样 → 每档位算 z 值，全部 `|z|≤3` 且取值域不超配置 → 字段权重生效。公式：`z=(f-p)/sqrt(p(1-p)/n)`，容差 `3σ` 随 n 收敛（n=20000 时 50% 档约 ±1.06pp）。
4. **取值域判定（需求口径）**：需求概率与实现概率**分离判定**——需求口径（如「图案组合决定1~4倍」）不看 z 检验，看取值域：需求外档位出现（10倍）、需求内档位缺失（3倍）→ 需求口径未生效，单独 rec（INFO）。
5. **整批复核**：`times=N` 验证整批共用单倍率 + 扣币基数一致性（before-after == N×cost）。

## 3. 协议级注入句柄（JS_HEAD，区别于 UI 句柄）

```js
window.__NET = () => { for (const [k, v] of System.entries()) { if (v && v.Network && v.Network.call) return v.Network; } return null; };
window.__NETC = (payload) => new Promise((resolve) => { const net = window.__NET(); if (!net) return resolve({ ok: false, resp: { err: 'no Network' } });
  net.call(payload.proto, payload.args || {}, (ok, resp) => resolve({ ok, resp })); setTimeout(() => resolve({ ok: false, resp: { timeout: true } }), 15000); });
window.__ITEM = (id) => { try { return SystemModules.knapsackMgr.getItemCount(id); } catch(e) { return -1; } };
```

- `qa(page, expr, default)` 兜底防异常（同 UI skill）
- 配置下发核对：遍历 `ShareRes.cfg_xxx[id]` 取字段与静态基线比对（CFG_FIELD 检查；字段缺失=已知行为，记录即可，以服务端配置为准）

## 4. 关键铁律（踩过的坑）

1. **整批共用一个倍率**：`times=N` 的返回 rate 是整批共用的，**不能**用批量结果统计单次概率 → 统计必须 `times=1` 单开
2. **GM 发币分批**：单次发放有上限，`min(10000, need-have+50)` 循环发 + 每轮 sleep(1) 重查持有（ensure_currency）
3. **采样节奏**：~0.12s/次，20000 次约 40 分钟 → 必须后台跑，每 100 次 wait_for_timeout(150) 防卡死，进度带 elapsed/fails 打日志
4. **fails 要单独计数**：rate=None（超时/网络）不算进样本，否则污染频率
5. **others 取值域必须为空**：verdict 判定除 |z|≤3 外，还要断言无配置外档位出现
6. headless 启动加 `--disable-background-timer-throttling` 等三参数，防止后台节流拖慢采样
7. 判定结果分级：字段生效（PASS/FAIL）与需求口径符合（INFO，人工判读）分开 rec，避免机器判定掩盖口径分歧

## 5. 标准流程

1. 读需求文档确定「需求概率口径」（无数值文档时如实标注「口径来自用例/口头，无书面基线」）
2. Grep 服务端实现 → 定位概率字段与抽取逻辑 → 写静态依据
3. 复制 probe_mibao_rate.py 改：CFG 基线、协议名/参数、箱/档位映射、货币 item_id、样本量
4. 样本量参考：主样本 20000（核心档 z≤3）、次路径 3000、参考箱各 1200；先小样本(200)冒烟再放大量
5. 后台执行 → data.json 实时落盘（save() 每阶段调用，中断不丢）
6. 生成 MD 报告：结论速览 + 逐档位频率表（实测/期望/偏差/z/3σ）+ 需求口径判定 + 静态依据
