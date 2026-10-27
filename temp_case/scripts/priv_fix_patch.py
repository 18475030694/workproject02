# -*- coding: utf-8 -*-
"""priv_fix_patch.py: 给构建产物 game.js 打特权卡容错补丁（查不到的卡跳过+warn 出 card_id；备份可回滚）
可选参数（post_build_wechatgame.py 会带参调用；不带参时行为与原版完全一致）:
  --gamejs  目标 game.js 路径（默认 10-27 实战产物路径）
  --bak     备份输出路径（默认 10-27 实战备份路径）
"""
import argparse, io, os, shutil, sys, time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_ap = argparse.ArgumentParser()
_ap.add_argument("--gamejs", default=r"E:\p1-x\trunk\client\build\wechatgame\subpackages\scripts\game.js")
_ap.add_argument("--bak", default=r"e:\workproject\temp_case\reports\game.js.bak_privfix_20261027")
_args = _ap.parse_args()

GJS = _args.gamejs
BAK = _args.bak

PATCHES = [
    ("l=this.getCardCfg(s.card_id);if((-1==l.time_limit",
     'l=this.getCardCfg(s.card_id);if(!l){console.warn("[PRIV-FIX] getPrivilegeVal skip card_id="+s.card_id+" entry="+JSON.stringify(s));continue}if((-1==l.time_limit',
     "getPrivilegeVal 跳过未知卡"),
    ("this.cardInfoMap.forEach((function(r,a){var n=e.getCardCfg(a),o=!0;(n.sys_id&&n.sys_id>0",
     'this.cardInfoMap.forEach((function(r,a){var n=e.getCardCfg(a),o=!0;if(!n){console.warn("[PRIV-FIX] updateRedPoint skip card_id="+a);return}(n.sys_id&&n.sys_id>0',
     "updateRedPoint 跳过未知卡"),
    ("var t=this.getCardCfg(e),r=Math.floor(g.getServeTime());return-1==t.time_limit",
     "var t=this.getCardCfg(e);if(!t)return!1;var r=Math.floor(g.getServeTime());return-1==t.time_limit",
     "getPrivilegeCardStatus 跳过未知卡"),
]

with io.open(GJS, encoding="utf-8", newline="") as f:
    whole = f.read()

print("getCardCfg( 全文件调用次数:", whole.count("getCardCfg("))

for old, new, tag in PATCHES:
    c = whole.count(old)
    print("%-30s 唯一性命中=%d" % (tag, c))
    assert c == 1, "old 片段不唯一(%d)，中止不写盘" % c

if not os.path.exists(BAK):
    shutil.copy2(GJS, BAK)
    print("已备份 ->", BAK)
else:
    print("备份已存在(不覆盖):", BAK)

for old, new, tag in PATCHES:
    whole = whole.replace(old, new)
    print("已替换:", tag)

with io.open(GJS, "w", encoding="utf-8", newline="") as f:
    f.write(whole)

print("写回完成 size=%d mtime=%s" % (len(whole), time.strftime("%H:%M:%S")))
