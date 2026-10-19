# 挂机奖励30%翻倍概率探针报告（smoke轮）

- 时间: 2026-10-14T19:04:22  账号: 4451@S5  cycles: 3(dt步进13000s)
- 特权快照: {'mul': 0, 'mul2': 0, 'card_valid': False, 'card_mul': None}
- 主线进度: None  实测档位: id=1
- 产物: E:\workproject\reports\probe_guaji_rate_20261014_190422

## 结论速览

- **[INFO] PRIV_SNAPSHOT**: GUAJI_MUL=0 GUAJI_MUL2=0 离线卡=False 卡特权值=None → tier1 期望 p=0.0, tier2 p=0.0 (口径30%=不吻合, 以读数为准)
- **[INFO] PASSID_PROBE**: 主线进度读取: None
- **[INFO] CFG_ROW_EST**: passId=None → 预估档位 id=None (interval1=5, interval2=None); 采样后按产出拟合校准
- **[INFO] LASTRECV_AHEAD**: lastReceiveTime=-1 服务器时间=1792178316 → 超前=0s
- **[PASS] CYCLE0_RESET**: 清零成功 last_recv=1792178491, 丢弃产出=[{'id': 1001, 'count': 1}, {'id': 1002, 'count': 1}, {'id': 2, 'count': 320}, {'id': 3, 'count': 11}, {'id': 5, 'count': 8}] (dt_base=85000)
- **[INFO] CFG_ROW_FITTED**: 产出拟合档位 id=1 (|z|均分=3.39, n1=49) vs passId预估=None → 不一致/预估缺失, 以拟合为准
- **[FAIL] TIER1_DROP_Z**: tier1 掉落+翻倍联合 z 检验 (n=49, p=0.0): {'2': -6.43, '3': -2.18, '5': -1.57}
- **[FAIL] TIER1_DOUBLE_30PCT**: 翻倍率反推 p̂(per-item)=[-0.5339, -0.9835, -0.9876] 期望 p=0.0 → z=[-7.4, -83.65, -98.77] 判定见z
- **[INFO] TIME_RESTORE**: 还原应答=ERR <urlopen error timed out> 服务器时间=None 本地=1791976210 漂移=Nones (无法读服务器时间, 请人工核对)

## tier1 明细（掉落频率 + 翻倍率联合 z 检验）

n=49, 期望翻倍率 p=0.0（来源: runtime_getPrivilegeVal）

| item | 实测 | 期望 | z | p̂(翻倍率) | z(p̂) |
|---|---|---|---|---|---|
| 2 | 113 | 225.4 | -6.43 | -0.5339 | -7.4 |
| 3 | 4 | 10.2 | -2.18 | -0.9835 | -83.65 |
| 5 | 3 | 6.8 | -1.57 | -0.9876 | -98.77 |

## 逐轮记录

| cycle | dt | elapsed | n1 | n2 | 产出 |
|---|---|---|---|---|---|
| 0 | 85000 | - | - | - | - |
| 1 | 98000 | 42 | 8 | 0 | 3×1 2×36 5×1 |
| 2 | 111000 | 84 | 16 | 0 | 2×36 3×2 5×1 |
| 3 | 124000 | 127 | 25 | 0 | 3×1 5×1 2×41 |

## 静态依据

- [mod_guaji_reward.lua L248-271](file:///E:/p1-x/trunk/server/src/lua-server/service/lobby/guaji/mod_guaji_reward.lua#L248-L271): 每掷点每条目 r=math.random(0,10000) vs 权重掉落 → 命中后 r2 vs nDoubleWeight 翻倍(*2); nDoubleWeight 取特权 GUAJI_MUL(10)/GUAJI_MUL2(22); 无离线闯关卡(7)时溢出部分进 privilege_reward_map 待补发
- [cfg_guaji_reward.lua](file:///E:/p1-x/trunk/server/src/res/Config/guaji/cfg_guaji_reward.lua): 156 行档位随主线; 高档位 tier1 全 w=10000 必中(数量随档位递增), tier2 权重恒 7000/2000/1400
- 统计口径: E[id]=N·Σ(w·m)·(1+p), Var=N·Σ(w·m²(1+3p)−(w·m(1+p))²); w=0 条目按实现怪癖 r=0 命中 1/10001 计
- 加速手段: GM set_timeshift(全服生效, 测后已还原 dt=0); 每轮 dt 递增 → 重登触发结算 → 协议直发领取
