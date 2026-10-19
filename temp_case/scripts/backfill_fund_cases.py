# -*- coding: utf-8 -*-
"""回填基金特权入口合并测试用例执行结果（静态代码走查结论）"""
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill

XLSX = r'E:\workproject\temp_case\cases\基金特权入口合并测试用例.xlsx'

# ============ 设置：是否默认生成"非通过用例汇总"sheet（放除通过以外的所有用例+空备注列） ============
ADD_NONPASS_SHEET = True

# ================= Sheet1 主用例 TC-001~TC-114 =================
S1 = {
"TC-001": ("通过｜主界面基金入口(UIMainViewMiddle.ts onClickWarOrder)打开合并界面UIWarOrderEntry，onShow未传索引时默认选中tab0=基础类页签。", "通过"),
"TC-002": ("通过｜特权入口点击打开UIPrivPanel(独立界面)，与基金界面UIWarOrderEntry为两个不同UI，符合'独立不同界面'。", "通过"),
"TC-003": ("通过｜UIWarOrderEntry仅含基础/消耗/任务3个页签与滚动列表、一键充值按钮，无任何特权内容。", "通过"),
"TC-004": ("特权为独立系统(UIPrivilegeMain/UIPrivPanel+PrivilegeMgr)，代码层无基金/战令内容；界面遍历需手测确认。", "手测确认"),
"TC-005": ("不通过(P2-17)｜入口显隐由功能开启配置控制(cfg_sys_open id=31'主线通关第40关')，与'账号下无任何基金开启'不联动；40关后无基金开启时主入口仍显示，打开为空界面。", "不通过"),
"TC-006": ("部分通过｜入口显示结果成立，但原因是功能开启条件(主线40关)而非'首个基金开启'联动；且TC-005场景会露出空界面。", "部分通过"),
"TC-010": ("通过｜cfg_warorder_open tab=1清单与处理2完全一致：炼宝1/2/3、乾坤藏甲1/2/3、仙友1/2/3、升级1、进阶1、神话仙友，无多余无遗漏。", "通过"),
"TC-011": ("通过｜tab=2：升级基金2~5、进阶基金2~5，与处理2一致。", "通过"),
"TC-012": ("通过｜tab=3：武器零件、灵源、神器、法阵、翅膀、坐骑6个基金，与处理2一致。", "通过"),
"TC-013": ("通过(代码层)｜客户端按cfg_warorder_open[syId][period].tab字段分组(WarOrderMgr.onData)；改配置后重新拉取即按新页签归组，需GM改配置手测。", "通过"),
"TC-020": ("通过｜页签显隐isTabOpen(tab)=该页签下存在已开启基金(WarOrderMgr)；无基础基金开启时基础页签隐藏。注：主入口本身40关后仍显示(见TC-005)。", "通过"),
"TC-021": ("通过｜任一基础基金开启(服务端推送gs2c_warorder_info)后isTabOpen(1)=true，页签显示。", "通过"),
"TC-022": ("通过｜升级/进阶2~5均未开启时isTabOpen(2)=false，消耗页签不显示。", "通过"),
"TC-023": ("不通过(P0-1)｜升级2~5开启需升级基金1免费+付费奖励全部领完(FinishPeriod含recharge_recv_index)，未充值玩家免费领完也不开启→消耗页签不显示；开启条件本身与处理4不符。", "不通过"),
"TC-024": ("不通过(P0-1/P0-2)｜同TC-023；且__IsOpenAll要求升级1与进阶1都完成才同步2~5，进阶2~5开启还耦合升级基金1进度。", "不通过"),
"TC-025": ("通过｜任务类6基金均未开启时isTabOpen(3)=false，任务页签不显示。", "通过"),
"TC-026": ("通过｜任一任务基金开启后任务页签显示。", "通过"),
"TC-027": ("通过(代码层)｜回归确认：is_end判定已修正(cost基金period1仅免费+付费奖励全部领完FinishPeriod两项索引均满才返回is_end，未领完不误删)；客户端领取回调updateRewardInfo收到is_end→删除fund并emit MSG_ON_WARORDER_CLOSED→Entry.refreshView→refreshTab+refreshContent页签/banner动态刷新，页签显隐按isTabOpen重算。需真机复核表现。", "通过"),
"TC-030": ("通过｜升级1免费未领完时FinishPeriod(1)=false，2~5不同步、未开启，符合'不批量开启'。", "通过"),
"TC-031": ("不通过(P0-1/P0-2)｜免费领完不批量开启：①FinishPeriod要求付费奖励也领完；②还需进阶基金1同时完成(__IsOpenAll硬编码两类都判断)；③未充值玩家recharge_recv_index恒为0，2~5永不开启。", "不通过"),
"TC-032": ("不通过(P0-1/P0-2)｜同TC-031：进阶1免费领完不会开启进阶2~5。", "不通过"),
"TC-033": ("不通过(P0-1)｜付费奖励阻塞开启：FinishPeriod(1)要求recharge_recv_index>=总档数，付费未领时2~5不开启，与'付费奖励不阻塞开启'直接冲突。", "不通过"),
"TC-034": ("字面通过｜仅领完升级1时进阶2~5确实不开启；但因P0-2耦合，此时升级2~5也不开启，整体与处理4不符(见TC-031)。", "部分通过"),
"TC-040": ("基础页签沿用原banner列表(UIWarOrderUnit)，布局需对照原版UI手测。", "手测确认"),
"TC-041": ("不通过(P1-7)｜已确认无代码控制隐藏页签：①基础类详情UIWarOrderComm.prefab中ToggleList_/_Tog1/_Tog2均active=True，UICommWarOrder.ts无任何ToggleList.active=false逻辑，且Tog2绑定了onClickToggleList回调，点击可切入showTaskPanel任务面板（任务页签可见且可用）；②消耗类详情UIWarOrderCost.prefab中ToggleList_/Tog1均active=True，UICostWarOrder.ts仅在updateRedpoint读取Tog1/RedPoint1设红点、无隐藏逻辑也未注册页签回调，Tog1单页签控件残留显示。页签实际会渲染在界面上，维持不通过。", "不通过"),
"TC-042": ("通过(代码层)｜消耗类基金score即主线通关数(服务端GetPassedId、主线通关事件刷新)，详情CurTxt显示当前积分(I18N_WARORDER_CUR_SCORE)；文案是否体现'通关数'语义需手测。", "通过"),
"TC-043": ("通过｜全代码无99999封顶(仅年份格式化有)，进度=99999可完整显示；但配套的封顶规则未实现(见TC-044)。", "通过"),
"TC-044": ("不通过(P2-12)｜CurTxt/进度直接显示原始数值，无99999封顶，超过99999会原样显示。", "不通过"),
"TC-050": ("不通过(P2-13需确认)｜banner奖励区仅展示第1档付费奖励图标(getWarOrderFirstRechargeReward返回rewards[1].recharge_reward)，非'所有解锁奖励'；需与策划确认是否为首档展示设计。", "不通过"),
"TC-051": ("通过｜banner奖励区为ScrollView(RewardScroll+ItemContent)，icon多时可滚动查看全部。", "通过"),
"TC-052": ("通过｜未充值时banner显示充值按钮(BtnRecharge.active=!is_recharge)并展示单基金金额(getRechargeMoney按buy_id取价)。", "通过"),
"TC-053": ("通过｜点击banner充值按钮buyProduct(config.buy_id)，每基金独立商品ID(如升级2=80002)，拉起单独订单非打包。", "通过"),
"TC-054": ("通过(代码层)｜回归确认已修复：①banner新增'已解锁'展示态(BtnAllreadyBuy，prefab Label='已解锁')，充值后切换显示且onClick空回调不可点；②充值成功即时刷新：服务端RechargeAction置is_recharge并SyncWarOrderUpdate→gs2c_warorder_info→WarOrderMgr.onData emit MSG_ON_WARORDER_GET_REWARD→UIWarOrderCostUnit.onWarorderUpdate即时切换充值/已解锁按钮，停留界面即生效无需重开。", "通过"),
"TC-055": ("通过(代码层)｜回归确认已修复：充值成功后banner即时切换为'已解锁'按钮(BtnAllreadyBuy)，onClickBtnAllreadyBuy为空回调点击无响应，不再出现停留期间可重复拉单的窗口；文案/视觉表现需真机确认。", "通过"),
"TC-056": ("通过(代码层)｜取消支付走sendRechargeFailed，无状态变更；is_recharge仅服务端回调成功后置位。需真机验证。", "通过"),
"TC-057": ("第二页签列表为新CostItemTpl banner模板，版式需对照UI稿。", "手测确认"),
"TC-058": ("'超值优惠'文案底衬为美术资源，需对照UI稿。", "手测确认"),
"TC-059": ("打包区充值按钮样式需对照UI稿。", "手测确认"),
"TC-060": ("通过｜存在未充值消耗类基金时BtnOneKeyRecharge显示且文案含价格；'或战令'当前范围仅基金，成立。", "通过"),
"TC-061": ("通过｜点击一键充值buyProduct(550001)，独立商品订单(one_key_buy_war_order.lua路由)。", "通过"),
"TC-062": ("通过(备注P2-18)｜550001回调同时调升级+进阶两类OneKeyBuyCostWarOrder，两类全部period置is_recharge=true并推送，消耗类2~5高级奖励全部解锁；备注：period1(基础页签升级1/进阶1)也被一并解锁，属需求外副作用。", "通过"),
"TC-063": ("通过(代码层)｜回归确认已修复：一键充值550001回调对升级/进阶两类全部period置is_recharge并逐period推送gs2c_warorder_info，客户端onData逐fund emit MSG_ON_WARORDER_GET_REWARD，各消耗banner即时切换为'已解锁'不可点态，无需重开界面。", "通过"),
"TC-064": ("通过(代码层)｜回归确认已修复：全部已充值后refreshOneKey令BtnAllreadyOneKey('已解锁')显示、BtnOneKeyRecharge隐藏；onShow即调refreshOneKey且监听MSG_ON_WARORDER_GET_REWARD即时刷新，显隐/金额不再依赖prefab默认值。", "通过"),
"TC-065": ("不通过(P1-10)｜550001为固定配置价商品，订单金额不按未充值基金动态统计；先单独充值1个基金再一键充值仍付全价，与澄清3不符。", "不通过"),
"TC-066": ("不通过(P1-10)｜已充值基金不会被重复解锁(OneKeyBuyCostWarOrder对已is_recharge的period跳过、幂等)，但玩家仍支付550001全价，订单层面对已购内容重复付费，与澄清3意图不符。", "不通过"),
"TC-067": ("解锁后走recv_reward领取流程，代码链路存在；前置'2~5开启'受P0-1影响需真机确认后走完整领取流程。", "手测确认"),
"TC-070": ("部分通过(P2-14已修)｜回归确认：未达成档位(isReach=false)仅显示UnReachBtn，不再与购买按钮同显(先统一置隐后按状态单显)；但UnReachBtn仍为按钮节点(绑定空回调onClickUnReachBtn不可点)而非纯文本，与'显示为未达成文本(非按钮)'字面仍有差距，视觉呈现需对照UI稿确认。", "部分通过"),
"TC-071": ("通过(代码层)｜回归确认：可购买档位(达成+未购买)显示BuyBtn+消耗数量(icon+CostNum，不足置红)；未达成档位仅显示未达成态(P2-14已修)，状态区分正确。", "通过"),
"TC-072": ("不通过(P2-15需确认)｜购买与领取为两步：BuyBtn点击仅扣仙玉推进buy_index(服务端C2gsWarorderBuyCost只扣费不发奖)，档位随后出现'领取'按钮(GetBtn)需再点击才发奖弹窗；与'购买即领取一步完成'预期不符，建议与策划确认交互。", "不通过"),
"TC-073": ("通过(代码层)｜消耗不足时CostNum置红(#e34e4e)；点击购买服务端校验不足返回COST_NOT_ENOUGHT，不扣费不发奖；飘字文案需真机确认。", "通过"),
"TC-074": ("通过(代码层)｜isCanCost按数量精确判断：刚好足够可购买、差1置红并提示；边界值建议真机复核。", "通过"),
"TC-075": ("通过(代码层)｜服务端主线通关事件→RecalcScore→score变化即SceneReady→SyncWarOrderUpdate实时推送gs2c_warorder_info(PackForClient含最新score)；客户端WarOrderMgr.onData更新数据后emit MSG_ON_WARORDER_GET_REWARD，消耗详情监听该消息全量refresh：CurTxt进度实时更新、refreshRewardList重建档位(未达成→购买实时刷新)，停留界面即生效无需重进。消耗banner(UIWarOrderCostUnit)本身无进度显示项，其充值按钮停留界面时不刷新(仅刷红点)，但重进界面可刷新：重开UIWarOrderEntry→onHide清空列表→onShow→refreshContent→ScrollViewWidget.refreshData(_clearUis后重建)→banner onShow重读is_recharge刷新按钮/金额/奖励。", "通过"),
"TC-076": ("部分通过｜红点正常(bStatus)；'总消耗价格'实际显示'当前可负担档位前缀'合计(客户端getOneKeyBuyCost与服务端__GetBuyCost一致、遇不可负担档位截断)，非全部满足条件档位总价，语义偏差需确认。", "部分通过"),
"TC-077": ("通过(代码层)｜回归确认已修复，三级红点链路齐备：①banner红点(r|t|b)；②页签红点：UIWarOrderEntry.prefab Tog1/Tog2/Tog3挂RedPoint组件(id=1100/1615/1616)，WarOrderMgr.updateRedPoint按页签聚合fund状态enableRedPoint，RedPoint组件每秒轮询isShow刷新；③主入口红点(UIMainView_Middle.prefab红点id=1271)经cfg_red_point父子链(1100/1615/1616→parent 1271)自动传递点亮。需真机验证视觉。", "通过"),
"TC-078": ("部分通过｜回归更新：无可购档位(bStatus=false)时banner红点不亮、详情内一键购买按钮/总消耗价格均隐藏，符合；banner点击在全部领完(hasRecvAllReward)时飘字'奖励已全部领取，请等待下一期基金开启'已实现(此前缺失)；差异：①文案与'当前无奖励可领取'不一致；②无可购档位但未领完时点击进详情(详情内仍可领取，属合理交互)。口径需与策划确认。", "部分通过"),
"TC-079": ("部分通过｜一键购买(buy_index=0)一次请求批量购买'可负担连续前缀'档位、一次性总扣费；但①发奖需再领取(同TC-072)；②中途有档位买不起则只买到前缀(见TC-080)，'全部购买'仅在全部可负担时成立。", "部分通过"),
"TC-080": ("不通过(P0-3)｜与澄清6相反：仙玉不足以支付全部总价时，服务端__GetBuyCost按逐档可负担累积，买得起几档买几档(部分购买、部分扣费)，仅当下一档买不起才停止；不存在'全部不购买'的整体失败语义。", "不通过"),
"TC-081": ("部分通过｜档位级：已购档BuyBtn隐藏(isBuy)、Cost隐藏正确；但详情底部'一键领取'(OneKeyGetBtn)显示条件为!bStatus，全部购买完成后仍持续显示不隐藏，与处理7'领取完后隐藏'不符。", "部分通过"),
"TC-082": ("通过(代码层)｜已领取(setRewared)/可购买(BuyBtn)/未达成(UnReachBtn)三状态并存渲染逻辑完整(P2-14同显问题已修复，三态互斥)。", "通过"),
"TC-083": ("待确认问题3现状更新(回归)｜banner侧已按澄清1落实：充值按钮充值成功即时切换为'已解锁'(BtnAllreadyBuy)不可点；详情侧ChargeBtn仍为直接隐藏(无已解锁态)；详情'一键领取'(OneKeyGetBtn)显示条件!bStatus：已充值基金领取完随is_end关闭界面消失，未充值基金免费领完后仍持续显示。剩余差异待策划确认口径后可关闭。", "待确认"),
"TC-084": ("通过｜已领取档位isBuy=true后BuyBtn/Cost隐藏、显示已领取态；服务端buy_index+1递进校验(NEED_BUY_PRE)防重复购买，重复请求不重复扣费。", "通过"),
"TC-090": ("不通过(P1-5)｜配置与服务端均未共用任务方案：6个任务类基金task_period分别为2/3/4/5/6/7(cfg_warorder_open.json)，各自独立CCycleWarOrder实例、独立任务列表与经验(cycle_war_order.lua)，与'共用同一套任务、经验互通'不符。", "不通过"),
"TC-091": ("不通过(P1-7)｜任务类基金详情点击banner打开UICommWarOrder，保留奖励/任务页签与任务面板(Tog2+Task)，任务按钮未移除。", "不通过"),
"TC-092": ("不通过(P1-6)｜任务页签无独立任务按钮：UIWarOrderEntry.prefab无任务按钮节点、代码无绑定；统一任务列表未实现(现任务列表仍按单基金在详情内UIWarOrderTasks展示)。", "不通过"),
"TC-093": ("不通过(P1-5)｜领任务奖励仅增加当前基金自身经验(__RecvOneTaskReward只加self.m_Exp)，不会统一增加页签内所有已开启基金经验。", "不通过"),
"TC-094": ("通过(语义偏差)｜未开启基金经验不变成立；但因任务经验本身不互通(P1-5)，'已开启基金统一加经验'同样不成立，该条仅字面通过。", "部分通过"),
"TC-095": ("不通过(P1-11未修)｜回归更新：任务可领时banner红点仍点亮(UIWarOrderUnit红点=rStatus||tStatus，任务基金tStatus生效)，与'banner不显示红点'相反；页签红点(1616)与主入口红点(1271)已实现(P1-8已修)，但预期中的'右上角任务按钮'不存在(P1-6)。", "不通过"),
"TC-096": ("部分通过｜回归更新：提交任务后gs2c_warorder_task_update→updateRedPoint重算，banner红点消失、页签红点(1616)消失、主入口红点(1271)同步消失，已实现；'任务按钮'红点因独立任务按钮未实现(P1-6)不适用。", "部分通过"),
"TC-097": ("任务列表沿用UIWarOrderTasks面板(第三页签模板TaskTpl)，布局需对照原版UI手测；注意当前任务列表按单基金展示而非统一列表(P1-6)。", "手测确认"),
"TC-098": ("通过(代码层)｜回归更新：升级出新奖励→服务端推送→updateRedPoint重算，banner红点(rStatus)、页签红点(1100)、主入口红点(1271)正常出现，三级齐备。", "通过"),
"TC-100": ("通过｜基金存在可领取奖励(免费或解锁)时hasRecvReward=true，banner红点显示。", "通过"),
"TC-101": ("通过(代码层)｜回归确认已修复：页签红点已实现，Tog1/Tog2/Tog3挂RedPoint组件(id 1100/1615/1616)，updateRedPoint按页签聚合点亮/熄灭。", "通过"),
"TC-102": ("通过｜主入口红点(UIMainView_Middle红点组件id=1271)由页签红点(1100/1615/1616)经cfg_red_point父子链传递点亮，任意基金可领取时点亮，关闭界面后仍显示。", "通过"),
"TC-103": ("通过(代码层)｜回归确认：领取全部可领奖励后updateRedPoint重算，banner红点、页签红点、主入口红点三级全部熄灭(1271经父子链随页签熄灭)，三级红点已齐备。", "通过"),
"TC-104": ("部分通过｜回归更新：is_end判定已修正，已充值消耗基金及基础基金免费+付费全部领完→服务端返回is_end→客户端删除fund并emit MSG_ON_WARORDER_CLOSED→banner随refreshView移除，符合；未充值消耗基金因付费奖励无法领取(recharge_recv_index恒0)永不触发is_end，免费领完后banner仍保留(点击进详情)，该场景与'全部领完banner隐藏'不符。", "部分通过"),
"TC-105": ("通过(代码层)｜回归确认P0-4已消除：cost基金period1仅FinishPeriod(免费+付费索引均满)才返回is_end，未领完任一次领取均返回false，不再出现'未领完banner被误删'；基础基金__StartNextPeriod推进期数逻辑正常。需真机复核。", "通过"),
"TC-106": ("通过(代码层)｜回归更新：存在满足条件未购买档位时banner红点(bStatus)、页签红点(1615)、主入口红点(1271)三级均点亮。", "通过"),
"TC-110": ("断网充值：客户端Network超时与SDK取消路径无状态写入代码，服务端以回调为准；需真机断网验证提示与状态。", "手测确认"),
"TC-111": ("通过(代码层)｜幂等完备：普通基金商品重复回调被WAR_ORDER_HAS_BUY拦截；550001被buyMap永久标记HAD_BUY；发奖与充值回调解耦(走recv_reward/buy_cost协议)，重复回调不重复解锁或发奖。", "通过"),
"TC-112": ("部分通过｜客户端购买/领取按钮无防连点置灰，连点会重复发协议；服务端幂等兜底(buy_cost要求buy_index+1递进NEED_BUY_PRE拦截；recv按free_recv_index推进不重复发奖)，不会重复扣费/发奖，但会有无效请求与错误提示，体验需真机确认。", "部分通过"),
"TC-113": ("通过(代码层)｜服务端全量持久化(SetDirty/Save)，重登SceneReady重新同步全部战令数据，状态以服务端为准；需真机复核表现。", "通过"),
"TC-114": ("阻塞(手测)｜集成流程受P0-1阻塞：新账号免费领完升级1/进阶1后消耗页签无法开启，步骤③起场景当前版本不可达；修复P0后需完整真机回归。", "阻塞"),
}

