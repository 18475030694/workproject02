192.168.*.*# 仙机→秘宝 回退验收 · 静态检查报告（①-④）

- 日期：2026-09-28　执行：AI 测试（会话重启后复核版）
- 对象：E:\p1-x\trunk（HEAD r10763，svn st 无秘宝相关本地改动）
- 基准：E:\p1-x\tag = svn ^/tags/2026-08-10（原始秘宝基准包）；E:\p1-x\tag_new = ^/tags/2026-09-11（仙机版包）
- 方法：本地文件 Read/Grep/md5 + svn log/cat/info 三方交叉验证；所有伪造嫌疑输出已弃用并标注

## 0. 回退提交考古（svn log 闭环，无缺失区间）

cfg_box_base.lua（服务端）提交序列：
- r9661 09-02「秘宝改仙机」（仙机期开始，钱币名引入）
- r9782 09-04 数值调整
- r10068/10079/10106/10118 09-09 秘宝系列（去掉首次必得等）
- r10316 09-11「秘宝大奖」+ r10337 09-11 法宝
- r10376/r10412 09-14 仙机（仙机期后段，倍率 4 档 {50,37,9,4}，svn cat r10411 证实）
- **r10731 09-28 12:11【配置excel】"仙机"改"秘宝"（服务端全量清扫）**
- **r10732 09-28 12:11【配置json】"仙机"改"秘宝"（客户端全量清扫）**
- **r10741 09-28 14:27「开箱子恢复」（cfg_box_base + cfg_section_reward）**
- r10755 TreasureBoxMgr 恢复、r10762 15:48 UITreasureBox.prefab 修改（qinglin）

**关键判定**：r10741 恢复内容 = 矿石名 + first_reward + cfg_section_reward（与 tag 完全一致 ✓）；**倍率表（5 档含 3 倍）、noticeDrawTimes、pack_pool 简化结构是刻意保留的仙机期产物，未回退到 tag 状态**。r10411（09-14 仙机中期）倍率为 4 档 {1,5000},{2,3700},{4,900},{10,400}（无 3 倍档）；trunk 现存 5 档 {52,30,8,6,4} 为仙机后段调整，**不是任何"秘宝"历史状态**。

## 1. ①文本/命名修改检查

### 1.1 已完成回退（✓）
| 项 | 证据 |
|---|---|
| 服务端 cfg_box_base.lua box_name | 矿石系：绿莹砂石/蓝翡精石/紫罗矿晶/玄黄矿玉/绯红灵玉（=tag） |
| 客户端 cfg_box_base.json | 矿石名 + icon=baoxiang01-05 + 材料类 desc（凝气丹/突破丹/灵力/装备精魄/仙玉） |
| 客户端 cfg_box_exchange.json | trunk==tag (md5 5F1124AF)，矿石名兑换配置 |
| 服务端 cfg_section_reward.lua | trunk==tag (md5 CA5276) |
| 入口/界面 | UITreasureBoxTabView→cls:"UITreasureBox"（旧UI）；New UI 无调用方（仅 UIConfig 注册） |

### 1.2 玩家可见残留（✗ 需修复）
| 文件 | 内容 | 当前风险 |
|---|---|---|
| client cfg_bulletin_msg.json + server cfg_bulletin_msg.lua | `"BigOpenBox":"恭喜%s仙友，欧皇附体，使用%s注%s摇中仙机<10倍>超级大奖"` | 发送代码 mod_open_box.lua L199-205 已注释 → 休眠；但文本含"注/摇中/仙机/10倍"赌博话术，一旦代码恢复即全服跑马灯。r10731 清扫漏掉 |
| server cfg_sys_msg.lua | 同 BigOpenBox 文案 | 同上（聊天系统消息路径） |
| client cfg_intelligence_info.json + server .lua | 情报条目 `"name":"仙机祸影"`（r9654 09-02 仙机期引入） | 玩家可见图鉴/情报文案，清扫漏网 |

### 1.3 代码级残留（休眠/低危）
- GameEnum.ts: `BAO_XIANG = 8 // 启动仙机` 注释、RATE_TYPE 枚举（1/2/3/4/10）
- UITreasureBoxTabView.ts L2 注释「仙机」
- TreasureBoxMgr.ts: `slotPathArr=[treasurebox_icon02_laohujituan01..04]`、`getSlotResultArrByRate()`（唯一调用方=休眠的 UITreasureBoxNew.ts:311）、requestOpenBox 仍把 `resp.rate` 广播进 MSG_ON_TREASURE_OPEN_BOX
- UITreasureBoxNew.ts + SlotMachineBox.ts（老虎机转轮整套实现）仍在 trunk，会打进构建包
- words.txt/SensitiveWords.ts 的「老虎机」为敏感词库，应保留 ✓；UISoulBeastHurtScene 的「老虎机」为魂兽追击玩法，与本次回退无关

