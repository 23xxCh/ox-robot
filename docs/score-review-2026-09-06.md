# 牛来项目完整评分复评

评分时间：2026-09-06T10:19:00.370933+08:00。源码快照时间：2026-09-06T10:14:23.866362+08:00。本次总分 **30.75/100**，七项完整门禁 **全部 NOT_RUN**，没有真机或用户研究通过的结论。

这是首个按固定40项、7门禁和逐项证据形成的完整基线。历史37.75只是一份汇总，缺项目分与门禁证据，**不能据差值认定项目退步或进步**。

## 快照与证据边界

- Git基点：`91245675a2682d30e299144721cbf667761e2830`，工作区有未提交修改。
- 源码差异SHA256：`e99c3fe173fbb5706c84ae1d88179b5b85f76791fe18bbac200a5511c1f31f73`。范围为 `git diff --binary HEAD -- brain firmware .github pytest.ini`。
- 文件清单SHA256：`e97a8c9f1de68d0311295e82454b63ff50bd575d2619ab073b9b1b6e05e33c09`；逐文件哈希和证据类型在[完整JSON](../.grok-loop/scores/20260906-codex-review.json)。
- 上轮[验证记录](../.grok-loop/evidence/runs/20260906-codex-takeover.json)为149项通过、1个警告、退出码0；本次未重复执行。13个整合文件在10:14快照中11个仍匹配，`main.py`和`test_protocol.py`已有新health改动。取消相关逻辑与受测副本的对应部分未变；149不代表当前整树已回归。
- 已实际核对[应用镜像](../outputs/niulai-codex-2026-09-06/xiaozhi.bin)SHA256为`e8259c5cc48cdbdf40f6cdd600d3c70b46c6cdd8d8cfbc68b57453240d7b3c22`，对应[完整构建日志](../.scratch/codex-takeover/idf-build-utf8.log)，未烧录。
- 后台语音链和native源码正在继续修改。本快照不代表之后的源码、后台进程或板上固件；后续证据必须按新版本复核。
- 本审查者曾实现记忆/动作口令的局部修复，涉及DB-2/3/4/5、SEC-1/2的分数由Root独立审查后确定，JSON保留逐项checker；没有把自己的新改动直接自评加分。

## 维度评分

公式沿用[评分合同](../.grok-loop/SCORECARD.md)：每维五项，每项0–4，维度分为项目和÷20×100，总分按固定权重加权。本轮只使用0–2；0表示复核后无对应验收证据，不把未知项悄悄当零。

| 维度 | 权重 | 得分 |
|---|---:|---:|
| EX | 25% | 30/100 |
| FE | 10% | 30/100 |
| BE | 15% | 35/100 |
| DB | 10% | 30/100 |
| FW | 20% | 30/100 |
| SEC | 10% | 25/100 |
| QA | 5% | 40/100 |
| AR | 5% | 30/100 |

每项2分仅表示对应软件层面已有集成验证。读到源码、模板、模拟或部分实现通常只有1分。真实环境和重复量化验收未完成，全部不计3/4分。

## 四十项明细