# ================= Sheet2 连点及奖励数量校验（按行序） =================
S2 = [
("部分通过(代码层)｜服务端幂等(recv按free_recv_index推进，重复请求返回NO_REWARD)不会重复领取；客户端按钮无点击后置灰/loading，防重全靠服务端。", "部分通过"),
("通过(代码层)｜弱网重复请求均被服务端幂等拦截，无重复发奖；第二次返回失败不会重复弹窗；需真机弱网复测。", "通过"),
("通过(代码层)｜已领取后GetBtn隐藏(isLGet)UI层不可点；协议直调被服务端拒绝，无重复领取记录。", "通过"),
("通过(代码层)｜失败时ok=false无发奖无状态变更，可重试不崩溃；提示文案依赖通用错误飘字需真机确认。", "通过"),
("通过(代码层)｜发奖/扣费均服务端持久化且有流水(RewardMap/DeductMap带reason)，静态无重复发放逻辑；DB一致性建议实测。", "通过"),
("通过｜页签切换纯本地同步刷新，onClickToggleList有curTabIndex防重入，无卡死/白屏风险点。", "通过"),
("通过(静态)｜页签内容同步刷新无异步加载，无数据串页风险；弱网表现建议真机复测。", "通过"),
("通过(静态)｜页签切换不发送网络请求，无冗余重复请求问题。", "通过"),
("通过(静态)｜定时器onHide统一清理(UIWarOrderUnit.timerHandler等)，无连点泄漏点；内存/卡顿需真机长测。", "通过"),
("部分通过(需真机)｜组合操作依赖服务端幂等兜底，客户端无互斥；功能正确性需真机验证。", "部分通过"),
("通过(代码层)｜发奖数量来自配置(CfgAwardListToRewardMap)，单领N1-N0=配置数量；具体数值需真机核对。", "通过"),
("通过(代码层)｜一键领取服务端RewardMap汇总全部待领奖励，每种道具增加量=配置之和；数值需真机核对。", "通过"),
("通过(代码层)｜弹窗/飘字展示数量与实际发放同源(同一配置)，一致；表现需真机确认。", "通过"),
("通过(代码层)｜多类型奖励同源配置逐项发放，经验/等级同步逻辑存在(__StartLevelUp)；需真机核对。", "通过"),
("手测确认｜非叠加道具走统一物品发放逻辑，背包分类与属性需真机验证。", "手测确认"),
("通过(代码层)｜连点由服务端幂等兜底仅发放一次，N1=N0+配置数量；客户端无防抖，体验需真机确认。", "通过"),
("通过(代码层)｜一键领取只处理free_recv_index之后的未领项，已领取项不会重复发放。", "通过"),
("手测确认｜数量上限/溢出为通用物品系统逻辑，需构造边界场景实测。", "手测确认"),
("通过(代码层)｜服务端持久化，重登以服务端数据为准，无中间态脏数据；需真机断线复测。", "通过"),
("手测确认｜前后端数量一致性需真机对比接口返回与客户端展示。", "手测确认"),
("手测确认｜数量0/极大值为配置边界，需构造配置实测。", "手测确认"),
]

