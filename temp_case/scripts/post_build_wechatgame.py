# -*- coding: utf-8 -*-
"""post_build_wechatgame.py: p1-x 微信小游戏一键构建后处理（幂等，可反复跑）

把《全流程指南》§4 的手工四步 + 校验收敛成一个脚本：
  [1] res_version 拷贝      remote/res_version.json -> remote/res_version.0.json
  [2] Version.ts 还原       构建必写脏占位符，改回 "BUILD_VERSION"（否则网页预览解密失败登录卡死）
  [3] multTextures 远程改造  分包版 -> remote bundle（绕开 DevTools 分包 create time_limit 战斗崩溃）
  [4] 特权卡容错补丁         调 priv_fix_patch.py（cfg 快照缺新卡时战斗崩，补丁查不到的卡 warn 后跳过）
  [5] 终检                  逐项断言上面所有步骤 + meta 基线 + 根 game.js 调试钩子提示

用法（本机 Python D:\\python\\python3.9\\python.exe）:
  常规（构建后跑一次）:
    python post_build_wechatgame.py
  只巡检不写盘（幂等自检，退出码 0=全过 1=有缺项）:
    python post_build_wechatgame.py --check
  连 Cocos CLI 构建一起跑（真一键，约 6 分钟，中途不要杀）:
    python post_build_wechatgame.py --cocos "CocosCreator.exe完整路径"
  测试/演练（指向模拟目录，不碰真产物）:
    python post_build_wechatgame.py --build-dir <模拟build目录> --client-root <模拟client目录>

注意：写 E:\\p1-x 需禁沙箱/授权；所有写盘动作先把原件备份到
  e:\\workproject\\temp_case\\reports\\post_build_bak\\<时间戳>\\
"""
import argparse, glob, io, json, os, re, shutil, subprocess, sys, time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
PRIV_FIX = os.path.join(HERE, "priv_fix_patch.py")
REPORTS = r"e:\workproject\temp_case\reports"

_ap = argparse.ArgumentParser(description="p1-x 微信小游戏一键构建后处理")
_ap.add_argument("--build-dir", default=r"E:\p1-x\trunk\client\build\wechatgame")
_ap.add_argument("--client-root", default=None, help="默认取 build-dir 上两级（.../client）")
_ap.add_argument("--check", action="store_true", help="只校验不写盘")
_ap.add_argument("--skip-priv", action="store_true", help="跳过特权卡补丁步骤")
_ap.add_argument("--cocos", default=None, help="CocosCreator.exe 路径；提供则先执行 CLI 构建（约6min）")
_ap.add_argument("--config", default=os.path.join(REPORTS, "buildConfig-local-wechat.json"))
_args = _ap.parse_args()

BUILD = os.path.abspath(_args.build_dir)
CLIENT = os.path.abspath(_args.client_root) if _args.client_root else os.path.dirname(os.path.dirname(BUILD))
VERSION_TS = os.path.join(CLIENT, "assets", "scripts", "Version.ts")
META = os.path.join(CLIENT, "assets", "multTextures.meta")
BAK_DIR = os.path.join(REPORTS, "post_build_bak", time.strftime("%Y%m%d_%H%M%S"))

RESULTS = []  # (tag, status, msg)


def report(tag, status, msg=""):
    RESULTS.append((tag, status, msg))
    mark = {"OK": "[OK]  ", "SKIP": "[SKIP]", "FAIL": "[FAIL]", "WARN": "[WARN]", "INFO": "[INFO]"}[status]
    print("%s %-14s %s" % (mark, tag, msg), flush=True)


def read_text(p):
    # utf-8-sig 容错 BOM（手工生成的 JSON 可能带 BOM，Cocos 产物本身无 BOM）
    with io.open(p, encoding="utf-8-sig", newline="") as f:
        return f.read()


def write_text(p, s):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p, "w", encoding="utf-8", newline="") as f:
        f.write(s)


def backup(p):
    """写盘前备份原件（只备份一次）。"""
    if not os.path.exists(p):
        return None
    os.makedirs(BAK_DIR, exist_ok=True)
    dst = os.path.join(BAK_DIR, os.path.basename(p))
    if not os.path.exists(dst):
        shutil.copy2(p, dst)
    return dst


