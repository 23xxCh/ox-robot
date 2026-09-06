# 牛来：第二轮软件验证与固件修复

日期：2026-09-06。Git 基点 `91245675a2682d30e299144721cbf667761e2830`，工作区有未提交修改。本轮延续 Codex 接管，Grok 的 STOP 保留。

## 已验证的语音能力

真实配置的云端 TTS 生成了 3.36 秒语音：“终于清静了。我刚想伸个懒腰，你又回来了。”经过实际 FFmpeg Opus 编码得到 57 包，再送入真实 ASR，识别结果为“终于清静了，我刚想伸个懒腰，你又回来了。”仅标点不同。生成耗时 1.924 秒、识别耗时 2.215 秒，都是一次样本，不是延迟分位数。

- [试听 WAV](../outputs/niulai-voice-check-2026-09-06/secret-voice.wav)
- [语音链路记录](../outputs/niulai-voice-check-2026-09-06/verification.json)
- [真实 LLM 两种人格输出](../outputs/niulai-voice-check-2026-09-06/llm-check.json)

本轮修复了 `raw_opus_packets_to_ogg`：音频 granule 时间戳固定使用 48 kHz，尾部空包过滤后最后一页仍带结束标记。依据 [RFC 7845 第 4 节](https://www.rfc-editor.org/rfc/rfc7845.html#section-4)。三个输入采样率回归先失败再通过，媒体测试共 7 项通过；独立检查另用真实 FFmpeg 解码确认封装有效。没有把此前错误夸大为已经观察到的三倍播放速度问题。

以上发生在电脑与云服务之间，没有测试实体麦克风、喇叭、声画同步或观众听感。

## 后端与运行证据

最终 `brain/tests` 全量执行退出码 0，**156 passed, 1 warning in 10.37s**，包含握手修复。保留一个既有 Starlette/httpx 弃用警告。运行命令为 `python -m pytest brain/tests -o addopts='' -q --basetemp=.scratch/codex-round2/pytest-after-handshake`；日志在 `.scratch/codex-round2/pytest-final.log`。

WebSocket hello 现在只完成握手，不根据上一连接遗留的共享人格触发私语。只有本次连接收到显式 ABSENT 才开始独处发言。实际收发循环的回归先复现 hello 后泄出 4 帧，再验证 hello 静默和 ABSENT 正常 TTS 均通过。

健康接口修复了把人工版本号当成 Git commit 的问题。现在返回实际 Git commit、启动时工作区是否修改、明确的固件源码哈希，以及 `firmware_runtime_verified: false`。启动时读取一次元信息，不在每次健康请求运行 Git。

本轮替换了 Codex 自己启动的本地服务，最终版本 `codex-c73d1a0ca59e`。实际 HTTP 首页、人格页、脚本及状态接口均返回 200；WebSocket Opus hello 和 UNKNOWN 后静默检查通过。服务仍绑定 `127.0.0.1:8000`；PID、日志及验证记录在 `.scratch/codex-round2/`。当前 WLAN 为 `192.168.18.144`，旧 `192.168.10.95` 已过时；修改固件中的地址不等于板子已连接。

## 固件修复与独立复核

移除妈妈流程中的 `vTaskDelay(2200)`，改用现有 ESP 定时事件；保持至少 2.2 秒和音频排空两项条件，重复唤醒合并。靠近、UNKNOWN、取消、断网和协议关闭使待续失效。六类排队的云回复检查允许状态与 generation，取消及重新启用时分别使旧批次失效；正常 VAD 停止录音继续接受本次回复，SECRET 心跳保留当前会话。

独立复核先发现并修复了 WS 关闭遗漏、旧 TTS 混入、VAD 被误当成取消、握手期间排队回复复活四处问题，最终给出 PASS。可运行检查抽取实际 C++ 状态及停止/启用函数体，验证时间与排空、重复唤醒、取消恢复、普通 VAD 回复及握手边界。它不能代替实际 FreeRTOS 调度和物理时间测量。

补丁 [application-intro-2026-09-06.patch](../firmware/xiaozhi-niulai/application-intro-2026-09-06.patch)已从保存的本轮前置源码成功还原两个候选文件，逐字节 SHA256 一致；检查保存在 [check_application_intro.py](../firmware/xiaozhi-niulai/check_application_intro.py)。补丁只覆盖本轮增量，依赖 `.scratch/codex-round2/native-before/` 对应基线，尚未固定完整外部小智上游和既有挂钩，不能宣称干净上游可重建。

剩余阻塞点包括 `PlaySound` 队列背压和同步 WebSocket 打开；generation 能拒绝已捕获旧批次的回调，尚无协议级标识用于辨认所有网络迟到的旧数据。因此不宣称 ≤100ms 停止或端到端旧消息隔离已验收。

完整 IDF 构建于 10:33 成功，退出码 0。新应用镜像 **2,804,672 字节**，SHA256 `f1275bf9ea427dde4c7f28ac77bf304102949fe070cb22a83c52c8ab3f5a900d`，已保存为 [xiaozhi.bin](../outputs/niulai-codex-round2-2026-09-06/xiaozhi.bin)。[构建记录](../firmware/xiaozhi-niulai/build-evidence.md)包含合并镜像及源码哈希。本轮原始证据汇总在 [20260906-codex-round2.json](../.grok-loop/evidence/runs/20260906-codex-round2.json)。

## 产品评分与下一优先级

[完整审计报告](score-review-2026-09-06.md)按固定 40 项、8 个维度及 7 项门禁建立首份可审计基线：**30.75/100**。它固定在 10:14 的受审快照，未把本轮后续语音、服务启动及固件修改混入得分。历史 37.75 只有不完整汇总，不能据此声称本轮涨分或降分。

下一步优先修复真实入口鉴权、完成真机验收、校正“唤醒”与“妈妈实际播放完成”的记忆事件语义。产品 PRD 和 spec 继续沿用现有文档，以最新 GOAL 规则为准，不另起一套产品。

真机接线和四腿悬空固定尚未获得确认。本轮不打开串口、不烧录、不下发实体动作；七项真机门禁仍为 NOT_RUN。
