---
name: "game-vm-ops"
description: "p1-x 游戏服远程控制：通过 vm_ctl.py 指令化操控 VM 上的游戏服——开服/关服/停服/查状态/备份数据库/回档还原数据库/虚拟机开机关机快照/关服窗口调整虚拟机系统时间（跳开服天数、开活动跨 0 点）。凡用户要求启停游戏服、重启服务、备份数据库、覆盖/还原/回档数据库、控制虚拟机电源、修改服务器日期时间时调用。"
---

# 游戏服远程控制（vm_ctl.py）

一条命令入口，SSH 直连游戏服主机（192.168.*.*），不依赖 SecureCRT。完整原理、23 个远端脚本逐条注释见《操作说明》（`temp_case/reports/vm_ops_操作说明_20261028.md`），日常操作与故障排查见《使用教程》（`temp_case/reports/vm_ops_使用教程_20261028.md`）。

## 1. 入口与配置

- 工具：`D:\python\python3.9\python.exe E:\workproject\temp_case\scripts\vm_ctl.py <子命令>`
- 连接配置：`temp_case/scripts/vm_servers.local.json`（**含明文 SSH 密码，只进 workproject01 备份仓，严禁进 workproject02 展示仓**；host/user/password/vmx/backup_dir/servers 白名单/别名）
- 操作台账：`temp_case/reports/vm_ops_ledger.jsonl`（每次操作自动记一条，密码自动掩码）
- 通道：paramiko SSH 直连（yang/***，sudo 同密码），游戏进程 root 属主 → start/stop/kill 已自动 sudo 包装
- 高危子命令（stop/kill/recover/vm off/setdate）必须 `--yes`

## 2. 命令速查

```
vm_ctl.py status --server 5服                    # 查状态（安全）
vm_ctl.py start  --server 5服                    # 开服 = start_all.sh cross_x1
vm_ctl.py stop   --server 5服 --yes              # 优雅停服
vm_ctl.py kill   --server 5服 --yes              # 强杀全机 skynet（兜底）
vm_ctl.py backup --server 5服                    # 备份数据库
vm_ctl.py backups --server 5服                   # 列出可还原备份
vm_ctl.py recover --server 5服 --dir <备份目录名> --yes   # 回档（先自动备份当前库）
vm_ctl.py setdate --datetime "2026-10-30 23:58" --yes    # 调 VM 系统时间（须关服窗口；跳天数开活动用）
vm_ctl.py setdate --sync-local --yes                     # 测完拨回：同步为本机真实时间
vm_ctl.py vm list | snap | on | off --yes        # 虚拟机电源层（vmrun）
vm_ctl.py probe                                  # 只读探查 VM 结构
vm_ctl.py raw --cmd "<命令>"                     # 任意命令（在部署目录执行）
```

- `--server` 接受别名（3服~7服）或 env 名 cross_x1；raw 传含 `$()` 的命令要用**单引号**（PowerShell 双引号内 `$(...)` 会被本地展开）

## 3. 关键事实（动手前必读）

1. **3/4/5/6/7 服是同一部署 cross_x1 的五个区服**（ServerList server_id 3~7），共库 `game_cross_x1`——开关/备份/回档对五个服整体生效，不是只动"5 服"。
2. 3~7 服均为用户个人测试服，可直接操作；但 S5 GM 操作类（非本 skill 范畴）遵循"改→测→还原"。
3. **停服是异步的**：stop 返回 OK 后进程数秒才退尽；`status` 显示的 PID 是 config 记录值，停服瞬间仍显示旧值，真实存活以 `raw --cmd 'ps -ef | grep skynet | grep -v grep | wc -l'` 为准（0=全停，14=全起）。
4. start_all 前置 baklog 检测到任何 skynet 存活即拒绝启动 → start 被拒就先 stop。
5. recover 流程：校验备份目录存在 → 强制已停服 → **自动备份当前库**（保险）→ `mongorestore --drop` 覆盖还原。回档目标优先选近期快照（数据回退最小）；保险备份确认无误后再删。
6. 备份是目录（非 tar.gz）且**不会自动清理**（脚本 14 天清理是死代码）——堆积多了手动删，删除用精确全路径 rm -rf，勿用通配符。
7. 备份/还原不依赖当前 config 是哪个 env（mongos.conf host 恒 127.0.0.1:27017）；VM env_config 有 cross_x1.lua 而 trunk 没有（trunk 较旧，勿拿 trunk 判合法 env）。
8. 备份目录名时间戳取自 VM 时钟——setdate 调过时间后目录名日期跟着新时钟走，找"最新备份"看列表排序而非文件名日期。（2026-10-28 曾停在中途日期，已用 setdate --sync-local 拨回真实时间）
9. **VM OS 时钟是 skynet/MongoDB/日志的统一时间源**，setdate 改它全局生效，覆盖面比 GM set_timeshift 完整（后者只动 skynet 层）。硬约束：①必须在关服窗口执行——工具检测到 skynet 存活即拒绝；②VM 硬件时钟未同步，虚拟机重启后时间可能还原；③改后 GM set_timeshift 的时间偏移模型失效，需重新实测校准；④向前跳转后尽量避免往回调，否则按未来日期开启的活动/状态可能错乱（测试 VM 上短暂跳转再拨回已实测无恙）。
10. stop_all 在 directorsvr 已死时会 killall skynet 兜底（波及全机）；kill 也是全机级。
11. 验证状态：probe/status/backup/backups/**setdate**/vm list/snap/**stop/start/recover** 已闭环实测 PASS（2026-10-28，操作说明 §7.1）；仅 kill/vm on/vm off 未实测。

## 4. 典型工作流

- **改坏数据回档**：stop --yes → recover --dir <备份> --yes → start
- **改数据前保险**：backup → （改数据/测试）→ 必要时 recover 刚做的备份
- **VM 重启后拉起**：vm list（不在则 vm on）→ status → start
- **跳开服天数 / 开活动跨 0 点**（2026-10-28 实测闭环 PASS）：stop --yes → `setdate --datetime "目标日 23:58" --yes` → start（等自然跨 0 点，服务端整点/每日调度自动触发）→ 测完 stop --yes → `setdate --sync-local --yes` → start。实测：跨 0 点时 scenesvr 打出 `WeekDay 5 Hour 0 NewHour`（星期与目标日吻合），14 进程全存活；日志在 `/home/p1x/server/src/log/`，start_all 的 baklog 目录名即取自当次 VM 时钟。