# ---------------------------------------------------------------- settings
def find_settings():
    """定位含 remoteBundles 的 settings.*.json，返回 (路径, 数据, 资源段key)。"""
    for p in sorted(glob.glob(os.path.join(BUILD, "src", "settings*.json"))):
        try:
            data = json.loads(read_text(p))
        except Exception:
            continue
        for key, sec in data.items():
            if isinstance(sec, dict) and "remoteBundles" in sec:
                return p, data, key
    return None, None, None


def load_game_json():
    p = os.path.join(BUILD, "game.json")
    return p, json.loads(read_text(p))


# ---------------------------------------------------------------- steps
def step_res_version():
    src = os.path.join(BUILD, "remote", "res_version.json")
    dst = os.path.join(BUILD, "remote", "res_version.0.json")
    if not os.path.exists(src):
        report("res_version", "FAIL", "缺 remote/res_version.json（构建产物不完整?）")
        return
    if os.path.exists(dst) and read_text(src) == read_text(dst):
        report("res_version", "SKIP", "res_version.0.json 已存在且一致")
        return
    if _args.check:
        report("res_version", "FAIL", "res_version.0.json 缺失或内容不一致（需执行拷贝）")
        return
    backup(dst)
    shutil.copy2(src, dst)
    report("res_version", "OK", "已拷贝 -> remote/res_version.0.json")


def step_version_ts():
    if not os.path.exists(VERSION_TS):
        report("Version.ts", "FAIL", "文件不存在: %s" % VERSION_TS)
        return
    txt = read_text(VERSION_TS)
    if "BUILD_VERSION" in txt:
        report("Version.ts", "SKIP", "占位符完好（未被构建写脏）")
        return
    if _args.check:
        report("Version.ts", "FAIL", "占位符被写脏（需还原为 BUILD_VERSION）")
        return
    new, n = re.subn(r'(export const Version\s*=\s*")([^"]+)(")', r"\1BUILD_VERSION\3", txt)
    if n != 1:
        report("Version.ts", "FAIL", "未匹配到 export const Version = \"...\" 结构，请人工核对")
        return
    backup(VERSION_TS)
    write_text(VERSION_TS, new)
    report("Version.ts", "OK", "已还原占位符 BUILD_VERSION")