# ================= Sheet3 待确认内容 =================
S3 = [
"代码走查结论：消耗类基金'充值解锁(付费)'与'仙玉购买档位(免费资格)'相互独立——未充值时档位可用仙玉购买(buy_index推进)，购买后可领该档免费奖励，付费奖励置灰；充值(is_recharge)后可补领所有已购档位的付费奖励(__GetLastExpReward从头遍历、已购且recharge_recv_index<index即补发)。注意：受P0-1影响，未充值玩家当前根本到不了消耗页签(2~5不开启)，该场景需修复P0后才会出现。",
"代码走查结论：两种红点未区分——任务可领(tStatus)与奖励可领(rStatus)都会点亮banner红点(UIWarOrderUnit红点=rStatus||tStatus)，页签层无红点。当前表现为'任务可领时banner亮红点'，与需求'banner无红点'冲突(缺陷P1-11)。",
"代码走查结论(回归更新)：充值解锁后banner按钮即时切换为'已解锁'(BtnAllreadyBuy)不可点，与澄清1一致(P1-9已修)；详情页ChargeBtn仍直接隐藏(无已解锁态)；'一键领取'(OneKeyGetBtn)显示条件为无未购档位(!bStatus)，已充值基金领取完随is_end关闭界面而消失，未充值基金免费领完后仍持续显示。剩余差异(详情已解锁态、未充值一键领取残留)待策划确认口径。",
]

