# 挂机奖励30%翻倍概率探针报告 v2（baseline_restat072744轮·广告通道）

- 时间: 2026-10-15T03:20:49  账号: ['2250', '6716', '8246']  档位: 主线19400→cfg[103](tier1全必中)
- 特权快照: {'mul': 0, 'mul2': 0, 'card_valid': False}  每号广告次数: 3×CalcReward(7200s)
- 产物: reports\probe_guaji_rate_20261015_032049

## 结论速览

- **[INFO] PREP**: 2250: uuid=8589935561 sys10=True last_recv=1792178944 priv={'mul': 0, 'mul2': 0, 'card_valid': False} gm=ERR <urlopen error timed out>
- **[INFO] PREP**: 6716: uuid=8589935492 sys10=True last_recv=1792179016 priv={'mul': 0, 'mul2': 0, 'card_valid': False} gm=ERR <urlopen error timed out>
- **[INFO] PREP**: 8246: uuid=8589935575 sys10=True last_recv=1792179075 priv={'mul': 0, 'mul2': 0, 'card_valid': False} gm=ERR <urlopen error timed out>
- **[INFO] PRIV_REF**: 期望翻倍率来源: {'mul': 0, 'mul2': 0, 'card_valid': False} (读数缺失则按口径30%兜底)
- **[INFO] CFG_ROW_FITTED**: 产出拟合档位 id=31 (|z|均分=1.25), reward1=[[2, 35, 10000], [2, 2, 10000], [3, 1, 6909], [3, 3, 0], [5, 1, 4606], [5, 2, 0]] interval1=5
- **[PASS] TIER1_DROP_Z**: tier1 掉落+翻倍联合 z 检验 (9次广告, n=12960, p=0.0, 档位31): {'2': None, '3': -1.14, '5': 1.37}
- **[PASS] TIER1_DOUBLE_30PCT**: 翻倍率 p̂(per-item)=[0.0002, -0.0067, 0.013] 期望 p=0.0 z=[-1.14, 1.37]  (特权读数 {'mul': 0, 'mul2': 0, 'card_valid': False})
- **[INFO] TIER2_DROP_Z**: tier2 z 检验 (n=216, p=0.0, 参考级): {'1001': -0.48, '1002': 0.14, '1003': -0.83}

## tier1 明细（广告通道, 掉落+翻倍联合 z 检验）

n=12960 掷, 期望翻倍率 p=0.0

| item | 实测 | 期望 | z | p̂(翻倍率) | z(p̂) |
|---|---|---|---|---|---|
| 2 | 479592 | 479520.0 | None | 0.0002 | None |
| 3 | 8894 | 8954.1 | -1.14 | -0.0067 | -1.14 |
| 5 | 6047 | 5969.4 | 1.37 | 0.013 | 1.37 |

## tier2 明细（n 较小, 参考级）

n=216, p=0.0

| item | 实测 | 期望 | z | p̂ | z(p̂) |
|---|---|---|---|---|---|
| 1001 | 148 | 151.2 | -0.48 | -0.0212 | -0.48 |
| 1002 | 44 | 43.2 | 0.14 | 0.0185 | 0.14 |
| 1003 | 26 | 30.2 | -0.83 | -0.1402 | -0.83 |

## 逐次记录

| 账号 | 轮次 | 成功 | errcode | 背包增量 |
|---|---|---|---|---|
| 2250 | 1 | True | 0 | 2×53280 3×1005 5×693 1001×16 1002×6 1003×3 |
| 2250 | 2 | True | 0 | 2×53280 3×992 5×644 1001×16 1002×6 1003×1 |
| 2250 | 3 | True | 0 | 2×53280 3×991 5×701 1001×13 1002×6 1003×2 |
| 6716 | 1 | True | 0 | 2×53280 3×991 5×676 1001×16 1002×6 1003×5 |
| 6716 | 2 | True | 0 | 2×53280 3×975 5×655 1001×21 1002×6 1003×3 |
| 6716 | 3 | True | 0 | 2×53282 3×982 5×696 1001×17 1002×2 1003×3 |
| 8246 | 1 | True | 0 | 2×53280 3×978 5×645 1001×13 1002×4 1003×3 |
| 8246 | 2 | True | 0 | 2×53315 3×975 5×675 1001×18 1002×6 1003×4 |
| 8246 | 3 | True | 0 | 2×53315 3×1005 5×662 1001×18 1002×2 1003×2 |

## 已知干扰与边界

- 主城挂机战斗掉落同窗口进背包（比例<0.1%, item2 万级产出下可忽略）
- item2 单次产出约 2000 万（翻倍部分另计 30%）, 已用 item3/item5（单次≈1872/5616）作主判据防溢出干扰
- 广告每日 3 次/号: 连续两轮采样需跨日或补号

## 静态依据

- [mod_guaji_reward.lua L248-271](file:///E:/p1-x/trunk/server/src/lua-server/service/lobby/guaji/mod_guaji_reward.lua#L248-L271): 每掷点每条目 r=math.random(0,10000) vs 权重 → 命中后 r2 vs nDoubleWeight 翻倍; nDoubleWeight=GetPrivilege(GUAJI_MUL=10)/GUAJI_MUL2(22)
- [mod_advert.lua L133-168](file:///E:/p1-x/trunk/server/src/lua-server/service/lobby/advert/mod_advert.lua#L133-L168): C2gsAdvertFinish 无真实广告校验, cd/count 校验后直接 OnFinishCallback → guaji OnAdvertCallback → CalcReward(7200)
- [cfg_advert.lua](file:///E:/p1-x/trunk/server/src/res/Config/advert/cfg_advert.lua): ad_type=1 count=3 cd=1
- [cfg_guaji_reward.lua [103]](file:///E:/p1-x/trunk/server/src/res/Config/guaji/cfg_guaji_reward.lua#L818-L824): 主线19400档 tier1 全必中 {{2,10605},{2,2},{3,1},{3,3},{5,1},{5,2}}×w10000, tier2 7000/2000/1400