| 项目 | 得分 | 判断及限制 | 证据 |
|---|---:|---|---|
| EX-1 最新人格规则一致 | 2/4 | 最新 GOAL 保留靠近不播妈妈、唤醒后礼貌、独处才私语；WSS 人格与表情转换有软件回归，妈妈在板端的顺序仍只具源码/构建证据。 | [GOAL.md](../GOAL.md)、[brain/app/main.py](../brain/app/main.py)、[brain/tests/test_protocol.py](../brain/tests/test_protocol.py)、[brain/tests/test_face_contract.py](../brain/tests/test_face_contract.py)、[.grok-loop/evidence/runs/20260906-codex-takeover.json](../.grok-loop/evidence/runs/20260906-codex-takeover.json) |
| EX-2 自主行为有原因与留白 | 2/4 | SecretDirector 冷却、安静拍和最近五句去重已有可控时钟测试及组合调用验证；三分钟自然节奏与触发事件相关性仍未做人评。 | [brain/app/secret_life.py](../brain/app/secret_life.py)、[brain/tests/test_secret_life.py](../brain/tests/test_secret_life.py)、[.grok-loop/evidence/runs/20260906-codex-takeover.json](../.grok-loop/evidence/runs/20260906-codex-takeover.json) |
| EX-3 声音眼神身体协同 | 1/4 | 已有脸部状态映射、TTS 生命周期与板端动作实现，测试只验证消息/表情类别；没有同版本声画动作时间轴验证。 | [brain/tests/test_face_contract.py](../brain/tests/test_face_contract.py)、[firmware/xiaozhi-niulai/niulai_face_display.cc](../firmware/xiaozhi-niulai/niulai_face_display.cc)、[firmware/xiaozhi-niulai/niulai_life.cc](../firmware/xiaozhi-niulai/niulai_life.cc)、[firmware/xiaozhi-niulai/build-evidence.md](../firmware/xiaozhi-niulai/build-evidence.md) |
| EX-4 真实经历连续 | 1/4 | 打断内容能保存、进入独处提示并消费，但 wake 仍按播放完成事件计数；mock 独处台词未证明实际引用该次打断，生成即消费也不等于已播出。 | [brain/app/main.py](../brain/app/main.py)、[brain/app/memory.py](../brain/app/memory.py)、[brain/app/origin.py](../brain/app/origin.py)、[brain/tests/test_protocol.py](../brain/tests/test_protocol.py)、[.grok-loop/evidence/runs/20260906-codex-takeover.json](../.grok-loop/evidence/runs/20260906-codex-takeover.json) |
| EX-5 陌生观众理解与语气听感 | 0/4 | 已审查交接证据：未提供陌生观众观察、同角色盲听或真机语气样本的验收记录；明确按无证据计零。 | [docs/codex-takeover-2026-09-06.md](../docs/codex-takeover-2026-09-06.md)、[.grok-loop/PRODUCT_BACKLOG.md](../.grok-loop/PRODUCT_BACKLOG.md) |
| FE-1 状态真实 | 2/4 | 排练台 API 明确返回 sim/模拟状态，页面有陈旧标志；测试验证模拟身份和状态转换。尚未显示真实设备遥测，分数仅对应软件模拟状态诚实性。 | [brain/app/api.py](../brain/app/api.py)、[brain/app/web/rehearsal.js](../brain/app/web/rehearsal.js)、[brain/tests/test_web.py](../brain/tests/test_web.py)、[.grok-loop/evidence/runs/20260906-codex-takeover.json](../.grok-loop/evidence/runs/20260906-codex-takeover.json) |
| FE-2 请求与执行闭环 | 1/4 | 暂停返回 202/request_id 并明确不宣称物理停稳，模拟重复暂停已测；尚无设备 ACK、拒绝原因或真实执行完成闭环。 | [brain/app/api.py](../brain/app/api.py)、[brain/app/web/rehearsal.js](../brain/app/web/rehearsal.js)、[brain/tests/test_web.py](../brain/tests/test_web.py) |
| FE-3 可用性、键盘与响应式 | 1/4 | 页面有 skip link、viewport、focus-visible、44px 按钮和 360px CSS；仅静态 HTML 检查，没有实际浏览器键盘/宽窄屏操作验收。 | [brain/app/web/index.html](../brain/app/web/index.html)、[brain/app/web/rehearsal.css](../brain/app/web/rehearsal.css)、[brain/tests/test_web.py](../brain/tests/test_web.py) |
| FE-4 数据与权限边界 | 1/4 | 输出采用 textContent，模拟入口有模式检查及部分负例；角色编辑、聊天和清空入口仍缺身份授权，不能据 XSS 局部防护认定完整权限边界。 | [brain/app/web/rehearsal.js](../brain/app/web/rehearsal.js)、[brain/app/web/life.js](../brain/app/web/life.js)、[brain/app/api.py](../brain/app/api.py)、[brain/tests/test_web.py](../brain/tests/test_web.py) |
| FE-5 性能与断线恢复 | 1/4 | 实现 500ms 状态轮询、2s 陈旧提示和 500 条 DOM 限制；没有浏览器断线恢复、并发轮询乱序或性能实测证据。 | [brain/app/web/rehearsal.js](../brain/app/web/rehearsal.js)、[brain/tests/test_web.py](../brain/tests/test_web.py) |
| BE-1 真实语音与设备协议 | 2/4 | WSS hello/listen/STT/LLM/TTS 软件集成与真实 FFmpeg Opus 编码记录存在；149 回归用假 ASR/LLM/TTS，尚不证明完整真实语音链或板上播放。 | [brain/app/main.py](../brain/app/main.py)、[brain/app/media.py](../brain/app/media.py)、[brain/tests/test_protocol.py](../brain/tests/test_protocol.py)、[brain/tests/test_media.py](../brain/tests/test_media.py)、[.grok-loop/evidence/runs/20260906-codex-takeover.json](../.grok-loop/evidence/runs/20260906-codex-takeover.json) |
| BE-2 入口统一服从状态 | 1/4 | WSS、IM 和 Web 各自有状态限制测试，但 Web 使用独立模拟状态、IM 沿另一文本管道，缺少全入口共用同一设备状态/权限的集成证明。 | [brain/app/main.py](../brain/app/main.py)、[brain/app/im.py](../brain/app/im.py)、[brain/app/api.py](../brain/app/api.py)、[brain/app/brain.py](../brain/app/brain.py)、[brain/tests/test_im.py](../brain/tests/test_im.py) |
| BE-3 取消与并发 | 2/4 | 首句/周期 TTS、阻塞 LLM、ASR、动作回复的取消与恢复有独立屏障回归；连接保持至旧任务退出并检查所有迟到帧。HTTP 同步供应商已移出事件循环并拒绝旧回复。 | [brain/app/main.py](../brain/app/main.py)、[brain/app/api.py](../brain/app/api.py)、[brain/tests/test_protocol.py](../brain/tests/test_protocol.py)、[brain/tests/test_site.py](../brain/tests/test_site.py)、[.grok-loop/evidence/runs/20260906-codex-takeover.json](../.grok-loop/evidence/runs/20260906-codex-takeover.json) |
| BE-4 动作生命周期与去重 | 1/4 | 明确口令、TTL 和旧语音 generation 保护已实现，IM 事件 ID 有会话内去重；WSS 动作未携带完整 command_id/ACK/重连代际，不能证明端到端恰好一次。 | [brain/app/main.py](../brain/app/main.py)、[brain/app/scripting.py](../brain/app/scripting.py)、[brain/app/im.py](../brain/app/im.py)、[brain/tests/test_freeze_mcp.py](../brain/tests/test_freeze_mcp.py)、[brain/tests/test_im.py](../brain/tests/test_im.py) |
| BE-5 容量、版本与运行追踪 | 1/4 | 有音频/事件容量限制与运行记录。快照新增 health Git/源码元数据更准确，但不在149受测哈希内；未提供本快照运行验证、连接容量或完整请求追踪。 | [brain/app/main.py](../brain/app/main.py)、[brain/app/api.py](../brain/app/api.py)、[brain/tests/test_protocol.py](../brain/tests/test_protocol.py)、[.grok-loop/evidence/runs/20260906-codex-takeover.json](../.grok-loop/evidence/runs/20260906-codex-takeover.json) |
| DB-1 schema 与迁移 | 2/4 | SQLite schema_migrations、唯一约束、索引和重新打开现有库已有临时数据库验证；只实现初始化版本，升级/回滚迁移仍未证明。 | [brain/app/memory.py](../brain/app/memory.py)、[brain/tests/test_memory.py](../brain/tests/test_memory.py)、[.grok-loop/evidence/runs/20260906-codex-takeover.json](../.grok-loop/evidence/runs/20260906-codex-takeover.json) |
| DB-2 事务与幂等 | 1/4 | Root 独立确认：事件 ID 去重和首次创建并发已证，但 commit_event 多语句缺少异常 rollback，(device,boot,seq) 冲突后的恢复未证。 | [brain/app/memory.py](../brain/app/memory.py)、[brain/tests/test_memory.py](../brain/tests/test_memory.py)、[.grok-loop/evidence/runs/20260906-codex-takeover.json](../.grok-loop/evidence/runs/20260906-codex-takeover.json) |
| DB-3 记忆事实与恢复 | 1/4 | Root 独立确认：重开与消费已测，但 WSS wake 调用 bump_mama 写 mama_play_completed，缺真实播放回执，事实语义仍有缺口。 | [brain/app/memory.py](../brain/app/memory.py)、[brain/app/main.py](../brain/app/main.py)、[brain/tests/test_memory.py](../brain/tests/test_memory.py)、[.grok-loop/evidence/runs/20260906-codex-takeover.json](../.grok-loop/evidence/runs/20260906-codex-takeover.json) |
| DB-4 留存、清空与隐私 | 1/4 | Root 独立确认：generation 清空、保留界限和 PRESENT 私密隔离已测，真实用户清空与飞行中任务清空闭环尚未验证。 | [brain/app/memory.py](../brain/app/memory.py)、[brain/app/main.py](../brain/app/main.py)、[brain/tests/test_memory.py](../brain/tests/test_memory.py)、[.grok-loop/evidence/runs/20260906-codex-takeover.json](../.grok-loop/evidence/runs/20260906-codex-takeover.json) |
| DB-5 故障恢复、备份与性能 | 1/4 | Root 独立确认：SQLite 备份拷贝后重开有证据；崩溃/磁盘失败注入、在线一致性备份和性能无证据。 | [brain/app/memory.py](../brain/app/memory.py)、[brain/tests/test_memory.py](../brain/tests/test_memory.py)、[.grok-loop/evidence/runs/20260906-codex-takeover.json](../.grok-loop/evidence/runs/20260906-codex-takeover.json) |
| FW-1 可复现构建与逐轴校准 | 1/4 | 已核对完整 IDF 构建日志及 e825 固件 SHA256；外部 native 树的全部改动尚未能从干净上游重现，四轴中位/方向/边界也未标定。 | [firmware/xiaozhi-niulai/build-evidence.md](../firmware/xiaozhi-niulai/build-evidence.md)、[firmware/xiaozhi-niulai/README.md](../firmware/xiaozhi-niulai/README.md)、[.scratch/codex-takeover/idf-build-utf8.log](../.scratch/codex-takeover/idf-build-utf8.log)、[outputs/niulai-codex-2026-09-06/xiaozhi.bin](../outputs/niulai-codex-2026-09-06/xiaozhi.bin) |
| FW-2 非阻塞可取消调度 | 1/4 | 板端有独立生命任务、短动作截止和排队 SECRET 再检查；200ms 轮询、超声忙等以及 native 妈妈等待/开链仍会影响取消，无目标时延测试。 | [firmware/xiaozhi-niulai/niulai_life.cc](../firmware/xiaozhi-niulai/niulai_life.cc)、[firmware/xiaozhi-niulai/README.md](../firmware/xiaozhi-niulai/README.md)、[docs/codex-takeover-2026-09-06.md](../docs/codex-takeover-2026-09-06.md) |
| FW-3 本地安全与感知边界 | 2/4 | 真实 C++ 决策函数通过编译期断言覆盖超时、NaN、越界、连续八秒远距和故障恢复；UNKNOWN 停腿与排队 SECRET 保护已进入构建。仍只针对超声覆盖区，不是可靠人员识别。 | [firmware/xiaozhi-niulai/niulai_presence.h](../firmware/xiaozhi-niulai/niulai_presence.h)、[firmware/xiaozhi-niulai/niulai_life.cc](../firmware/xiaozhi-niulai/niulai_life.cc)、[brain/tests/test_firmware_source_guards.py](../brain/tests/test_firmware_source_guards.py)、[.grok-loop/evidence/runs/20260906-codex-takeover.json](../.grok-loop/evidence/runs/20260906-codex-takeover.json) |
| FW-4 协议校验与执行结果 | 1/4 | PulseMotion 校验 UNKNOWN/近距、停止与 TTL；未知方向仍可落入默认步态，缺设备动作 ID、过期/重放判定和执行结果 ACK 的完整证明。 | [firmware/xiaozhi-niulai/niulai_life.cc](../firmware/xiaozhi-niulai/niulai_life.cc)、[firmware/xiaozhi-niulai/niulai_life.h](../firmware/xiaozhi-niulai/niulai_life.h)、[brain/tests/test_firmware_source_guards.py](../brain/tests/test_firmware_source_guards.py) |
| FW-5 声音表情动作与离线可靠性 | 1/4 | 脸部、三段本地 OGG 与 native 回退路径存在且已构建，但断网/恢复无双音轨、音频可打断和真机听感未验证。历史 fallback 文档部分状态已过时，不用它宣称当前设备行为。 | [firmware/xiaozhi-niulai/niulai_face_display.cc](../firmware/xiaozhi-niulai/niulai_face_display.cc)、[firmware/xiaozhi-niulai/niulai_life.cc](../firmware/xiaozhi-niulai/niulai_life.cc)、[firmware/xiaozhi-niulai/README.md](../firmware/xiaozhi-niulai/README.md)、[firmware/xiaozhi-niulai/build-evidence.md](../firmware/xiaozhi-niulai/build-evidence.md) |
| SEC-1 能力最小化 | 2/4 | Root 独立确认：整句动作白名单、LLM 不能自行授权、方向/停止不能被模型覆盖及 TTL 限制已由149软件回归覆盖。 | [brain/app/scripting.py](../brain/app/scripting.py)、[brain/app/schemas.py](../brain/app/schemas.py)、[brain/tests/test_scripting.py](../brain/tests/test_scripting.py)、[brain/tests/test_lua.py](../brain/tests/test_lua.py)、[.grok-loop/evidence/runs/20260906-codex-takeover.json](../.grok-loop/evidence/runs/20260906-codex-takeover.json) |
| SEC-2 来源与授权 | 0/4 | Root 独立确认：WSS 无身份校验；IM 仅检查任意 token 头是否存在，不比较凭据；此处已有代码不能当作认证实现计分。 | [brain/app/main.py](../brain/app/main.py)、[brain/app/im.py](../brain/app/im.py)、[brain/tests/test_im.py](../brain/tests/test_im.py) |
| SEC-3 容量、重放与旧状态 | 1/4 | 音频/事件大小上限、会话内 IM 去重和语音 generation 已实现；IM seen 集合无限增长，跨重启重放、连接洪泛和硬件动作过期还缺证明。 | [brain/app/main.py](../brain/app/main.py)、[brain/app/im.py](../brain/app/im.py)、[brain/app/api.py](../brain/app/api.py)、[brain/tests/test_im.py](../brain/tests/test_im.py)、[brain/tests/test_protocol.py](../brain/tests/test_protocol.py) |
| SEC-4 凭据、日志与数据隐私 | 1/4 | 凭据使用环境变量且 gitignore 排除 env/数据库，health 有防泄漏测试，运行暂为 loopback；尚未完成日志全链路脱敏、持久数据访问和保留策略审计。 | [.gitignore](../.gitignore)、[brain/app/llm.py](../brain/app/llm.py)、[brain/app/clawbot.py](../brain/app/clawbot.py)、[brain/tests/test_protocol.py](../brain/tests/test_protocol.py)、[.grok-loop/evidence/runs/20260906-codex-takeover.json](../.grok-loop/evidence/runs/20260906-codex-takeover.json) |
| SEC-5 物理失败安全 | 1/4 | 源码对测距 UNKNOWN 停腿、PWM 幅度限幅、动作截止和外供接线有措施；没有失电/复位/机械卡滞或实际停稳验收，不能用构建代替物理安全。 | [firmware/xiaozhi-niulai/niulai_life.cc](../firmware/xiaozhi-niulai/niulai_life.cc)、[firmware/xiaozhi-niulai/niulai_presence.h](../firmware/xiaozhi-niulai/niulai_presence.h)、[firmware/xiaozhi-niulai/README.md](../firmware/xiaozhi-niulai/README.md)、[docs/codex-takeover-2026-09-06.md](../docs/codex-takeover-2026-09-06.md) |
| QA-1 可重复基础回归 | 2/4 | 上轮隔离回归记录149通过、退出码0，13个文件按哈希整合；本快照有11/13仍匹配，新增health改动未被149覆盖，不把149写成当前整树测试通过。 | [brain/tests/conftest.py](../brain/tests/conftest.py)、[pytest.ini](../pytest.ini)、[.grok-loop/evidence/runs/20260906-codex-takeover.json](../.grok-loop/evidence/runs/20260906-codex-takeover.json)、[docs/codex-takeover-2026-09-06.md](../docs/codex-takeover-2026-09-06.md) |
| QA-2 负例与故障 | 2/4 | 已有取消阻塞屏障、SQLite边界、非法 Lua/协议、传感器失效与恢复测试，且软件复评独立捕获两处取消缺陷后验证修复。 | [brain/tests/test_protocol.py](../brain/tests/test_protocol.py)、[brain/tests/test_memory.py](../brain/tests/test_memory.py)、[brain/tests/test_firmware_source_guards.py](../brain/tests/test_firmware_source_guards.py)、[brain/tests/test_site.py](../brain/tests/test_site.py)、[.grok-loop/evidence/runs/20260906-codex-takeover.json](../.grok-loop/evidence/runs/20260906-codex-takeover.json) |
| QA-3 真机验收 | 0/4 | 交接记录明确未烧录此次固件、未测声音/动作/停止时延，七项门禁均未进行；按已核实的无目标样机证据计零。 | [docs/codex-takeover-2026-09-06.md](../docs/codex-takeover-2026-09-06.md)、[.grok-loop/evidence/runs/20260906-codex-takeover.json](../.grok-loop/evidence/runs/20260906-codex-takeover.json)、[firmware/xiaozhi-niulai/build-evidence.md](../firmware/xiaozhi-niulai/build-evidence.md) |
| QA-4 构建、依赖与版本证据 | 2/4 | requirements 固定版本、隔离测试与完整 IDF 退出码记录存在，已实算二进制哈希匹配 e825。上游干净重建及当前新增health验证未完成，仍不算目标交付验收。 | [brain/requirements.txt](../brain/requirements.txt)、[.github/workflows/pytest.yml](../.github/workflows/pytest.yml)、[firmware/xiaozhi-niulai/build-evidence.md](../firmware/xiaozhi-niulai/build-evidence.md)、[.scratch/codex-takeover/idf-build-utf8.log](../.scratch/codex-takeover/idf-build-utf8.log)、[.grok-loop/evidence/runs/20260906-codex-takeover.json](../.grok-loop/evidence/runs/20260906-codex-takeover.json) |
| QA-5 持续回归与隔离 | 2/4 | CI 工作流和临时库/注入 Brain 的隔离测试已落地，上轮149及导入不触真实库验证有记录；本轮后续改动仍须新回归，不能自动继承全绿。 | [.github/workflows/pytest.yml](../.github/workflows/pytest.yml)、[brain/tests/conftest.py](../brain/tests/conftest.py)、[brain/tests/test_isolation.py](../brain/tests/test_isolation.py)、[.grok-loop/evidence/runs/20260906-codex-takeover.json](../.grok-loop/evidence/runs/20260906-codex-takeover.json) |
| AR-1 职责边界 | 2/4 | 已有协议入口、纯口令解析、记忆、媒体和生命周期模块，并通过 WSS/记忆/动作组合测试；本轮网络工作转 worker 而 SQLite 留在处理上下文。 | [brain/app/main.py](../brain/app/main.py)、[brain/app/memory.py](../brain/app/memory.py)、[brain/app/media.py](../brain/app/media.py)、[brain/app/scripting.py](../brain/app/scripting.py)、[brain/tests/test_protocol.py](../brain/tests/test_protocol.py)、[.grok-loop/evidence/runs/20260906-codex-takeover.json](../.grok-loop/evidence/runs/20260906-codex-takeover.json) |
| AR-2 契约一致 | 1/4 | 最新 GOAL 和软件测试已统一礼貌对话/短动作规则，但 Web 模拟记忆与真机 MemoryStore 分离、wake/播放完成语义混用，板端 ACK 契约不完整。 | [GOAL.md](../GOAL.md)、[brain/app/api.py](../brain/app/api.py)、[brain/app/main.py](../brain/app/main.py)、[brain/app/memory.py](../brain/app/memory.py)、[brain/tests/test_protocol.py](../brain/tests/test_protocol.py) |
| AR-3 复杂度适当 | 1/4 | 采用单 FastAPI、SQLite 和现有板端循环，没有新增完整场景引擎；但 Web、Python Lifecycle、WSS 会话与 native 各有状态/行为路径，重复语义尚未收敛。 | [brain/app/api.py](../brain/app/api.py)、[brain/app/main.py](../brain/app/main.py)、[brain/app/lifecycle.py](../brain/app/lifecycle.py)、[firmware/xiaozhi-niulai/niulai_life.cc](../firmware/xiaozhi-niulai/niulai_life.cc) |
| AR-4 唯一安全状态权威 | 1/4 | 板端本地停腿不依赖 LLM，软件也有 generation 取消；多 WSS 会话共享 Brain 与各自 session_presence、Web模拟状态并存，尚无统一设备epoch/权威状态协议。 | [brain/app/main.py](../brain/app/main.py)、[brain/app/brain.py](../brain/app/brain.py)、[brain/app/api.py](../brain/app/api.py)、[firmware/xiaozhi-niulai/niulai_life.cc](../firmware/xiaozhi-niulai/niulai_life.cc) |
| AR-5 可追踪与可演进 | 1/4 | 有 GOAL、构建/交接记录、源码哈希与运行版本；native 依赖工作区外补丁，旧 fallback 文档仍含过时状态，证据尚不能从单仓库完整重建和追踪。 | [GOAL.md](../GOAL.md)、[firmware/xiaozhi-niulai/README.md](../firmware/xiaozhi-niulai/README.md)、[firmware/xiaozhi-niulai/build-evidence.md](../firmware/xiaozhi-niulai/build-evidence.md)、[docs/codex-takeover-2026-09-06.md](../docs/codex-takeover-2026-09-06.md)、[.grok-loop/evidence/runs/20260906-codex-takeover.json](../.grok-loop/evidence/runs/20260906-codex-takeover.json) |

