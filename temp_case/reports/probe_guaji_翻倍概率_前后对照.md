# 挂机奖励30%翻倍概率 前后对照报告（v2广告通道）

- 前(baseline): E:\workproject\reports\probe_guaji_rate_20261015_032049  特权={'mul': 0, 'mul2': 0, 'card_valid': False}
- 后(after):    E:\workproject\reports\probe_guaji_rate_20261015_155354  特权={'mul': 3000, 'mul2': 3000, 'card_valid': True}

## tier1 对比

| item | 前obs | 前p̂ | 后obs | 后p̂ | p̂差 |
|---|---|---|---|---|---|
| 2 | 479592 | -0.9965 | 620749 | 0.2945 | 1.291 |
| 3 | 8894 | -0.8284 | 11697 | 0.3063 | 1.1347 |
| 5 | 6047 | -0.8445 | 7806 | 0.3077 | 1.1522 |

## 判定对比

- AD_2250_R1: 前=PASS / 后=INFO
- AD_2250_R2: 前=PASS / 后=INFO
- AD_2250_R3: 前=PASS / 后=INFO
- AD_2663_R1: 前=INFO / 后=PASS
- AD_2663_R2: 前=INFO / 后=PASS
- AD_2663_R3: 前=INFO / 后=PASS
- AD_6716_R1: 前=PASS / 后=INFO
- AD_6716_R2: 前=PASS / 后=INFO
- AD_6716_R3: 前=PASS / 后=INFO
- AD_7371_R1: 前=INFO / 后=PASS
- AD_7371_R2: 前=INFO / 后=PASS
- AD_7371_R3: 前=INFO / 后=PASS
- AD_7583_R1: 前=INFO / 后=PASS
- AD_7583_R2: 前=INFO / 后=PASS
- AD_7583_R3: 前=INFO / 后=PASS
- AD_8246_R1: 前=PASS / 后=INFO
- AD_8246_R2: 前=PASS / 后=INFO
- AD_8246_R3: 前=PASS / 后=INFO
- CFG_ROW_FITTED: 前=INFO / 后=INFO
- PREP: 前=INFO / 后=INFO
- PRIV_REF: 前=INFO / 后=INFO
- TIER1_DOUBLE_30PCT: 前=FAIL / 后=PASS
- TIER1_DROP_Z: 前=PASS / 后=PASS
- TIER2_DROP_Z: 前=INFO / 后=INFO