## 2. ②prefab 修改检查

| prefab | trunk vs tag | 老虎机/仙机引用 |
|---|---|---|
| UITreasureBox.prefab（激活） | **不一致**（r10762 15:48 修改，差异内容因工具污染未能可靠定性） | grep laohujituan/仙机/老虎 = 无命中 ✓ |
| UITreasureBoxRewards.prefab（激活，结算） | **一致**（md5 20F7B86D，两次独立验证） | 无命中 ✓ |
| UITreasureBoxNew.prefab（休眠） | 含 1 处「仙机」字样 | 引用老虎机美术（见③） |

结论：激活链路 prefab 无老虎机元素引用；UITreasureBox.prefab 与 tag 存在差异但不含违禁引用（定性待人工用 TortoiseSVN diff 复核一次）。

## 3. ③美术字/图片资产检查

images/treasurebox/ 目录现存两代资产共存：
- 秘宝代：treasurebox_icon01_baoxiang01-05.png（cfg_box_base.json 引用，激活）
- 仙机代（休眠但随包发布）：treasurebox_icon02_laohujituan01-04.png（老虎机图标×4）、treasurebox_img02_laohuji_lagan01.png（拉杆）、treasurebox_img02_laohuji_gold00.png 等；img_collection.json 中 8 处 laohujituan 索引

- 激活 prefab/脚本/配置均未引用 laohujituan 图（仅休眠 UITreasureBoxNew + TreasureBoxMgr.slotPathArr 引用）
- **风险**：休眠 UI 代码+图片仍会打包进客户端构建产物，合规角度建议物理删除或排除出构建

## 4. ④按钮修改检查

- 开箱按钮走 I18N：I18N_TREASURE_BOX_BTN_TEXT（初步证据值≈「开启{1}个」）、I18N_TREASURE_BOX_GAP_TIP「还差{1}秘宝值领取{2}」——秘宝语义，无「投注/摇奖」话术（cfg_langs 完整值提取受工具污染，运行时⑤以截图复核为准）
- UIConfig 定义的按钮：ExchangeBtn(兑换)/OpenBtn(开箱)/BtnDetail(说明)/SkipTog(跳过动画)/BtnAdd(看广告)/BtnClose——与旧秘宝功能集一致
- 休眠 UITreasureBoxNew.prefab 内含 1 处「仙机」字符串（随包但不可达）

## 5. 服务端奖励机制核对（⑥⑦的判定依据）

mod_open_box.lua（C2gsOpenBox）实际生效链路：
1. first_reward：首开固定奖励（trunk 已恢复，见下表）
2. is_section=1 → _SectionDraw：按主线进度查 cfg_section_reward[boxId] 分段，逐抽按 weight 随机出材料（×特权加成）
3. _PoolDraw：遍历 pack_pool 组，非空组按权重抽 cfg_box_pack 卡包；**6000-6002 pack_pool 全空 → 无卡包加成**；6003=固定包1（凝气丹×5）；6004=每抽 4×固定包2（×40）
4. rate：**抽出但完全不参与奖励计算**（使用 rate 的两个函数已注释），仅 return 给客户端；旧 UI 不消费该值
5. 公告 BigOpenBox 判定代码已注释（见 1.2）

trunk vs tag first_reward：6001-6003 与 tag 完全一致；6000 用 {5009,1} 而 tag 为 {5222,1}——差异 1 处，需策划确认是否有意（5009 与 5222 均为 cfg_box_pack 9/11 号包内仙友）。

## 6. 待运行时验证（⑤⑥⑦⑧）

- ⑤ 玩家视角：旧 UI 是否正常打开、无老虎机/倍率元素、按钮文案截图
- ⑥ 结算显示 vs 实际：开箱掉落与 _SectionDraw+_PoolDraw 数学期望核对
- ⑦ 概率：静态期望已可推演（cfg_section_reward==tag + 固定包）；采样验证受货币获取限制，受限需注明
- ⑧ 回归：首开奖励/积分累计/兑换/跳过动画/红点/看广告

## 7. 结论（静态部分）

**回退整体完成度：高（玩家主链路已回秘宝），遗留 3 类问题：**
1. 【中危·玩家可见】公告/系统消息 BigOpenBox 赌博话术 + 情报「仙机祸影」文案漏扫（当前休眠不触发）
2. 【低危·合规】休眠老虎机整套代码（UITreasureBoxNew/SlotMachineBox/TreasureBoxMgr 转轮方法）+ 老虎机美术仍随包发布
3. 【待确认·数值】倍率表 5 档/noticeDrawTimes 残留（不生效但留于配置）；6000 首开奖励 5009≠tag 的 5222；UITreasureBox.prefab 与 tag 差异未定性
