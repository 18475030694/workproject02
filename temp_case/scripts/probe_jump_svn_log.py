# -*- coding: utf-8 -*-
"""临时探针2：URL方式查xlsx日志 + cfg_item_source 29/43引入时间（只读）"""
import sys, io, subprocess, json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
SVN = r'E:\workproject\harness\vendor\svn\app\PFiles\bin\svn.exe'
TRUNK = r'E:\p1-x\trunk'
from urllib.parse import quote

def svn_out(args, cwd=TRUNK):
    cmd = [SVN] + args + ['--non-interactive', '--no-auth-cache']
    r = subprocess.run(cmd, capture_output=True, cwd=cwd)
    if r.returncode:
        raise RuntimeError(r.stderr.decode('utf-8', errors='replace')[:400])
    return r.stdout.decode('utf-8', errors='replace')

print('==== X-系统开启.xlsx 日志 ====')
xurl = 'http://svn.******.com/p1-x/trunk/' + quote('export/X-系统开启.xlsx')
print(svn_out(['log', '-l', '6', xurl]))
print('==== W-物品来源配置.xlsx 日志 ====')
wurl = 'http://svn.******.com/p1-x/trunk/' + quote('export/W-物品来源配置.xlsx')
print(svn_out(['log', '-l', '6', wurl]))

print('==== cfg_item_source.json 历史命中 ====')
jurl = 'http://svn.******.com/p1-x/trunk/client/assets/resources/cfg/item/cfg_item_source.json'
for rev in ['10603', '10602', '10600', '10590', '10580']:
    out = svn_out(['cat', '-r', rev, jurl])
    data = json.loads(out)
    hits = []
    for iid, sources in data.items():
        for k, e in sources.items():
            if isinstance(e, dict) and e.get('goWin') in (29, 43, 46, 181, 182):
                hits.append((iid, e.get('title'), e['goWin']))
    print('r%s: 命中%s条 %s' % (rev, len(hits), hits[:8]))