wb = openpyxl.load_workbook(XLSX)
thin = Alignment(wrap_text=True, vertical='top')
hdr_fill = PatternFill('solid', fgColor='DDEBF7')
hdr_font = Font(bold=True)

# ---- 收集非通过用例原始内容（须在回填写入前读取，保留Sheet2源G列原文） ----
def _row_vals(ws, r, n):
    return [ws.cell(row=r, column=c).value for c in range(1, n + 1)]

nonpass_rows = []  # 统一列: 用例编号/所属模块/用例标题/优先级/前置条件/测试步骤/预期结果/关联需求/实际结果/是否通过/备注(空)
if ADD_NONPASS_SHEET:
    ws1_src = wb['基金特权入口合并测试用例']
    for r in range(2, ws1_src.max_row + 1):
        tc = str(ws1_src.cell(row=r, column=1).value or '').strip()
        if tc in S1 and S1[tc][1] != '通过':
            res, verdict = S1[tc]
            vals = _row_vals(ws1_src, r, 8)
            nonpass_rows.append(vals[:8] + [res, verdict, ''])
    ws2_src = wb['连点及奖励数量校验测试用例']
    for i in range(len(S2)):
        r = 2 + i
        res, verdict = S2[i]
        if verdict != '通过':
            v = _row_vals(ws2_src, r, 8)  # 源列: 模块/编号/名称/优先级/前置/步骤/预期结果/是否通过
            nonpass_rows.append([v[1], v[0], v[2], v[3], v[4], v[5], v[6], '', res, verdict, ''])
    ws3_src = wb['待确认内容']
    for i in range(len(S3)):
        r = 2 + i
        v = _row_vals(ws3_src, r, 3)  # 源列: 序号/待确认内容/当前状态
        nonpass_rows.append([f'待确认-{v[0]}', '待确认内容', v[1], '', '', '', '', v[2], S3[i], '待确认', ''])