def step_multtextures():
    sp, data, key = find_settings()
    if not sp:
        report("multTextures", "FAIL", "src/settings*.json 里找不到含 remoteBundles 的段")
        return
    sec = data[key]
    ver = (sec.get("bundleVers") or {}).get("multTextures")

    remote_dir = os.path.join(BUILD, "remote", "multTextures")
    bs_dir = os.path.join(BUILD, "src", "bundle-scripts", "multTextures")

    # 定位分包版源（本次构建产物）
    src = next((c for c in (os.path.join(BUILD, "subpackages", "multTextures"),
                            os.path.join(BUILD, "multTextures")) if os.path.isdir(c)), None)

    if src:
        cfgs = glob.glob(os.path.join(src, "config.*.json"))
        if len(cfgs) != 1:
            report("multTextures", "FAIL", "源目录 config.*.json 数量异常(%d): %s" % (len(cfgs), src))
            return
        src_ver = re.search(r"config\.([0-9a-f]+)\.json$", os.path.basename(cfgs[0]))
        src_ver = src_ver.group(1) if src_ver else None
        if ver and src_ver and ver != src_ver:
            report("multTextures", "FAIL",
                   "settings.bundleVer(%s) 与源 config 版本(%s) 不一致——源目录疑似旧构建残留，人工核对" % (ver, src_ver))
            return
        ver = ver or src_ver
        if _args.check:
            report("multTextures", "FAIL", "存在分包版源(%s)且尚未改造为远程 bundle" % os.path.relpath(src, BUILD))
            return
        # 拷 config + import/native -> remote/multTextures
        os.makedirs(remote_dir, exist_ok=True)
        backup(os.path.join(remote_dir, "config.%s.json" % (ver or "_")))
        shutil.copy2(cfgs[0], os.path.join(remote_dir, os.path.basename(cfgs[0])))
        for sub in ("import", "native"):
            s, d = os.path.join(src, sub), os.path.join(remote_dir, sub)
            if os.path.isdir(s):
                if os.path.isdir(d):
                    shutil.rmtree(d)
                shutil.copytree(s, d)
        # bundle 脚本入口: 源 game.js -> src/bundle-scripts/multTextures/index.{ver}.js
        js_src = next((c for c in (os.path.join(src, "game.js"), os.path.join(src, "index.js"))
                       if os.path.exists(c)), None)
        if not js_src:
            report("multTextures", "FAIL", "源目录里找不到 bundle 脚本入口(game.js/index.js)")
            return
        os.makedirs(bs_dir, exist_ok=True)
        write_text(os.path.join(bs_dir, "index.%s.js" % ver), read_text(js_src))
        # 清掉不同版本号的旧文件
        for p in glob.glob(os.path.join(remote_dir, "config.*.json")):
            if os.path.basename(p) != "config.%s.json" % ver:
                os.remove(p)
        for p in glob.glob(os.path.join(bs_dir, "index.*.js")):
            if os.path.basename(p) != "index.%s.js" % ver:
                os.remove(p)
        report("multTextures", "OK", "已从 %s 拷贝远程 bundle（ver=%s）" % (os.path.relpath(src, BUILD), ver))
    else:
        # 没有分包版源：要么已改造，要么产物异常
        if not os.path.exists(os.path.join(remote_dir, "config.%s.json" % (ver or "*"))):
            has_any = glob.glob(os.path.join(remote_dir, "config.*.json"))
            if not has_any:
                report("multTextures", "FAIL", "找不到分包版源，remote/multTextures 也为空——产物异常，人工核对")
                return
        report("multTextures", "SKIP", "无分包版源，remote/multTextures 已就位（视为已改造）")

    # settings: multTextures 挪到 remoteBundles
    subs = [x for x in (sec.get("subpackages") or []) if x != "multTextures"]
    rb = sec.get("remoteBundles") or []
    need_settings = (subs != (sec.get("subpackages") or [])) or ("multTextures" not in rb)
    if need_settings:
        if _args.check:
            report("multTextures", "FAIL", "settings.%s 段仍把 multTextures 配为分包" % key)
            return
        backup(sp)
        sec["subpackages"] = subs
        if "multTextures" not in rb:
            rb.append("multTextures")
        sec["remoteBundles"] = rb
        write_text(sp, json.dumps(data, ensure_ascii=False, separators=(",", ":")))
        report("multTextures", "OK", "settings: subpackages=%s remoteBundles=%s" % (subs, rb))
    else:
        report("multTextures", "SKIP", "settings 已是远程 bundle 配置")

    # game.json: subpackages 只留 scripts
    gp, gdata = load_game_json()
    gsubs = gdata.get("subpackages") or []
    g_new = [x for x in gsubs if x.get("name") != "multTextures"]
    if g_new != gsubs:
        if _args.check:
            report("multTextures", "FAIL", "game.json 仍含 multTextures 分包条目")
            return
        backup(gp)
        gdata["subpackages"] = g_new
        write_text(gp, json.dumps(gdata, ensure_ascii=False, indent=4))
        report("multTextures", "OK", "game.json 分包已只留 scripts")
    else:
        report("multTextures", "SKIP", "game.json 已只留 scripts 分包")


def step_priv_patch():
    if _args.skip_priv:
        report("privilege", "SKIP", "--skip-priv 指定，跳过")
        return
    gjs = os.path.join(BUILD, "subpackages", "scripts", "game.js")
    if not os.path.exists(gjs):
        report("privilege", "FAIL", "缺 %s" % gjs)
        return
    if "[PRIV-FIX] getPrivilegeVal skip" in read_text(gjs):
        report("privilege", "SKIP", "补丁已在（game.js 含 [PRIV-FIX] 容错）")
        return
    if _args.check:
        report("privilege", "FAIL", "补丁未打（cfg 快照缺新卡时战斗会崩）")
        return
    rc = subprocess.run([sys.executable, PRIV_FIX, "--gamejs", gjs,
                         "--bak", os.path.join(BAK_DIR, "game.js.bak_privfix")]).returncode
    if rc == 0 and "[PRIV-FIX] getPrivilegeVal skip" in read_text(gjs):
        report("privilege", "OK", "三处容错补丁已打（备份在 post_build_bak）")
    else:
        report("privilege", "FAIL", "priv_fix_patch.py 执行异常 rc=%d，人工核对" % rc)


