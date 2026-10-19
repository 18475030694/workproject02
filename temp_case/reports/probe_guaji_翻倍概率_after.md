# 挂机奖励30%翻倍概率探针报告 v2（after轮·广告通道）

- 时间: 2026-10-15T15:53:54  账号: ['7583', '7371', '2663']  档位: 主线19400→cfg[103](tier1全必中)
- 特权快照: {'mul': 3000, 'mul2': 3000, 'card_valid': True}  每号广告次数: 3×CalcReward(7200s)
- 产物: E:\workproject\reports\probe_guaji_rate_20261015_155354

## 结论速览

- **[INFO] PREP**: 7583: uuid=8589935654 sys10=True last_recv=1792250460 priv={'mul': 3000, 'mul2': 3000, 'card_valid': True} gm=ERR <urlopen error timed out>
- **[INFO] PREP**: 7371: uuid=8589935656 sys10=True last_recv=1792250460 priv={'mul': 3000, 'mul2': 3000, 'card_valid': True} gm=ERR <urlopen error timed out>
- **[INFO] PREP**: 2663: uuid=8589935586 sys10=True last_recv=1792252016 priv={'mul': 3000, 'mul2': 3000, 'card_valid': True} gm=ERR <urlopen error timed out>
- **[INFO] PRIV_REF**: 期望翻倍率来源: {'mul': 3000, 'mul2': 3000, 'card_valid': True} (读数缺失则按口径30%兜底)
- **[INFO] CFG_ROW_FITTED**: 产出拟合档位 id=31 (|z|均分=0.9), reward1=[[2, 35, 10000], [2, 2, 10000], [3, 1, 6909], [3, 3, 0], [5, 1, 4606], [5, 2, 0]] interval1=5
- **[PASS] TIER1_DROP_Z**: tier1 掉落+翻倍联合 z 检验 (9次广告, n=12960, p=0.3, 档位31): {'2': -1.44, '3': 0.7, '5': 0.56}
- **[PASS] TIER1_DOUBLE_30PCT**: 翻倍率 p̂(per-item)=[0.2945, 0.3063, 0.3077] 期望 p=0.3 z=[-1.44, 0.7, 0.56]  (特权读数 {'mul': 3000, 'mul2': 3000, 'card_valid': True})
- **[INFO] TIER2_DROP_Z**: tier2 z 检验 (n=216, p=0.3, 参考级): {'1001': -0.15, '1002': 4.0, '1003': 0.1}

## tier1 明细（广告通道, 掉落+翻倍联合 z 检验）

n=12960 掷, 期望翻倍率 p=0.3

| item | 实测 | 期望 | z | p̂(翻倍率) | z(p̂) |
|---|---|---|---|---|---|
| 2 | 620749 | 623376.0 | -1.44 | 0.2945 | -1.44 |
| 3 | 11697 | 11640.3 | 0.7 | 0.3063 | 0.7 |
| 5 | 7806 | 7760.2 | 0.56 | 0.3077 | 0.56 |

## tier2 明细（n 较小, 参考级）

n=216, p=0.3

| item | 实测 | 期望 | z | p̂ | z(p̂) |
|---|---|---|---|---|---|
| 1001 | 195 | 196.6 | -0.15 | 0.2897 | -0.15 |
| 1002 | 89 | 56.2 | 4.0 | 1.0602 | 4.0 |
| 1003 | 40 | 39.3 | 0.1 | 0.3228 | 0.1 |

## 逐次记录

| 账号 | 轮次 | 成功 | errcode | 背包增量 |
|---|---|---|---|---|
| 7583 | 1 | True | 0 | 2×68342 3×1273 5×831 1001×24 1002×14 1003×7 |
| 7583 | 2 | True | 0 | 2×69751 3×1307 5×866 1001×17 1002×10 1003×9 |
| 7583 | 3 | True | 0 | 2×68899 3×1311 5×897 1001×28 1002×6 1003×6 |
| 7371 | 1 | True | 0 | 2×68780 3×1251 5×810 1001×19 1002×13 |
| 7371 | 2 | True | 0 | 2×69156 3×1300 5×914 1001×24 1002×13 1003×3 |
| 7371 | 3 | True | 0 | 2×68593 3×1314 5×864 1001×17 1002×6 1003×4 |
| 2663 | 1 | True | 0 | 2×68563 3×1297 5×832 1001×23 1002×7 1003×1 |
| 2663 | 2 | True | 0 | 2×68984 3×1318 5×901 1001×20 1002×6 1003×4 |
| 2663 | 3 | True | 0 | 2×69681 3×1326 5×891 1001×23 1002×14 1003×6 |

## 已知干扰与边界

- 主城挂机战斗掉落同窗口进背包（比例<0.1%, item2 万级产出下可忽略）
- item2 单次产出约 2000 万（翻倍部分另计 30%）, 已用 item3/item5（单次≈1872/5616）作主判据防溢出干扰
- 广告每日 3 次/号: 连续两轮采样需跨日或补号

## 静态依据

- [mod_guaji_reward.lua L248-271](file:///E:/p1-x/trunk/server/src/lua-server/service/lobby/guaji/mod_guaji_reward.lua#L248-L271): 每掷点每条目 r=math.random(0,10000) vs 权重 → 命中后 r2 vs nDoubleWeight 翻倍; nDoubleWeight=GetPrivilege(GUAJI_MUL=10)/GUAJI_MUL2(22)
- [mod_advert.lua L133-168](file:///E:/p1-x/trunk/server/src/lua-server/service/lobby/advert/mod_advert.lua#L133-L168): C2gsAdvertFinish 无真实广告校验, cd/count 校验后直接 OnFinishCallback → guaji OnAdvertCallback → CalcReward(7200)
- [cfg_advert.lua](file:///E:/p1-x/trunk/server/src/res/Config/advert/cfg_advert.lua): ad_type=1 count=3 cd=1
- [cfg_guaji_reward.lua [103]](file:///E:/p1-x/trunk/server/src/res/Config/guaji/cfg_guaji_reward.lua#L818-L824): 主线19400档 tier1 全必中 {{2,10605},{2,2},{3,1},{3,3},{5,1},{5,2}}×w10000, tier2 7000/2000/1400