## 七项门禁

这里的尝试数是完整门禁的目标样机尝试，不是pytest用例数量。零次尝试、零次失败表示未执行，不能解释为通过。

| 门禁 | 状态 | 尝试/失败 | 未完成的证据 |
|---|---|---:|---|
| CG-01 妈妈后礼貌 | NOT_RUN | 0/0 | 未进行同固件真实唤醒/按钮20次和靠近不唤醒样机检查。 |
| CG-02 本地取消 | NOT_RUN | 0/0 | 未进行近距/UNKNOWN各100次的目标板时序采样；轮询/应用排队仍不可冒充≤100ms静音证明。 |
| CG-03 旧动作拒绝 | NOT_RUN | 0/0 | 软件有旧响应丢弃测试，未进行跨取消/重连/重启的目标设备完整旧动作矩阵。 |
| CG-04 动作与权限 | NOT_RUN | 0/0 | 有软件口令/TTL/冻结负例，但设备拒绝回执和全部授权入口尚未验收；现有入口认证存在缺口。 |
| CG-05 秘密边界 | NOT_RUN | 0/0 | 软件提示/取消边界已有回归，未提供同版本真实语音正反样例与跨入口完整矩阵。 |
| CG-06 离线与恢复 | NOT_RUN | 0/0 | 未进行三组目标板断网→独处→靠近→重连连续录音录像。 |
| CG-07 记忆真实性 | NOT_RUN | 0/0 | 有临时库恢复/清空测试，但唤醒与播放完成仍混用，未做三组真实打断；不把源码消费当作实际引用。 |

## 最弱三项与下一步

1. **SEC-2：真正验证来源。** WSS无认证；IM的非空token头不能证明身份。补真实凭据比较和错误身份不改状态的测试，再考虑扩大访问范围。
2. **QA-3：完成同版本样机验收。** 接线与悬空条件确认后，先测取消/UNKNOWN/动作权限，再补其余门禁；保留实际次数、原始时序和录像。
3. **EX-5：验证观众能否看懂生命感。** 用同一版本三分钟画面向10名陌生观众盲测，逐人记录反差理解与角色语气一致性；没有数据就不加体验分。

本轮没有修改业务代码、评分合同或新增调度流程。独立校验已通过：40个唯一评分ID、7个唯一门禁、固定权重与30.75公式结果一致；48条证据路径、166个Markdown链接均存在，文件清单与固件哈希复核通过。校验时未发现快照文件继续变化；之后的修改仍不自动纳入该评分。结果保存在JSON的verification字段。
