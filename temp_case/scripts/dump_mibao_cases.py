# -*- coding: utf-8 -*-
"""dump 秘宝用例 xlsx 全部内容"""
import sys
import openpyxl

F = r"E:\workproject\temp_case\cases\新秘宝用例.xlsx"

wb = openpyxl.load_workbook(F, read_only=True, data_only=True)
for ws in wb.worksheets:
    print("#" * 30, "sheet:", ws.title, f"({ws.max_row}行 x {ws.max_column}列)")
    n = 0
    for row in ws.iter_rows():
        n += 1
        vals = []
        for c in row:
            v = c.value
            if v is None:
                continue
            s = str(v).replace("\n", "\\n")
            if len(s) > 200:
                s = s[:200] + f"...<{len(s)}字符>"
            if s.strip():
                vals.append(f"[{c.coordinate}]{s}")
        if vals:
            print(" | ".join(vals))
        if n > 200:
            print("...(截断)")
            break
wb.close()
