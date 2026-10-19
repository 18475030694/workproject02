# -*- coding: utf-8 -*-
"""大圣礼包用例表同步：天数计算口径改为「自购买日起」。覆盖同名文件（遵循回填覆盖约定）。"""
import openpyxl

PATH = r'e:\workproject\temp_case\cases\大圣礼包调整测试用例.xlsx'

# (sheet名可选限定, 旧文本, 新文本) —— 对所有 sheet 全文扫描替换，旧文本足够唯一
REPLACES = [
    # 概览·需求口径
    ("天数由礼包开启（购买）时开始计算",
     "天数自购买日起开始计算（购买当天为第1天，锚点=购买日TodayNo，每日0点解锁下一天）"),
    # 概览·当前状态
    ("代码未更新；本表为执行版，部署后按表执行并回填（实际结果/测试结果/备注）",
     "代码已修改（fb_gift.lua：day_no改自购买日起算；老存档兼容锚点=第1天；占位数据隔离修复）；未部署S5，部署后按表执行并回填（实际结果/测试结果/备注）"),
    # TC-001 预期4
    ("4.天数从购买时开始计算",
     "4.天数自购买日起计算：购买当天=第1天，购买后立即可领第1天"),
    # TC-004 预期1
    ("1.0点后第2天奖励解锁可领取\n2.领取成功、数量正确",
     "1.0点后第2天奖励解锁可领取（第2天=购买日+1自然日，每天一档）\n2.领取成功、数量正确"),
    # TC-005 预期1
    ("1.0点后第3天奖励解锁可领取\n2.领取成功、数量正确",
     "1.0点后第3天奖励解锁可领取（第3天=购买日+2自然日，每天一档）\n2.领取成功、数量正确"),
    # TC-022 备注
    ("天数锚点（原购买时间 or 更新时间）待确认#4",
     "已确认：天数自购买日起计算；旧存档无购买时间，兼容口径=改版后首个0点全部解锁未领份额（视为窗口已过）"),
    # TC-E05 备注（占位拦截验证点）
    ("set_server_day 注意S5共享改→测→还原\n | 点3", None),
]

# 待确认#4：整行状态更新（按序号定位）
CONFIRM_ROW_4 = (
    "已确认（2026-10-15）：天数自购买日起开始计算。新购锚点=购买日TodayNo；旧存档无购买时间，兼容锚点=第1天（改版后首个0点全解锁未领份额）",
)

wb = openpyxl.load_workbook(PATH)
hit = 0
for old, new in REPLACES:
    if new is None:
        continue
    found = False
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                if isinstance(c.value, str) and old in c.value:
                    c.value = c.value.replace(old, new)
                    found = True
    print(('OK  ' if found else 'MISS'), old[:40].replace('\n', ' '))
    hit += 1 if found else 0

# TC-E05：按用例编号定位行，备注列追加占位拦截验证点
ws_e = wb['异常与边界用例']
header = [c.value for c in ws_e[1]]
idx_no = header.index('用例编号')
idx_note = header.index('备注')
for row in ws_e.iter_rows(min_row=2):
    if row[idx_no].value == 'TC-E05':
        note = row[idx_note].value or ''
        add = '；过期未购买的账号不出现领取入口，直发领取协议服务端拦截（NOT_BUY）'
        if add.lstrip('；') not in note:
            row[idx_note].value = note + add if note else add.lstrip('；')
        print('OK   TC-E05 备注:', row[idx_note].value)

ws = wb['待确认内容']
for row in ws.iter_rows():
    if row[0].value == 4:
        row[2].value = CONFIRM_ROW_4[0]
        print('OK   待确认#4 -> 已确认（天数自购买日起）')

import time
try:
    wb.save(PATH)
    print('saved:', PATH, 'replaced', hit, '/', len(REPLACES))
except PermissionError:
    print('file locked, wait 120s and retry...')
    time.sleep(120)
    try:
        wb.save(PATH)
        print('saved:', PATH, 'replaced', hit, '/', len(REPLACES))
    except PermissionError:
        alt = PATH.replace('.xlsx', '_天数锚点版.xlsx')
        wb.save(alt)
        print('still locked; saved as new file:', alt)
