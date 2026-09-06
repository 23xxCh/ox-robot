# IDF BUILD_PASS / FLASH_PASS — 实体对话基础连通通过

2026-09-06 11:22 完整构建成功，随后 COM6 以 460800 波特率仅更新 `0x20000` 应用分区，写入 2,805,264 字节并通过 esptool `Hash of data verified`。未重写 NVS 和资源分区。用户已确认台架接线准备。

- 当前应用 SHA256：`2FA63F2A6FF446D013F48B4BBF83476DF73034289DA482F9ED7A28F3EB279C46`。
- native `application.cc`：`20B99D565A9E04A5207163A648FBAD95B51CF0C98990BD41793EC9C69A303EF9`；`application.h` 沿用 `302D03C06EED68A3B4BE5BB0B7236CAAD53AD5E359830B6686B2B6E04AE2849B`。
- `generated_assets.bin`：3,127,685 字节，SHA256 `B1FBEF49B009A0B0A352BBFFF089DCBF1B53BDF7F7F075F669E4C077078DEC5C`，与前次烧录资源一致。
- 日志：`.scratch/codex-round4/idf-build.log`、`flash-write.log`、`serial-after.log`。旧应用回退副本 `application-before.bin` 留在同一忽略目录；当前镜像含私有设备配置，未复制到公开交付目录。
- 烧录后实际重启：ELF SHA 前缀 `c22101d8c`；启动 768 ms 加载 srmodels，778 ms 记录本地资源应用，7358 ms 初始化 `detector: MultiNet`。未再出现引擎拒绝替换模型的旧故障。板子取得 IP `192.168.18.251`。
- 持久源码检查 `check_application_intro.py` 与 `check_application_voice_startup.py` 均通过。11:31 用户确认“对话通了”；串口记录 BOOT 后实体转录与回答，以及一次实际关键词 `niulai` 检测 → 妈妈 → 收音 → 回答。可靠性分母和延迟门禁仍未完成，详见 `docs/codex-dialogue-2026-09-06.md`。
- 当前已验基础连通镜像私有副本：`.scratch/codex-round4/working-dialogue.bin`，SHA256 与本段当前应用一致。串口观察已结束并释放 COM6，未重置设备。

## 历史构建：10:33（第二轮，彼时未烧录）

2026-09-06 10:33 +08，第二轮完整构建成功，exit 0。妈妈等待改为可取消定时事件，包含旧回复过滤和正常 VAD 回复保护，已通过独立源码复核及实际 C++ 检查。

- `xiaozhi.bin`：2,804,672 字节，SHA256 `F1275BF9EA427DDE4C7F28AC77BF304102949FE070CB22A83C52C8AB3F5A900D`。
- `merged-binary.bin`：11,516,293 字节，SHA256 `117443B1EC9B94455C56D0CC0E07C55ECB29010C2CD52D0F31B20907B39CA0D9`。
- 应用副本：`outputs/niulai-codex-round2-2026-09-06/xiaozhi.bin`；日志：`.scratch/codex-round2/idf-build.log`；完整记录：`.grok-loop/evidence/runs/20260906-codex-round2.json`。
- 命令：`python scripts/build.py niulai-s3-expand-v17 --name niulai-s3-expand-v17`。IDF export 将工具入口解析到 `E:\AI_TOY_NATIVE\esp-idf-v6.0.2`；UTF-8 环境已设置。
- native `application.cc` SHA256 `458AE720797A69152B115FB09D0DBFC7CA3932911FAF7C070C74763197CC37A2`，`application.h` SHA256 `302D03C06EED68A3B4BE5BB0B7236CAAD53AD5E359830B6686B2B6E04AE2849B`。
- 仍未烧录、未打开串口、未做实体声音与动作验收；仅更改固件目标 IP 不代表服务已可从板端访问。

## 历史构建：10:02（第一轮接管）

2026-09-06 10:02 +08，Codex 接管修复构建成功，exit 0。命令仍为 `python scripts/build.py niulai-s3-expand-v17 --name niulai-s3-expand-v17`，另设 `PYTHONUTF8=1`、`PYTHONIOENCODING=utf-8`。

- `xiaozhi.bin`：2,803,312 字节，SHA256 `E8259C5CC48CDBDF40F6CDD600D3C70B46C6CDD8D8CFBC68B57453240D7B3C22`。
- `merged-binary.bin`：11,516,293 字节，SHA256 `15DF8DBA2C49E749DFC9082803BBCA13B87B711FA38276D74D5D9D059630C002`。
- overlay/native 的 `niulai_life.cc`、`niulai_life.h`、`niulai_presence.h` 已同步；本次包含测距失效 UNKNOWN 保护。
- 应用固件副本：`outputs/niulai-codex-2026-09-06/xiaozhi.bin`；日志：`.scratch/codex-takeover/idf-build-utf8.log`（均相对项目根目录）。
- COM6 只验证到 CH340 枚举；未烧录、未听到真机声音、未测停止时延。合并镜像不能当成保留 NVS 的更新包。

## 历史构建：09:25（修复前）

Date: 2026-09-06 09:25 +08  
Command: `python scripts/build.py niulai-s3-expand-v17`  
Cwd: `E:\XIAOZHI_NATIVE\xiaozhi-esp32`  
IDF: 6.0.2  
Exit: 0  
Heard / COM6: NOT_RUN

| artifact | size | sha256 | mtime |
|---|---:|---|---|
| `build/xiaozhi.bin` | 2803120 (0x2ac5b0) | `60387221D40C45855BFBAB35B992AE2E538B64397BE0A5F6E8D75E95EEA4CDC0` | 2026-09-06 09:25:09 |
| `build/merged-binary.bin` | 11516293 (0xafb985) | `1CC75308E710C7B5188A6098AE212D46D0AD95A18CE34B42EC2428AECFBFEAEB` | 2026-09-06 09:25:15 |

Overlay `niulai_life.cc` sha256[:12] `AE5245A671E7` **MATCH** native `main/boards/niulai-s3-expand-v17/niulai_life.cc`.

This is source+build identity, not axis calibration and not on-device playback.