# ---------------------------------------------------------------- verify
def verify():
    print("-" * 60)
    ok = True

    def chk(tag, cond, msg_ok, msg_bad):
        nonlocal ok
        if cond:
            report(tag, "OK" if tag != "multTextures.meta" else "OK", msg_ok)
        else:
            ok = False
            report(tag, "FAIL", msg_bad)

    sp, data, key = find_settings()
    if sp:
        sec = data[key]
        chk("v-settings", "multTextures" in (sec.get("remoteBundles") or [])
            and [x for x in (sec.get("subpackages") or []) if x != "multTextures"] == (sec.get("subpackages") or []),
            "remoteBundles 含 multTextures / subpackages=%s" % (sec.get("subpackages"),),
            "settings 分包/远程配置不对（见 [3]）")
        ver = (sec.get("bundleVers") or {}).get("multTextures")
    else:
        chk("v-settings", False, "", "找不到 settings")
        ver = None

    gp, gdata = load_game_json()
    names = [x.get("name") for x in (gdata.get("subpackages") or [])]
    chk("v-game.json", names == ["scripts"], "subpackages 只留 scripts", "game.json subpackages=%s" % names)

    cfg_ok = ver and os.path.exists(os.path.join(BUILD, "remote", "multTextures", "config.%s.json" % ver))
    idx_ok = ver and os.path.exists(os.path.join(BUILD, "src", "bundle-scripts", "multTextures", "index.%s.js" % ver))
    chk("v-remote-files", bool(cfg_ok and idx_ok),
        "remote/multTextures + bundle-scripts 入口齐备(ver=%s)" % ver,
        "远程 bundle 文件缺（ver=%s，见 [3]）" % ver)

    chk("v-res_version", os.path.exists(os.path.join(BUILD, "remote", "res_version.0.json")),
        "res_version.0.json 在", "res_version.0.json 缺（见 [1]）")

    vt_ok = os.path.exists(VERSION_TS) and "BUILD_VERSION" in read_text(VERSION_TS)
    chk("v-Version.ts", vt_ok, "占位符 BUILD_VERSION 完好", "占位符被写脏（见 [2]）")

    gjs = os.path.join(BUILD, "subpackages", "scripts", "game.js")
    pj_ok = os.path.exists(gjs) and "[PRIV-FIX] getPrivilegeVal skip" in read_text(gjs)
    chk("v-privilege", pj_ok, "特权卡容错补丁在", "补丁缺失（见 [4]）")

    if os.path.exists(META):
        m = read_text(META)
        is_bundle = '"isBundle": true' in m or '"isBundle":true' in m
        if is_bundle:
            report("multTextures.meta", "OK", "isBundle:true（SVN 基线）")
        else:
            ok = False
            report("multTextures.meta", "FAIL", "isBundle 非 true——meta 被写坏，先还原再重新构建！")
    else:
        report("multTextures.meta", "WARN", "找不到 meta（演练目录可忽略）")

    root_gjs = os.path.join(BUILD, "game.js")
    if os.path.exists(root_gjs):
        t = read_text(root_gjs)
        hooks = ("18080" in t) or ("PLAT-CFG-PATCH" in t)
        report("game.js 钩子", "INFO", "调试钩子在（可选件）" if hooks
               else "根 game.js 无调试钩子（可选件，需要 18080 收日志时按指南 §4.4 手工注入）")

    print("-" * 60)
    return ok


def main():
    print("post_build_wechatgame | build=%s" % BUILD)
    print("client=%s | mode=%s" % (CLIENT, "CHECK 只读巡检" if _args.check else "修复写入"))
    if _args.cocos and not _args.check:
        print("-" * 60)
        subprocess.run(["taskkill", "/f", "/im", "CocosCreator.exe"], capture_output=True)
        print("CLI 构建开始（约6分钟，中途不要杀）...")
        t0 = time.time()
        rc = subprocess.run([_args.cocos, "--project", CLIENT, "--build", "configPath=" + _args.config]).returncode
        print("CLI 构建结束 rc=%d 耗时%.1fmin" % (rc, (time.time() - t0) / 60))
        if rc != 0:
            report("cocos-build", "FAIL", "构建失败，终止后处理")
            sys.exit(1)
        report("cocos-build", "OK", "CLI 构建完成")

    if not _args.check:
        step_res_version()
        step_version_ts()
        step_multtextures()
        step_priv_patch()
    ok = verify()

    n_fail = sum(1 for _, s, _ in RESULTS if s == "FAIL")
    print("=" * 60)
    print("结果: %s（FAIL=%d）" % ("PASS 全部就绪" if ok else "FAIL 有缺项", n_fail))
    if not _args.check and ok:
        print("后续手工项: 起 8080 静态服务器 -> DevTools 点编译（勾不校验合法域名）-> 进一次战斗冒烟")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