# ---- Sheet1 ----
ws = wb['基金特权入口合并测试用例']
ws.cell(row=1, column=9, value='实际结果(代码走查)')
ws.cell(row=1, column=10, value='是否通过')
ws.cell(row=1, column=9).fill = hdr_fill; ws.cell(row=1, column=9).font = hdr_font
ws.cell(row=1, column=10).fill = hdr_fill; ws.cell(row=1, column=10).font = hdr_font
filled1 = 0
for r in range(2, ws.max_row + 1):
    tc = ws.cell(row=r, column=1).value
    if tc and str(tc).strip() in S1:
        res, verdict = S1[str(tc).strip()]
        c9 = ws.cell(row=r, column=9, value=res); c9.alignment = thin
        c10 = ws.cell(row=r, column=10, value=verdict); c10.alignment = thin
        filled1 += 1
ws.column_dimensions['I'].width = 70
ws.column_dimensions['J'].width = 12

# ---- Sheet2 ----
ws2 = wb['连点及奖励数量校验测试用例']
filled2 = 0
for i, (res, verdict) in enumerate(S2):
    r = 2 + i
    c7 = ws2.cell(row=r, column=7, value=res); c7.alignment = thin
    c8 = ws2.cell(row=r, column=8, value=verdict); c8.alignment = thin
    filled2 += 1
