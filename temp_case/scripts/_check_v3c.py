# -*- coding: utf-8 -*-
"""v3x 片段静态校验：python 语法 + JS 花括号平衡（AST 取 JS_ 常量）。用法: python _check_v3c.py [脚本路径]"""
import ast
import sys

target = sys.argv[1] if len(sys.argv) > 1 else r"E:\workproject\harness\e2e_fabao_v3d.py"
print("check:", target)
src = open(target, encoding="utf-8").read()
tree = ast.parse(src)
print("python syntax OK")
ns = {}
for node in tree.body:
    if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id.startswith("JS_"):
        seg = ast.get_source_segment(src, node)
        try:
            exec(compile(seg, "<js>", "exec"), ns)
        except Exception as e:  # noqa: BLE001
            print(node.targets[0].id, "EXEC FAIL:", e)
ok = True
for k, v in ns.items():
    if k.startswith("JS_") and isinstance(v, str):
        d = 0
        instr = None
        esc = False
        for ch in v:
            if instr:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == instr:
                    instr = None
            else:
                if ch in ('"', "'", "`"):
                    instr = ch
                elif ch == "{":
                    d += 1
                elif ch == "}":
                    d -= 1
        if d != 0:
            ok = False
        print(k, "balance", d)
print("JS count:", len([k for k in ns if k.startswith("JS_")]))
print("ALL OK" if ok else "BALANCE ERROR")
