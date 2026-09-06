# Grok Loop运行索引

只追加已发生的事实，最近5条用于恢复；详细命令与结果存evidence／runs。

| 日期 | 类型 | 代码基点 | 结果 | 证据／下一步 |
|---|---|---|---|---|
| 2026-09-06 | Codex隔离基线 | d31b046 | 63 passed，1已有warning；非真机验证 | [baseline](evidence/baseline.json)；等待当前Grok接管，尚未启动新的后台循环 |
| 2026-09-06 | NIU-L00 PASS_SOFTWARE | 769bd45 | 导入不再打开现役SQLite；3 isolation + pytest exit 0；Checker PASS_SOFTWARE；未测真机 | [run](evidence/runs/20260906T074530-NIU-L00.json)；scheduler 01a073f8a1627741b5506ed398a38cbb；next NIU-L02 |
| 2026-09-06 | NIU-L02 PASS_SOFTWARE | a6e47f8 | 冻结后迟到 walk 拒绝；近距才冻腿；礼貌短走保留。BUILD/硬件 NOT_RUN | [run](evidence/runs/20260906T080000-NIU-L02.json)；next NIU-L01 |
| 2026-09-06 | NIU-L01 PASS_SOFTWARE | 381d86a | 独处冷却/安静/5句去重；PRESENT 后不再 tick 私密。硬件 NOT_RUN | [run](evidence/runs/20260906T081500-NIU-L01.json)；第3轮成功，启动独立评分 |

Loop技能的可选上游只读适配器probe返回NEEDS_HUMAN：未安装固定版本的上游工具。它不是执行本协议的必要条件；本轮没有安装依赖，也没有把文档协议认证为L3控制器。

首次运行时Grok须补：唯一执行者、实际scheduler ID或scheduler不可用、当前HEAD、第一条episode。没有这些证据，不把状态写为RUNNING。
