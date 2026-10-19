# -*- coding: utf-8 -*-
"""旧秘宝 UI 基线比对（只读）：trunk vs tag(基准) vs tag_new 的 md5 + 图片目录清单"""
import hashlib
import io
import os
import sys
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOTS = {"trunk": r"E:\p1-x\trunk", "tag_new(上tag)": r"E:\p1-x\tag_new", "tag(基准)": r"E:\p1-x\tag"}

FILES = [
    r"client\assets\scripts\ui\treasurebox\UITreasureBox.ts",
    r"client\assets\scripts\ui\treasurebox\UITreasureBoxRewards.ts",
    r"client\assets\scripts\ui\treasurebox\UITreasureBoxTabView.ts",
    r"client\assets\resources\ui\prefab\treasurebox\UITreasureBox.prefab",
    r"client\assets\resources\ui\prefab\treasurebox\UITreasureBoxRewards.prefab",
    r"client\assets\scripts\logic\treasurebox\TreasureBoxMgr.ts",
    r"server\src\res\Config\box\cfg_box_base.lua",
]

def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()

out = ["=== 旧秘宝基线比对 %s ===" % datetime.now().isoformat(timespec="seconds")]
for rel in FILES:
    row = []
    for name, root in ROOTS.items():
        p = os.path.join(root, rel)
        if os.path.isfile(p):
            row.append("%s=%s(%dB)" % (name, md5f(p)[:8], os.path.getsize(p)))
        else:
            row.append("%s=<无>" % name)
    same = "全部一致" if len({x.split("=")[1].split("(")[0] for x in row if "<无>" not in x}) == 1 else "有差异"
    out.append("%-56s [%s] %s" % (os.path.basename(rel), same, " | ".join(row)))

# 美术字/图片目录
for name, root in ROOTS.items():
    d = os.path.join(root, r"client\assets\resources\ui\images\treasurebox")
    out.append("\n[%s] images/treasurebox (%s)" % (name, "存在" if os.path.isdir(d) else "不存在"))
    if os.path.isdir(d):
        names = sorted(f for f in os.listdir(d) if not f.endswith(".meta"))
        out.append("  共 %d 个文件: %s" % (len(names), ", ".join(names)))

# prefab 内引用的 spriteFrame / 图片名（旧 UI prefab）
import re
for name, root in ROOTS.items():
    p = os.path.join(root, r"client\assets\resources\ui\prefab\treasurebox\UITreasureBox.prefab")
    if not os.path.isfile(p):
        continue
    with open(p, "r", encoding="utf-8", errors="ignore") as f:
        t = f.read()
    sprites = sorted(set(re.findall(r'"__uuid__": "([0-9a-f]{8})', t)))
    out.append("\n[%s] UITreasureBox.prefab 引用uuid数=%d" % (name, len(sprites)))

dest = r"E:\workproject\temp_case\reports\ui_baseline_cmp.txt"
with open(dest, "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("written:", dest)
print("\n".join(out))
