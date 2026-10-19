# -*- coding: utf-8 -*-
"""工具/环境一致性诊断（只读）：
1) e:/ 根目录条目按 Unicode 码点打印（识别同形异码/大小写变体）
2) 对 workproject / p1-x 的多种拼写变体探测 realpath + 关键文件 md5 一致性
3) 同一逻辑文件在不同拼写下的 md5 对比 -> 判定是否多棵目录树
"""
import hashlib
import io
import os
import sys
import unicodedata

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

def cp(name):
    return "+".join("U+%04X" % ord(c) for c in name)

def md5f(p):
    h = hashlib.md5()
    try:
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError as e:
        return "ERR:%s" % e.errno

out = []
out.append("=== 环境一致性诊断 ===")

# 1) 盘符根
for drive in ("e:", "e:"):
    try:
        names = sorted(os.listdir(drive + "/"))
        out.append("\n[%s/] 共 %d 项" % (drive, len(names)))
        for n in names:
            low = n.lower()
            if any(k in low for k in ("work", "p1", "p1", "project")):
                out.append("  %r  cp=%s" % (n, cp(n)))
    except OSError as e:
        out.append("[%s/] ERR %s" % (drive, e))

# 2) 候选拼写变体（覆盖本会话出现过的所有拼写）
variants = [
    "e:/workproject", "e:/workproject", "e:/workproject", "e:/workproject",
    "e:/p1-x", "e:/p1-x", "e:/p1-x",
]
seen = {}
out.append("\n=== 拼写变体探测 ===")
for v in variants:
    try:
        real = os.path.realpath(v)
        isdir = os.path.isdir(v)
    except OSError as e:
        real, isdir = "ERR:%s" % e, False
    out.append("%-28s isdir=%s realpath=%s" % (repr(v), isdir, real))
    if isdir:
        seen.setdefault(real, []).append(v)

# 3) 关键文件 md5 一致性（同一逻辑文件，多拼写）
out.append("\n=== 关键文件 md5（按拼写） ===")
probe_files = [
    ("temp_case/reports/rollback_state_probe.txt", "workproject"),
    ("temp_case/reports/svn_audit.txt", "workproject"),
    ("temp_case/scripts/rollback_state_probe.py", "workproject"),
    ("temp_case/scripts/svn_audit.py", "workproject"),
    ("temp_case/scripts/env_probe.py", "workproject"),
]
for rel, base_kind in probe_files:
    row = []
    for v in ("e:/workproject", "e:/workproject", "e:/workproject"):
        p = os.path.join(v, rel)
        if os.path.isfile(p):
            row.append("%s=%s(%dB)" % (v, md5f(p)[:10], os.path.getsize(p)))
        else:
            row.append("%s=<缺>" % v)
    out.append("%-46s %s" % (rel, " | ".join(row)))

for rel in ("trunk/server/src/res/Config/box/cfg_box_base.lua",
            "trunk/client/assets/scripts/ui/treasurebox/UITreasureBoxNew.ts"):
    row = []
    for v in ("e:/p1-x", "e:/p1-x", "e:/p1-x"):
        p = os.path.join(v, rel)
        if os.path.isfile(p):
            row.append("%s=%s(%dB)" % (v, md5f(p)[:10], os.path.getsize(p)))
        else:
            row.append("%s=<缺>" % v)
    out.append("%-46s %s" % (rel, " | ".join(row)))

# 4) scripts 目录实际内容（码点级）
out.append("\n=== scripts 目录实际内容 ===")
for v in ("e:/workproject", "e:/workproject"):
    d = os.path.join(v, "temp_case", "scripts")
    if os.path.isdir(d):
        out.append("[%s]" % d)
        for n in sorted(os.listdir(d)):
            out.append("   %r" % n)

out.append("\n=== NFC/NFD 归一化检查 ===")
for v in ("e:/workproject", "e:/workproject", "e:/p1-x"):
    nfc = unicodedata.normalize("NFC", v)
    out.append("%s NFC相同=%s" % (repr(v), nfc == v))

dest = r"E:\workproject\temp_case\reports\env_diag.txt"
with open(dest, "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("written:", dest)
print("\n".join(out))
