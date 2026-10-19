# -*- coding: utf-8 -*-
"""仙机→秘宝 回退状态盘点（只读）：trunk/tag/tag_new 三方比对 + 残留词扫描"""
import hashlib
import io
import os
import sys
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOTS = {
    "trunk": r"E:\p1-x\trunk",
    "tag_new": r"E:\p1-x\tag_new",
    "tag": r"E:\p1-x\tag",
}
REL_CFG = r"server\src\res\Config\box\cfg_box_base.lua"
REL_UI = r"client\assets\scripts\ui\treasurebox"
REL_PF = r"client\assets\resources\ui\prefab\treasurebox"
RESIDUAL_WORDS = ["仙机", "老虎机", "laohujituan", "Laohujituan"]
SKIP_DIRS = {".svn", "library", "temp", "node_modules", "temp_case", ".git", "vendor", " previews"}
SCAN_EXT = {".lua", ".ts", ".prefab", ".json", ".txt", ".cs", ".js", ".md", ".xml", ".asset"}

out = []
def w(s=""):
    out.append(str(s))

def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

w("=== 回退状态盘点 %s ===" % datetime.now().isoformat(timespec="seconds"))

# 1) 目录身份
for name, root in ROOTS.items():
    w("\n[%s] %s exists=%s" % (name, root, os.path.isdir(root)))
    if not os.path.isdir(root):
        continue
    cfg = os.path.join(root, REL_CFG)
    w("  cfg_box_base.lua exists=%s" % os.path.isfile(cfg))
    if os.path.isfile(cfg):
        w("    md5=%s size=%d" % (md5(cfg), os.path.getsize(cfg)))
    for label, rel in [("ui_scripts", REL_UI), ("prefabs", REL_PF)]:
        d = os.path.join(root, rel)
        if os.path.isdir(d):
            names = sorted(os.listdir(d))
            w("  %s (%d): %s" % (label, len(names), ", ".join(names)))
        else:
            w("  %s: <目录不存在> %s" % (label, d))

# 2) cfg_box_base 三方 diff
def read_lines(root, rel):
    p = os.path.join(root, rel)
    if not os.path.isfile(p):
        return None
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        return f.readlines()

import difflib
base = read_lines(ROOTS["trunk"], REL_CFG)
for other in ("tag_new", "tag"):
    oth = read_lines(ROOTS[other], REL_CFG)
    w("\n--- diff trunk vs %s (cfg_box_base.lua) ---" % other)
    if base is None or oth is None:
        w("  <缺文件> base=%s other=%s" % (base is not None, oth is not None))
        continue
    dl = list(difflib.unified_diff(base, oth, lineterm=""))
    w("  变更行数=%d" % len([x for x in dl if x[:1] in "+-" and x[:3] not in ("+++", "---")]))
    w("".join(dl[:120]))

# 3) 残留词扫描（client/assets + server/src，跳过构建临时目录）
for name, root in ROOTS.items():
    if not os.path.isdir(root):
        continue
    w("\n=== 残留词扫描 [%s] ===" % name)
    hits = {}
    scanned = 0
    for sub in (r"client\assets", r"server\src"):
        base_dir = os.path.join(root, sub)
        if not os.path.isdir(base_dir):
            continue
        for dirpath, dirnames, filenames in os.walk(base_dir):
            dirnames[:] = [d for d in dirnames if d.lower() not in SKIP_DIRS]
            for fn in filenames:
                ext = os.path.splitext(fn)[1].lower()
                if ext not in SCAN_EXT:
                    continue
                p = os.path.join(dirpath, fn)
                try:
                    if os.path.getsize(p) > 8 << 20:
                        continue
                    with open(p, "r", encoding="utf-8", errors="ignore") as f:
                        txt = f.read()
                except OSError:
                    continue
                scanned += 1
                for wd in RESIDUAL_WORDS:
                    n = txt.count(wd)
                    if n:
                        key = wd
                        hits.setdefault(key, []).append((n, p))
    w("  扫描文件数=%d" % scanned)
    if not hits:
        w("  残留词：无")
    for wd, lst in sorted(hits.items()):
        total = sum(n for n, _ in lst)
        w("  [%s] 命中文件=%d 总次数=%d" % (wd, len(lst), total))
        for n, p in sorted(lst, key=lambda x: -x[0])[:15]:
            w("    %4d  %s" % (n, p))

# 4) trunk UITreasureBoxNew.ts 头部（是否仍是转轮实现）+ 入口引用
p_new = os.path.join(ROOTS["trunk"], REL_UI, "UITreasureBoxNew.ts")
if os.path.isfile(p_new):
    with open(p_new, "r", encoding="utf-8", errors="replace") as f:
        head = f.read(3000)
    w("\n=== trunk UITreasureBoxNew.ts 头部 3000 字 ===")
    w(head)
    with open(p_new, "r", encoding="utf-8", errors="replace") as f:
        full = f.read()
    for kw in ["SlotMachineBox", "isRolling", "resultArray", "slotMachine", "LaGan", "转轮", "老虎"]:
        w("  kw[%s]=%d" % (kw, full.count(kw)))

# 引用 UITreasureBoxNew 的代码（trunk client/assets/scripts）
refs = []
ui_dir = os.path.join(ROOTS["trunk"], r"client\assets\scripts")
for dirpath, dirnames, filenames in os.walk(ui_dir):
    dirnames[:] = [d for d in dirnames if d.lower() not in SKIP_DIRS]
    for fn in filenames:
        if not fn.endswith((".ts", ".js")):
            continue
        p = os.path.join(dirpath, fn)
        if os.path.abspath(p) == os.path.abspath(p_new):
            continue
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                t = f.read()
        except OSError:
            continue
        if "UITreasureBoxNew" in t:
            ln = [i + 1 for i, line in enumerate(t.splitlines()) if "UITreasureBoxNew" in line][:5]
            refs.append((p, ln))
w("\n=== trunk 中引用 UITreasureBoxNew 的文件（除自身）：%d ===" % len(refs))
for p, ln in refs[:20]:
    w("  %s lines=%s" % (p, ln))

dest = r"E:\workproject\temp_case\reports\rollback_state_probe.txt"
with open(dest, "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("written:", dest)
