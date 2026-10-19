# -*- coding: utf-8 -*-
"""检查图鉴详情dump中的label文本，判断运行时代码是否为最新版"""
import json, re, sys

d = json.load(open(r'E:\workproject\reports\e2e_fabao_20260908_170105\dump_atlas_desc.json', encoding='utf-8'))
s = json.dumps(d, ensure_ascii=False)

# 列出 UISoulRingAtlasDesc 子树内带 text 的节点
i = s.find('UISoulRingAtlasDesc')
sub = s[i:i+8000] if i >= 0 else s
pat = re.compile(r'\{"path": "([^"]+)", "name": "[^"]+", "active": (true|false)(?:, "text": "([^"]*)")?')
count = 0
for m in pat.finditer(sub):
    path, active, text = m.groups()
    if text is not None and text != '':
        print(active, path.split('/')[-2] + '/' + path.split('/')[-1], '=>', text[:60])
        count += 1
    if count > 25:
        break

print('=== 年/阶/灵力 in atlas_desc ===')
for kw in ['阶', '年', '灵力']:
    hits = re.findall(r'"text": "([^"]*' + kw + r'[^"]*)"', s)
    for h in set(hits):
        print(kw, '=>', h[:80])

# 图鉴 dump: 分类按钮文本
a = json.load(open(r'E:\workproject\reports\e2e_fabao_20260908_170105\dump_atlas.json', encoding='utf-8'))
sa = json.dumps(a, ensure_ascii=False)
togs = re.findall(r'"name": "TogTemp[^"]*"[^}]*?"text": "([^"]*)"', sa)
print('=== atlas TogTemp labels ===')
print(togs)
