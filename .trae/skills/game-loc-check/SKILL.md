# game-loc-check —— 改名/翻译漏改核查方法论 + 工具

适用场景：游戏内术语改名（如「秘宝→仙机」）或翻译版本发布前，核查文字、配置、prefab、图片、入口图标是否有漏改。与 game-ui-e2e-test（运行时 UI 测试）互补：本 skill 做**静态资产核查**，不需要启动游戏。

## 铁律（违反即事故）

1. **源文件只读**：对 E:\p1-x 一切内容只读；svn 仅用 ls/cat/diff --summarize/export
2. **输出白名单**：所有输出/缓存/基线必须位于 `E:\workproject` 内（工具入口有断言）
3. **tag 一律手动指定**：本地 trunk/tag_new/tag 是滚动目录，工具不做自动推断；缺参时打印可选清单提示用户
4. **开跑先身份自检**：两源差异极小（<0.5%）→ 红字警告"可能刚打完包，对比无意义"
5. **凭证隔离**：svn 账号只存 `harness/loc_check/svn_auth.local.json`，不进报告/SKILL/产物
6. **xlsx 残留=高危**：策划源表未改，重导会回退客户端，一律 must_fix

## 工具（harness/loc_check/）

- `run_check.py`：CLI 入口（scan / compare / images / list-tags / report）
- `scanners.py`：文本+xlsx 术语扫描、身份自检、输出白名单断言
- `svnclient.py`：svn 只读封装（子命令白名单）
- `img_refs.py`：图片清单 + uuid 引用链反查
- `report.py`：Excel（含发现日期/修改日期栏）+ Markdown
- `terms_*.json`：术语任务文件（按任务命名留存）
- svn.exe：SlikSVN 1.14.5 便携版在 `harness/vendor/svn/app/PFiles/bin/`

## 三级对比体系

| 类型 | 原型(基线) | 验证集 | 命令 |
|---|---|---|---|
| ①版本验收 | 指定 tag URL | 指定 tag URL | `compare --src-a <URL> --src-b <URL>` |
| ②问题回归 | 快照 baseline.json | 当前 trunk | `scan --vs-baseline <json>`（已修复自动回填修改日期） |
| ③全量巡检 | 术语表驱动 | 单源 | `scan --src E:\p1-x\trunk` |

原理：术语残留扫描只需**验证集**一份全量数据；原型集仅用于图片对比+变更归因（`svn diff --summarize` 秒级、零导出）。URL 源 export 缓存在 `temp_case/.svn_cache/`，复用 `--refresh` 强刷。

## 标准流程（新任务接入）

1. 建 `terms_<任务名>.json`：old→new 术语 + 白名单（如「神秘宝箱」）+ 扫描范围
2. `python run_check.py list-tags` 挑 tag（手动）
3. `compare --src-a E:\p1-x\trunk --src-b E:\p1-x\tag_new`（或两 tag URL）
4. 看报告四级分级：**确认漏改 / 疑似待复核 / 注释级 / 白名单命中**；修复后 `scan --vs-baseline` 复跑验收
5. 图片环节：`images --src ... --subdir <目录>` 出人工清单（引用链反查到 prefab/config）；文字内容靠 OCR——引擎已定稿 **RapidOCR**（`harness/loc_check/ocr.py` 封装，`ocr_bench.py` 基准脚本）

## 已知限制 / 待办

- `http://svn.******.com/p2/src/`（美术/策划/工具目录）****** 账号无权限 → 上游源头核查暂不可用，需申请授权
- tag URL 格式：`http://svn.******.com/p1-x/tags/YYYY-MM-DD`（15 个日期 tag 已验证）
- OCR 引擎已定稿 RapidOCR（2026-09-21 基准 12/12 PASS：秘宝烙字图全召回置信 1.0、负样本零误报、单图 0.2~0.4s、2x 放大无增益→默认原图）；风格化烙字可能漏检→低置信转人工清单；PaddleOCR 留备选未接
- 翻译专项（多语种 cfg_langs key 完整性/占位符/UI溢出/字体/多语种切图）**留档待用户确认**，当前只做文件变化修改对比
- 玩家存量数据（已购礼包名/邮件标题）、音频配音属工具盲区，需运营/人工清单
