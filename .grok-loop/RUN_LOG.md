# Grok Loop运行索引

只追加已发生的事实，最近5条用于恢复；详细命令与结果存evidence／runs。

| 日期 | 类型 | 代码基点 | 结果 | 证据／下一步 |
|---|---|---|---|---|
| 2026-09-06 | Codex隔离基线 | d31b046 | 63 passed，1已有warning；非真机验证 | [baseline](evidence/baseline.json)；等待当前Grok接管，尚未启动新的后台循环 |
| 2026-09-06 | NIU-L00 PASS_SOFTWARE | 769bd45 | 导入不再打开现役SQLite；3 isolation + pytest exit 0；Checker PASS_SOFTWARE；未测真机 | [run](evidence/runs/20260906T074530-NIU-L00.json)；scheduler 01a073f8a1627741b5506ed398a38cbb；next NIU-L02 |
| 2026-09-06 | NIU-L02 PASS_SOFTWARE | a6e47f8 | 冻结后迟到 walk 拒绝；近距才冻腿；礼貌短走保留。BUILD/硬件 NOT_RUN | [run](evidence/runs/20260906T080000-NIU-L02.json)；next NIU-L01 |
| 2026-09-06 | NIU-L01 PASS_SOFTWARE | 381d86a | 独处冷却/安静/5句去重；PRESENT 后不再 tick 私密。硬件 NOT_RUN | [run](evidence/runs/20260906T081500-NIU-L01.json)；第3轮成功，启动独立评分 |
| 2026-09-06 | FAST_TRACK A/B/C + CI | f4379f3 | abort 丢旧秘密音频；ClawBot；脸契约；Actions。本地 94 passed | 独立复评 36.0→36.75；CG 全 NOT_RUN |
| 2026-09-06 | consume+health hash+CI | 2c12b7f | ABSENT 打断消费一次；/health 带 firmware_hash；Actions 绿；100 pytest | 独立复评 36.75→37.75 |
| 2026-09-06 | IDF BUILD_PASS | 8477f5f | `python scripts/build.py niulai-s3-expand-v17` exit 0；xiaozhi.bin 09:25 sha256 60387221…；overlay=native AE5245A671E7；未烧录 | [build-evidence](../firmware/xiaozhi-niulai/build-evidence.md) |


| 2026-09-06 | NIU-L03 PASS_SOFTWARE | 227f99d | /health version=git short or src-digest; abort leftover already in 90dfba7; 97 pytest; checker=unavailable; live 8000 not restarted | [run](evidence/runs/20260906T085000-NIU-L03.json); next P0-6-VERIFY |
| 2026-09-06 | P0-6-VERIFY PASS_SOFTWARE | f08ad6a | 16 walk/ttl/freeze tests; docs already ttl<=2000; no flash | [run](evidence/runs/20260906T090600-P0-6.json); next NIU-L04 |
| 2026-09-06 | STOPPED | 9124567 | `.grok-loop/STOP` present (Codex takeover). No product writes. Demo checkout preserved. `/health` timeout. STOP not deleted. | [run](evidence/runs/20260906T094812-STOP-CHECK.json); next NIU-L04 after STOP lifts |

Loop技能的可选上游只读适配器probe返回NEEDS_HUMAN：未安装固定版本的上游工具。它不是执行本协议的必要条件；本轮没有安装依赖，也没有把文档协议认证为L3控制器。

首次运行时Grok须补：唯一执行者、实际scheduler ID或scheduler不可用、当前HEAD、第一条episode。没有这些证据，不把状态写为RUNNING。
`20260906-codex-takeover` PASS_SOFTWARE_BUILD: 149 tests; 13 integrated files hash-matched; local HTTP/WS live; full IDF build E8259C5CC48C. Hardware NOT_RUN. See evidence/runs/20260906-codex-takeover.json and docs/codex-takeover-2026-09-06.md. Grok remains paused by STOP.

`20260906-codex-round2` PASS_SOFTWARE_BUILD: 156 tests; real cloud TTS/Opus/ASR; hello requires explicit ABSENT for private speech; cancellable mama intro independently reviewed; full IDF build F1275BF9EA42. 40-item 10:14 score baseline 30.75; 7 hardware gates NOT_RUN. See evidence/runs/20260906-codex-round2.json. Grok STOP retained.

## 2026-09-06 11:27 — 实体对话修复
用户已确认台架准备，round3烧录后复现仅妈妈。修复测距取消礼貌会话及语音模型加载晚于引擎问题；完整构建、COM6应用烧录、哈希校验成功。实机重启srmodels先加载，detector为MultiNet。当前服务合成输入Opus→ASR→回答音频通过，首音频4.074秒；实际喊名字、麦克风与完整回答待用户现场测试。SEC-2增量派生31.75，其余39项沿用旧快照。详见 docs/codex-dialogue-2026-09-06.md 和 evidence/runs/20260906-codex-dialogue.json。STOP保留，无自治调度器。

11:31 补充：用户确认对话通；真机BOOT问答及一次 niulai 关键词唤醒后问答均有UART闭环。保存私有 working-dialogue.bin；记录最终串口日志SHA，已释放COM6而未重置设备。当前基础连通通过，重复唤醒成功率与延迟门禁未验收。
