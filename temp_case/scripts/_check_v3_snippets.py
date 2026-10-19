# -*- coding: utf-8 -*-
"""校验 e2e_fabao_v3.py 中 JS 片段的开头与括号平衡"""
import sys
sys.path.insert(0, r'E:\workproject\harness')
import e2e_fabao_v3 as m


def balance(v):
    depth = 0
    instr = None
    esc = False
    i = 0
    while i < len(v):
        ch = v[i]
        if instr:
            if esc:
                esc = False
            elif ch == '\\':
                esc = True
            elif ch == instr:
                instr = None
        else:
            if ch in ('"', "'", '`'):
                instr = ch
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
        i += 1
    return depth


for name in sorted(dir(m)):
    if name.startswith('JS_'):
        v = getattr(m, name)
        s = v.strip().replace('\n', ' ')
        b = balance(v)
        flag = '  <-- UNBALANCED' if b != 0 else ''
        print(f'{name}: start[{s[:46]}] len={len(v)} balance={b}{flag}')
