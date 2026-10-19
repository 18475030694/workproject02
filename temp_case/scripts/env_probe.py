# -*- coding: utf-8 -*-
"""运行环境可达性探测（只读）：预览 7456 / GM 6011 / 账号可用性线索"""
import io
import json
import sys
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

def probe(url, timeout=6):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "qa-probe"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read(400)
            return {"ok": True, "status": r.status, "head": body.decode("utf-8", "ignore")[:200]}
    except Exception as e:
        return {"ok": False, "err": "%s: %s" % (type(e).__name__, e)}

out = []
out.append("=== 运行环境探测 %s ===" % __import__("datetime").datetime.now().isoformat(timespec="seconds"))
for name, url in [
    ("preview_root", "http://localhost:7456/"),
    ("preview_scene", "http://localhost:7456/?debug=1"),
    ("gm_index", "http://192.168.*.*:6011/index"),
    ("gm_root", "http://192.168.*.*:6011/"),
]:
    r = probe(url)
    out.append("[%s] %s -> %s" % (name, url, r))
    if r["ok"]:
        out.append("    body_head: %r" % r["head"][:160])

# GM 可用接口嗅探（常见只读查询）
for path in ["/role_info?uuid=4451", "/get_role?uuid=4451", "/query_role?uuid=4451"]:
    r = probe("http://192.168.*.*:6011" + path, timeout=5)
    out.append("[gm%s] %s" % (path, r))

dest = r"E:\workproject\temp_case\reports\env_probe.txt"
with open(dest, "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("written:", dest)
print("\n".join(out))
