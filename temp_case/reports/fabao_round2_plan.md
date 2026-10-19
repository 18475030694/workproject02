# 法宝第二轮测试——静态结论与运行时方案（2026-09-08 晚）

## 环境
- 预览: http://localhost:7456/?qa=1（已启动）; QA桥 window.__qa + 全局 cc + window.SystemModules 可用
- GM HTTP: http://192.168.*.*:6011/index/<cmd>?uuid=...（已确认可达）
  - set_mainline_stage(uuid, stage_id=40) 解锁法宝8/炼宝9
  - award_item(uuid, item_id, count) 发物品（法宝碎片 ring_chip_id 16001+，法宝 gift_id 6001+）
  - set_role_level(uuid, level) 设角色等级
  - query_account_uuid(account, platform) 查uuid
- Playwright 1.60 + chromium 已装好（用 D:\python\python3.9 的 python，需 dangerouslyDisableSandbox 跑 playwright install/浏览器启动）
- 复用 harness/e2e_login.py（wait_qa_bridge/force_select_server/screenshot）与 harness/e2e_fabao.py 的 qa/texts/wait_main_city/open_via_qa
- 账号快捷造号: localStorage TMP_ACCOUNT_=<新号> → reload → 点 LoginBtn_ → 进游戏后按 Escape → 再 reload 重登（用户口述快捷高级号法，需实验验证；兜底 GM set_mainline_stage+set_role_level）
- 硬约束: E:\p1-x 只读！造数据一律用运行时内存补丁（page.evaluate 改 SystemModules.ShareRes 或 cfg 对象）

## 代码今天3次更新: 12:04 / 17:38 / 18:41（开发者仍在改，预览chunk可能已含新代码）

## 配置关键数据（E:\p1-x\trunk\client\assets\resources\cfg\soul_ring\）
- cfg_soul_ring_base.json: 72条法宝, quality==ring_group 100%（造数需patch）; 字段 gift_id/name/level(初始阶)/quality/ring_group/ring_chip_id/icon/show_res/tab/attr_AttackBase/attr_DefenseBase/attr_MaxHpBase
- 最长法宝名 8 字符（[仙]九龙神火罩）
- cfg_soul_ring_quality.json: 10档品质(1凡..10仙) → bg/common_item02_wupinkuangXX、color、atlas_filter_res、skill_res、atlas_res、title_bg
- cfg_soul_ring_misc.json: atlas_red_god_show_cond=11
- cfg_skill_level.json（R1关键）: 各层颜色 40阶=#519f3e(绿) 60阶=#4c8dbe(蓝) 80阶=#9875b3(紫) 100阶=#c3a04c(黄) 150阶=#de645d(红) 250阶=#ff73f7(粉) ← 非统一绿

## SoulRingMgr 语义（logic/soulring/SoulRingMgr.ts）
- getInitialLevel(gift_id)=conf.level 初始阶; getCurLevel=ringMap有无?ring_level:初始
- calcAddLv(ringInfo): buddy_id(已穿戴) && isAdapterSkill(ring_id,skill_id) 时=特性eff(如+30阶"适配")，否则0
- calcRingFinalLV = ring_level + calcAddLv（最终阶=真实+适配）
- calcRingYear = cfg_soul_ring_upgrade[group][ring_level].year（无加成）
- ringMap 由 gs2c_soul_ring_sync 服务器下发

