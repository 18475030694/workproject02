# -*- coding: utf-8 -*-
"""svn 权威对账（只读）：tags 清单 + trunk 近 40 条提交的变更文件清单"""
import io
import json
import os
import subprocess
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

EXE = r"e:\workproject\harness\vendor\svn\app\PFiles\bin\svn.exe"
AUTH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "harness", "loc_check", "svn_auth.local.json")
AUTH2 = r"e:\workproject\harness\loc_check\svn_auth.local.json"
auth_path = AUTH2 if os.path.isfile(AUTH2) else AUTH
with open(auth_path, "r", encoding="utf-8") as f:
    a = json.load(f)

def run(args, timeout=600):
    cmd = [EXE] + args + ["--username", a["username"], "--password", a["password"],
                          "--non-interactive", "--no-auth-cache"]
    r = subprocess.run(cmd, capture_output=True, timeout=timeout)
    out = r.stdout.decode("gbk", errors="replace")
    err = r.stderr.decode("gbk", errors="replace")
    return out, err, r.returncode

lines = []
out, err, rc = run(["ls", "http://svn.******.com/p1-x/tags/"])
lines.append("=== tags 目录 === rc=%d" % rc)
lines.append(out if out else err)

out, err, rc = run(["log", "-v", "-l", "40", "http://svn.******.com/p1-x/trunk"])
lines.append("=== trunk 最近40条提交(带变更文件) rc=%d ===" % rc)
lines.append(out if out else err)

dest = r"E:\workproject\temp_case\reports\svn_audit.txt"
with open(dest, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("written:", dest, "log_lines=", len("\n".join(lines).splitlines()))