ws2.column_dimensions['G'].width = 70
ws2.column_dimensions['H'].width = 12

# ---- Sheet3 ----
ws3 = wb['待确认内容']
ws3.cell(row=1, column=4, value='代码走查结论')
ws3.cell(row=1, column=4).fill = hdr_fill; ws3.cell(row=1, column=4).font = hdr_font
for i, res in enumerate(S3):
    r = 2 + i
    c4 = ws3.cell(row=r, column=4, value=res); c4.alignment = thin
ws3.column_dimensions['D'].width = 80

# ---- 非通过用例汇总sheet（除通过以外的所有用例内容 + 空备注列） ----
if ADD_NONPASS_SHEET:
    NP_SHEET = '非通过用例汇总'
    if NP_SHEET in wb.sheetnames:
        del wb[NP_SHEET]
    wsn = wb.create_sheet(NP_SHEET)
    np_headers = ['用例编号', '所属模块', '用例标题', '优先级', '前置条件', '测试步骤', '预期结果', '关联需求', '实际结果(代码走查)', '是否通过', '备注']
    for c, h in enumerate(np_headers, start=1):
        cell = wsn.cell(row=1, column=c, value=h)
        cell.fill = hdr_fill; cell.font = hdr_font; cell.alignment = thin
    for i, row in enumerate(nonpass_rows):
        for c, v in enumerate(row, start=1):
            cell = wsn.cell(row=2 + i, column=c, value=v)
            cell.alignment = thin
    for col, w in zip('ABCDEFGHIJK', (12, 22, 30, 8, 18, 30, 40, 10, 70, 10, 20)):
        wsn.column_dimensions[col].width = w

OUT = r'E:\workproject\temp_case\cases\基金特权入口合并测试用例_已回填.xlsx'
try:
    wb.save(OUT)
except PermissionError:
    OUT = r'E:\workproject\temp_case\cases\基金特权入口合并测试用例_已回填_v2.xlsx'
    wb.save(OUT)
print(f'Saved to: {OUT}')
print(f'Sheet1 filled: {filled1}/83, Sheet2 filled: {filled2}/21, Sheet3 filled: {len(S3)}/3')
if ADD_NONPASS_SHEET:
    print(f'非通过用例汇总: {len(nonpass_rows)} rows')
