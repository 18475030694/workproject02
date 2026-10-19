# loc_check 核查报告 — mibao_xianji

生成时间：2026-09-21 16:13:01

## 参数

| 项目 | 内容 |
| --- | --- |
| 任务 | mibao_xianji |
| 描述 | 秘宝→仙机 改名核查（首个任务，兼作工具 ground truth 验证） |
| 术语 | 秘宝→仙机 |
| 验证集 A（当前trunk） | E:\p1-x\trunk |
| 原型 B（上一tag） | E:\p1-x\tag_new |
| tag 间变更条目 | （非 URL 对比，无） |
| 运行时间 | 2026-09-21 16:13:01 |

## 警告

- 两源差异极小（239/72364）——很可能刚打完新版本包导致上一tag与当前内容相同，对比可能无意义！请确认 tag 状态，或改用 repo tag 精确对比（list-tags 后传 URL）。

## 统计

| 级别 | 数量 |
| --- | --- |
| 确认漏改 | 11 |
| 疑似待复核 | 0 |
| 注释级 | 1 |
| 白名单命中 | 4 |

## 扫描源

- A 当前trunk（E:\p1-x\trunk，13106 文件）
- B 上一tag（E:\p1-x\tag_new，12967 文件）

## 对比汇总（当前trunk vs 上一tag）

| 文件 | 命中词 | 当前trunk | 上一tag | 状态 |
| --- | --- | --- | --- | --- |
| client/assets/scripts/logic/gameenum.ts | 秘宝 | 1 | 1 | 未修复（两侧均有） |
| client/assets/resources/ui/prefab/yxact/lottery/uiyxactlottery.prefab | 秘宝 | 1 | 1 | 未修复（两侧均有） |
| client/assets/resources/ui/prefab/yxact/zhongqiu/uiyxactzhongqiugift.prefab | 秘宝 | 1 | 1 | 未修复（两侧均有） |
| client/assets/resources/ui/prefab/yxact/zhongqiu/uiyxactzhongqiuwin.prefab | 秘宝 | 1 | 1 | 未修复（两侧均有） |
| export/l-聊天.xlsx | 秘宝 | 1 | 1 | 未修复（两侧均有） |
| export/p-跑马灯.xlsx | 秘宝 | 1 | 1 | 未修复（两侧均有） |
| export/x-限时活动-16额外奖励.xlsx | 秘宝 | 1 | 1 | 未修复（两侧均有） |
| export/z-主线任务.xlsx | 秘宝 | 3 | 3 | 未修复（两侧均有） |
| export/条件类型.xlsx | 秘宝 | 1 | 1 | 未修复（两侧均有） |
| server/src/lua-server/service/lobby/defines.lua | 秘宝 | 1 | 1 | 未修复（两侧均有） |
| client/assets/resources/cfg/langs/cfg_langs.json | 秘宝 | 1 | 1 | 未修复（两侧均有） |
| client/assets/scripts/logic/fuben/towermgr.ts | 秘宝 | 1 | 1 | 未修复（两侧均有） |
| export/y-语言包.xlsx | 秘宝 | 1 | 1 | 未修复（两侧均有） |
| server/src/res/config/langs/cfg_langs.lua | 秘宝 | 1 | 1 | 未修复（两侧均有） |

## 确认漏改 TOP 清单

| 文件 | 位置 | 命中词 | 上下文 |
| --- | --- | --- | --- |
| E:\p1-x\trunk\client\assets\resources\ui\prefab\yxact\lottery\UIYxActLottery.prefab | L4447 | 秘宝 | "_string": "月宫秘宝", |
| E:\p1-x\trunk\client\assets\resources\ui\prefab\yxact\zhongqiu\UIYxActZhongQiuGift.prefab | L928 | 秘宝 | "_string": "月宫秘宝", |
| E:\p1-x\trunk\client\assets\resources\ui\prefab\yxact\zhongqiu\UIYxActZhongQiuWin.prefab | L4864 | 秘宝 | "_string": "月宫秘宝", |
| E:\p1-x\trunk\export\L-聊天.xlsx | 系统消息!A53 | 秘宝 | 秘宝超级大奖 |
| E:\p1-x\trunk\export\P-跑马灯.xlsx | Sheet1!A54 | 秘宝 | 秘宝超级大奖 |
| E:\p1-x\trunk\export\X-限时活动-16额外奖励.xlsx | (sheet名)秘宝 | 秘宝 | 秘宝 |
| E:\p1-x\trunk\export\Z-主线任务.xlsx | 条件类型读取!B7 | 秘宝 | 开启绿色秘宝 |
| E:\p1-x\trunk\export\Z-主线任务.xlsx | Sheet1!F9 | 秘宝 | 秘宝开放 |
| E:\p1-x\trunk\export\Z-主线任务.xlsx | Sheet1!G9 | 秘宝 | 开秘宝引导 |
| E:\p1-x\trunk\export\条件类型.xlsx | 条件类型!A40 | 秘宝 | 领取X次秘宝值奖励 |
| E:\p1-x\trunk\server\src\lua-server\service\lobby\defines.lua | L12 | 秘宝 | OPEN_BOX 		= 3, 	-- 秘宝 |