## 六条新需求静态结论（法宝问题.xlsx，截图在 temp_case/reports/fb_issue_imgs/）
- R1 技能激活不同层级统一绿颜色: **未实现**。UIRingUnlockSkill.ts L96 `【${data.name}】` 用 cfg_skill_level[].color（多层异色，见上）
- R2 仙品法宝/图鉴前期隐藏(11级奖池或开服16天可见可点): **部分实现**。UISoulRingAtlas.ts L48-52 未达标点仙品tab→提示"炼宝等级达到11级可查阅"且toggle还原；L63-72 过滤内容；但①tab未"直接隐藏"仍可见 ②仅判 pool_level>=11，无"开服16天"或条件
- R3 公告滚屏调整(前4天:神8/圣9/仙10; 5~18天:圣/仙; 19+天:仙; 字体按品质变色): **未实现**。服务器 mod_soul_ring.lua L1064-1078 固定 ring_group>=6 触发 BigSoulRing，无开服天数过滤；cfg_bulletin_msg.lua L32-33 模板固定样式非按品质变色；客户端 BulletinMgr processBulletinMsg 固定黄色#fffedb
- R4 图鉴按当前真实阶数+战力属性按真实阶(升阶加成要加/适配不加): **部分实现**。图鉴列表 RingAtlasItem.ts L72 calcRingFinalLV(data.gift_id)传数字→返回初始阶（列表显示初始阶，错）；图鉴详情 UISoulRingAtlasDesc.ts L46/49 用 calcRingFinalLV（含适配，错，截图139阶应为109）；属性 L90 用 getCurLevel（真实阶，对）。即阶数显示两端都不对、属性对
- R5 适配加成能激活特性: **部分实现**。装配面板 UIHeroSoulRing.ts L560-561 与列表项 UIHeroSoulItem.ts L168-169 用 calcRingFinalLV（含适配，对）；UISoulRingDesc.ts L132-133 与 UISoulRingAtlasDesc.ts L66-67 用 ring_level 真实阶（不含适配，错）
- R6 查看法宝属性按最终阶(适配属性+特性解锁也加上): **部分实现**。已装配详情面板 UIHeroSoulRing.ts L537 addition 用 rindLevel+addRindLevel（最终阶，对，截图+9612）；列表项 UIHeroSoulItem.ts L102 只用 lv 真实阶（错）；UISoulRingDesc.ts L157 真实阶（错）；图鉴详情 L90 真实阶（R4要求如此，符）

## TC007-009 外观解耦: 未实现（外观按quality）
- UISoulRing.ts L51-54/59/83-92: Bg/名称色/框特效全按 cfg_soul_ring_base[ring].quality → cfg_soul_ring_quality[quality]
- 造数方案（运行时补丁，不改文件）: page.evaluate 改 ShareRes.cfg_soul_ring_base[6001].quality（如 1→7）→ 重新打开图鉴/列表 → 读节点 Sprite.spriteFrame.name（bg）+ 名称颜色对比
  - TC009 改quality外观应变但若解耦正确应不变 → 预期复现缺陷: 外观跟随quality变化=FAIL证据
  - TC007 同quality(1)不同group(1 vs 2): patch 6002.ring_group=9 保持quality=1 → 外观相同=FAIL
  - TC008 同group不同quality: patch 6003.quality=7 group=3 vs 6001 quality=1 group=1后…（注意先备份原值，测完恢复再reload）
- 取证: atlas_res 道具框 spriteFrame.name、名称 Label.color、UIRing 光球

## TC042 属性一致性（等待+慢速+与配置对比）
- 流程: 登录(1351/1353已有数据或award_item造) → GM解锁 → 打开 UIHeroSoulRing → 选中英雄与技能槽 → 等待≥2s → 读装配面板 AttrTempEquip1-3 的 AttrlVal label 值 → 公式: base(attr_AttackBase等) × cfg_soul_ring_upgrade[group][ring_level+addLv].addtion/10000 → 对比（<10万floor，≥10万保留2位小数, formatNum千分位）
- 角色面板: 打开英雄属性界面对比 SOUL_RING 系统加成（playerMgr.getSysAttr(SysIdEnum.SOUL_RING)）
- 慢速: 每步 wait_for_timeout(1500~2500) 防异步加载未完成

## TC043 布局（长名/大数值）
- patch 某法宝 name='[极]超长名称测试一二三四五'（>8字）→ 打开装备列表 → 检查 NameR_txt 与 SoulRing 图标 boundingBox 是否相交（UITransform worldSpace）+ 截图人工复核 → 恢复
- UIHeroSoulItem 布局: 名称 NameR_txt 在列表项，图标 SoulRing；代码无 overflow 约束处理

## 战斗技能表现回归
- GM set_mainline_stage → 进主线战斗（UIBattle?）→ 截图 + console错误收集 + dumpUITree 找法宝技能文案（如"法宝阶数加成"伤害）
- 属性面板: playerMgr.getSysAttr(SOUL_RING) 应含装备法宝加成

## 产物
- 更新 temp_case/cases/法宝UI优化测试用例_trae.xlsx（TC007-009/042/043+新增需求映射行）
- 更新 temp_case/reports/法宝UI优化测试报告_trae.md（第二轮章节: R1-R6结论+运行时证据）
- 报告目录 reports/e2e_fabao_v3_<ts>/
