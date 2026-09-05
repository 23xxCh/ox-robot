# 「牛来」ESP-Claw + AI 小智双节点系统架构

**文档版本：** 2.0 Proposal  
**日期：** 2026-09-01  
**适用范围：** AIX ORIGIN 硬件黑客松 P0 原型  
**状态：** 推荐方案；需通过双板与电源物料门禁后冻结  
**覆盖关系：** 本文针对“必须真实使用 ESP-Claw 与 AI 小智”的新要求，覆盖 `architecture-niulai-robot-2026-08-31.md` 中的单板运行时选择；原文的安全、机械、电源和测试要求继续有效。

## 1. 结论

黑客松版本采用：

> **两块 ESP32-S3、两个独立固件、一个人格状态源、一条本地语义链路、一个独立硬件安全边界。**

- **AI 小智语音节点**负责听、说、实时语音会话和公开对话。
- **ESP-Claw 生命控制节点**负责人格状态、秘密活动、记忆、动作编排、传感器和身体控制。
- **ESP-Claw 控制节点是人格与身体的唯一权威。** 小智只有语音会话状态，不得自行改变人格或直接控制执行器。
- 两板通过短线 3.3 V UART 交换有版本、序号、TTL、`persona_epoch` 和 CRC 的语义事件；不通过板间链路传输原始音频、PWM、轮速或舵机角度。
- 人员检测、避障、低电、动作租约、急停和最终执行器裁决全部留在 ESP-Claw 控制板和硬件侧，绝不依赖 UART、Wi-Fi、云端或 LLM。
- 另设一根由控制板直接控制的小智功放 `AMP_MUTE/EN` 硬件线；发现人、状态未知或急停时可立即静音，不等待语音软件响应。

不采用：把 ESP-Claw 与 xiaozhi-esp32 两套完整固件硬合并到同一颗 ESP32-S3。

## 2. 架构驱动

### 2.1 功能驱动

1. 无人时，牛来秘密活动、观察、吐槽并留下轻量记忆。
2. 发现人或无法确认人员状态时，立即装死并清除私密动作与语音。
3. 听到“牛来”后，从装死状态公开复活，先回答本地“妈妈”，再允许公开语音互动。
4. ESP-Claw 必须真实参与 Event、Memory、Capability/Lua 和行为编排。
5. AI 小智必须真实参与本地唤醒/音频链路和至少一次 ASR→LLM→TTS 公开对话。
6. 核心三分钟故事在断网时仍可完成；云端只增加内容丰富度。

### 2.2 非功能驱动

| ID | 要求 | 架构响应 |
|---|---|---|
| NFR-SAFE-001 | 非安全模块不得直写执行器 | 控制板 C/C++ Safety Supervisor 与私有 HAL 拥有最终权限 |
| NFR-RT-001 | `PRESENT/UNKNOWN` 到运动撤销不超过 300 ms | 人员传感、安全裁决和电机停止均在控制板本地短路径 |
| NFR-OFFLINE-001 | 断网仍完成核心故事 | 本地 KWS/按钮、本地“妈妈”、本地台词和本地动作 |
| NFR-REL-001 | 重启、断链、超时默认安全 | 握手前 `BOOT_SAFE`；动作租约；链路看门狗；STBY 下拉 |
| NFR-DEMO-001 | 三分钟 Demo 连续 10 次通过 | 冻结版本、离线兜底、场景回放和双板故障注入 |
| NFR-AUDIO-001 | 电机/扬声器不破坏语音 | 语音与执行器分板、分电源域、星形接地、P0 半双工优先 |
| NFR-DEV-001 | 三人短周期可并行 | 语音、生命控制、机械电源三条工作流由 UART 契约解耦 |

## 3. 方案比较

| 方案 | 是否真实使用两套系统 | 黑客松风险 | 判断 |
|---|---:|---:|---|
| 一颗 S3 合并两套完整固件 | 是 | 极高 | 拒绝；IDF、入口、分区、NVS、网络、音频任务和内存模型冲突 |
| 两块 S3，UART 语义互联 | 是 | 最低 | **P0 推荐**；边界清楚，可独立刷写与故障定位 |
| 小智为主，只移植 ESP-Claw 思想/组件 | 部分 | 中 | 未来单板产品路线；不能宣称 P0 运行完整 ESP-Claw |
| ESP-Claw 单板 + PC 模拟小智语音网关 | 部分 | 中 | 双板缺货时救场；玩具依赖 PC，演示独立性较弱 |

### 3.1 架构模式（Architecture Pattern）

本方案是一个**双节点、事件驱动、分层的嵌入式系统**：每块板内部保持模块化单体，板间只通过有类型的语义事件协作。它不是微服务架构，也不是两个 Agent 对等争抢控制权。

- **语音平面：** 小智节点处理实时音频和公开对话。
- **生命平面：** ESP-Claw 节点处理人格、记忆、环境事件和行为编排。
- **安全平面：** 控制板上的固定规则与硬件链路覆盖前两者，拥有最终否决权。
- **集成模式：** UART 消息合同 + 单一人格权威 + 有时限的动作/语音租约。

### 3.2 关键取舍（Trade-off Analysis）

- 用一块额外 S3、少量 BOM 和协议开发成本，换取两套上游工程可独立升级、可并行开发、可隔离故障。
- 接受 P0 体积和功耗略高，换取 Demo 阶段的可调试性；产品化后再以测量结果决定是否裁剪成单板。
- UART 不传原始音频和执行器细节，牺牲少量跨板灵活性，换取带宽确定性、权限边界和本地安全闭环。
- P0 不追求多设备横向扩展（Scalability）；只在协议中保留设备身份和版本字段，避免为尚不存在的规模提前复杂化。

## 4. 总体架构

```text
                         可选互联网 / 本地服务器
                ┌────────────────────────────────┐
                │ 小智 Server                    │
                │ ASR / 对话 LLM / TTS / MCP     │
                └───────────────┬────────────────┘
                                │ WebSocket 或 MQTT+UDP
                                ▼
┌──────────────── AI 小智语音节点 ESP32-S3 A ────────────────┐
│ Mic → Audio Codec → ESP-SR AFE → Opus → 实时语音协议       │
│        本地唤醒 / AEC / VAD          ↕                     │
│ Speaker ← Audio Output ← Opus Decode                       │
│ Voice FSM: IDLE / LISTENING / THINKING / SPEAKING / FAILED │
│ 设备 MCP：仅暴露 niu.get_state / niu.perform 等窄工具       │
└──────────────────────┬──────────────────────────────────────┘
                       │ 3.3V UART 语义协议
                       │ + AMP_MUTE/EN 硬线
                       ▼
┌──────────────── ESP-Claw 生命控制节点 ESP32-S3 B ──────────┐
│ ESP-Claw: Event Router / Memory / Skills / Capability / Lua │
│                         │ 语义 ActionIntent                 │
│                         ▼                                   │
│ Persona FSM → Action Gateway → Safety Supervisor            │
│      ▲                                  │                   │
│ Presence / Wake / Memory                 ▼                   │
│                              Motion / Servo / OLED / Audio   │
│ Presence雷达 / HC-SR04 / Battery / E-stop / Watchdog         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
           两驱电机 / 头部两轴 / 嘴巴 / 双眼 OLED

实体急停：直接切断电机与舵机执行器电源，并硬件拉低 AMP_MUTE；
控制板逻辑保持上电，用于锁存故障与记录原因。
```

### 4.1 部署与启动边界（Deployment）

- 两块板分别编译、烧录、回滚；禁止把两套完整固件在 P0 合成同一个工程。
- 上电时控制板先进入 `BOOT_SAFE`，小智板先保持扬声器静音；完成版本握手和本地自检后才允许进入人格状态。
- 小智 Server 可部署在局域网电脑或云端，但它下线不能破坏装死、复活、本地“妈妈”和运动安全。
- 发布包必须绑定小智固件版本、ESP-Claw 固件版本、板间协议版本和角色资源版本，禁止只更新一侧后直接上场。

## 5. 单一权威与双平面

### 5.1 唯一状态所有者

| 状态/资源 | 唯一权威 | 说明 |
|---|---|---|
| `persona_state`、`persona_epoch` | ESP-Claw 控制板 | 小智只能读取，不能修改 |
| 人员三态、安全状态、动作租约 | ESP-Claw 控制板 | 不跨板裁决 |
| 语音会话状态 | 小智语音板 | 控制板读取并可取消/静音 |
| 公开对话内容 | 小智 Server/LLM | 必须受控制板下发的语音策略约束 |
| 秘密行为和轻量人格记忆 | ESP-Claw 控制板 | 决定何时秘密活动、记住什么 |
| 执行器 | Safety Supervisor | 任何 Agent、Lua、MCP 只能提交意图 |

### 5.2 双平面

1. **确定性控制平面**：人员检测、装死、急停、避障、低电、动作租约、电机与舵机控制。运行在控制板 C/C++，优先级最高。
2. **创意智能体平面**：ESP-Claw 记忆、秘密行为组合、小智公开对话、云端 LLM。只产生短文本、情绪标签和白名单动作意图。

### 5.3 语音所有权租约

同一时刻只允许一个内容源说话：

| 人格状态 | 允许说话的源 | 规则 |
|---|---|---|
| `FREEZE_DETECTED` | 无 | 硬件静音；等待“牛来” |
| `PUBLIC_ALIVE` | 小智 | 公开对话；ESP-Claw 私密 Agent 暂停 |
| `SECRET_ALIVE` | ESP-Claw 或本地台词库 | 小智对话 Agent 静默，仅充当受控 TTS/播放端 |
| 任一安全停止态 | 无 | 清队列、撤销动作、硬件静音 |

控制板发出的每个语音许可都绑定 `persona_epoch` 和截止时间。状态变化后，旧 ASR、LLM、TTS 或音频结果全部丢弃。

## 6. 状态模型

不要把安全状态和人格状态混成一个枚举；采用两个正交状态机。

### 6.1 Safety FSM

```text
BOOT_SAFE ──自检通过──► NORMAL
    ▲                    │
    │ 关键状态未知/故障   ├──► SAFE_STOP
    │                    │
    └────重新握手/自检────┘

任意状态 ──实体急停──► E_STOP_LATCHED
E_STOP_LATCHED ──实体释放 + 本地重新武装──► BOOT_SAFE
```

### 6.2 Persona FSM

```text
上电默认
   ▼
FREEZE_DETECTED  ◄──────────── PRESENT / UNKNOWN
   │
   │ 连续 ABSENT 达去抖时间（建议初值 5 秒）
   ▼
SECRET_ALIVE ──发现人/状态未知──► FREEZE_DETECTED
   ▲                                  │
   │ ABSENT + 公开会话结束             │ WAKE_NIULAI
   └──────────── PUBLIC_ALIVE ◄────────┘
                         │
                         └─会话超时且仍 PRESENT → FREEZE_DETECTED
```

`MAMA_RESPONSE` 是 `PUBLIC_ALIVE` 的进入动作，不再是说完一句就退回机械人格的独立终态。

### 6.3 状态优先级

```text
实体急停
  > 硬件/供电故障
  > PRESENT 或 UNKNOWN 导致装死
  > 障碍与低电
  > 用户“牛来”公开唤醒
  > 公开对话配套动作
  > 秘密自主活动
  > LLM 建议
```

## 7. 组件设计

### 7.1 AI 小智语音节点

| 组件 | 职责 | 禁止事项 |
|---|---|---|
| `audio_service` | I²S 采集/播放、Opus 队列、音量与功放状态 | 不控制身体执行器 |
| `afe_engine` | 本地唤醒、AEC、VAD | 不判断人格 |
| `voice_fsm` | 管理监听、思考、播放、打断和故障 | 不自行从装死切到公开人格 |
| `xiaozhi_protocol` | WebSocket 或 MQTT+UDP 语音通信 | P0 只启用一种主协议 |
| `niu_uart_bridge` | 将唤醒、语音状态和 MCP 意图转换为板间消息 | 不传原始音频和底层控制值 |
| `local_audio_assets` | 离线“妈妈”和故障提示 | 仅使用审核过的 asset_id |

### 7.2 ESP-Claw 生命控制节点

| 组件 | 职责 | 禁止事项 |
|---|---|---|
| `presence_adapter` | 输出 `PRESENT/ABSENT/UNKNOWN` 和 freshness | 不把超声波当人员传感器 |
| `safety_supervisor` | 急停、人员、障碍、低电、链路和看门狗仲裁 | 不访问网络、LLM 或文件系统 |
| `persona_fsm` | 唯一人格状态与 `persona_epoch` | 不直接写 GPIO |
| `life_engine` | 情绪、能量、秘密活动和行为选择 | 不越过安全优先级 |
| `action_gateway` | 验证动作名、来源、epoch、TTL 和参数枚举 | 不接受 PWM、裸角度或无限时长 |
| `motion_controller` | 有限速度、有限时长、动作租约与停止 | 链路断开后不延续旧动作 |
| `servo/display_controller` | 命名姿态和预设表情 | 不越机械限位 |
| `espclaw_bridge` | Event、Memory、Capability、Lua 接入 | Agent/Lua 不拥有最终执行权 |
| `niu_uart_link` | 板间握手、心跳、幂等、ACK 和故障统计 | 不能把链路故障解释成 ABSENT |

### 7.3 ESP-Claw 的最小真实使用证明

P0 至少满足：

1. `WAKE_DETECTED`、`PRESENT`、`ABSENT` 等进入 ESP-Claw Event Router。
2. Memory 保存至少一个会改变后续表现的字段，例如 `forced_mama_count`。
3. 一个 Skill/Lua 编排至少三种秘密行为，例如环顾、眨眼、低声吐槽。
4. 一个 Capability 通过 Action Gateway 请求命名动作。
5. Agent 超时或崩溃不会影响装死、停车和本地“妈妈”。

## 8. 板间接口

### 8.1 物理层

- 3.3 V TTL UART，全双工，短线，共地。
- 建议 460800 baud，8N1；线束较长或噪声严重时降速并复测。
- P0 不用 Wi-Fi/MQTT 作为板间安全链路。
- 增加独立 `AMP_MUTE/EN` 线，默认下拉为静音。

### 8.2 帧格式

采用 `COBS + 固定头 + 紧凑 JSON Payload + CRC32`，最大帧 512 B。

```text
protocol_version
sender_boot_id
message_type
seq
correlation_id
persona_epoch
ttl_ms
payload_length
payload
crc32
```

规则：

- 接收端使用自己的单调时钟判断 TTL，不依赖网络时间。
- `boot_id + seq` 识别重启、重复和乱序。
- 一次性动作使用 `correlation_id` 幂等；重发不得重复执行。
- 未知版本、CRC 错误、超长帧和未知动作全部拒绝并计数。
- 队列有界；拥塞先丢遥测，不能丢 `CANCEL_AUDIO`、状态和故障消息。
- 链路只传语义事件；不传 PCM、Opus、任意 URL、PWM、轮速和裸舵机角度。

### 8.3 消息合同

#### 小智 → 控制板

| 类型 | 关键字段 | 用途 |
|---|---|---|
| `HELLO` | version、firmware、capabilities、boot_id | 握手与能力协商 |
| `HEARTBEAT` | voice_state、heap、faults | 链路健康 |
| `WAKE_DETECTED` | source、confidence、session_id | 统一映射为 `WAKE_NIULAI` |
| `VOICE_STATE` | IDLE/LISTENING/THINKING/SPEAKING/FAILED | 同步会话状态 |
| `ACTION_REQUEST` | action、enum_params、ttl、epoch、action_id | 小智 MCP 高层动作请求 |
| `PLAYBACK_EVENT` | started/ended/cancelled/failed、session_id | 嘴部/表情有限联动 |
| `AUDIO_FAULT` | reason | 声学链路降级 |
| `CLOUD_FAULT` | reason | 退回本地交互 |

#### 控制板 → 小智

| 类型 | 关键字段 | 用途 |
|---|---|---|
| `HELLO_ACK` | accepted_version、boot_id | 建立会话 |
| `AUTHORITATIVE_STATE` | safety、presence、persona、epoch | 唯一权威状态 |
| `VOICE_POLICY` | listen、cloud、mute、max_volume、epoch | 控制是否能听/说 |
| `PLAY_LOCAL_ASSET` | asset_id、epoch、deadline | 离线“妈妈”等固定音频 |
| `SPEAK_REQUEST` | filtered_text、epoch、deadline | P1 秘密台词 TTS |
| `CANCEL_AUDIO` | epoch、reason | 清除迟到或私密音频 |
| `ACTION_RESULT` | action_id、accepted/rejected/done/cancelled、reason | 动作反馈 |
| `LINK_POLICY` | normal/degraded | 降级策略 |

### 8.4 超时与失败安全

| 项目 | 建议初值 | 失败行为 |
|---|---:|---|
| 心跳周期 | 200 ms | 仅健康同步 |
| 心跳可疑 | 400 ms | 禁止新的跨板动作 |
| 链路失效 | 600 ms | 取消小智来源动作并停车；不自动恢复旧动作 |
| 普通 ACK | 100 ms | 只重试一次，随后降级 |
| `WAKE_DETECTED` 新鲜度 | 500 ms | 过期丢弃 |
| `CANCEL_AUDIO` | 50 ms | 未确认时保持硬件 MUTE |
| 运动续租 | 50 ms | 连续 100 ms 未续租即停车 |
| 动态语音总截止 | 5 s | 丢弃并使用本地资源 |

链路恢复稳定 2 秒后才允许重新启用跨板功能，且不得恢复断线前的动作或语音。

## 9. 关键数据流

### 9.1 被发现后装死

```text
毫米波 PRESENT/UNKNOWN
  → Safety Supervisor（本地）
  → 撤销动作租约 + 电机停车 + 舵机回安全姿态
  → Persona = FREEZE_DETECTED，epoch++
  → AMP_MUTE 硬件拉低
  → UART CANCEL_AUDIO（异步确认）
  → 清除私密台词、表情和动作队列
```

该路径不经过 ESP-Claw Agent、小智、UART、Wi-Fi 或 LLM 才能完成停车。

### 9.2 “牛来”公开复活

```text
小智本地 KWS 检测“牛来”
  → WAKE_DETECTED(session_id)
  → 控制板设置 PRESENT hold，Persona = PUBLIC_ALIVE，epoch++
  → 眼睛/头/嘴进入公开复活动作
  → PLAY_LOCAL_ASSET("mama")
  → 小智播放本地“妈妈”
  → 允许公开语音会话
```

隐藏按钮产生同一个 `WAKE_NIULAI` 事件作为演示兜底，但真实语音验收必须单独记录。

### 9.3 公开对话与动作

```text
Mic → 小智 AFE/Opus → ASR/LLM/TTS → Speaker
                         │
                         └─ MCP niu.perform("happy_nod")
                              → UART ACTION_REQUEST
                              → Action Gateway
                              → Safety Supervisor
                              → 命名姿态
```

MCP 工具只等待“已接受/已拒绝”，不阻塞到动作完全结束。

### 9.4 无人秘密活动

```text
连续 ABSENT 达去抖时间
  → Persona = SECRET_ALIVE，epoch++
  → 小智公开对话 Agent 静默
  → ESP-Claw Event/Memory/Skill 选择秘密行为
  → ActionIntent → Action Gateway → Safety Supervisor
  → 短动作 + 本地台词/受控 TTS
```

任何 `PRESENT/UNKNOWN` 都抢占以上流程。

## 10. 数据模型

| 实体 | 关键字段 | 所有者/存储 |
|---|---|---|
| `AuthoritativeState` | safety、presence、persona、epoch、entered_ms | 控制板 RAM |
| `VoiceSession` | session_id、state、started_ms、last_update_ms | 小智板 RAM |
| `BehaviorMemory` | forced_mama_count、curiosity、energy、recent_behavior_ids | ESP-Claw Memory/FATFS；P0 可会话级 |
| `ActionIntent` | source、action、params、epoch、ttl、action_id | 控制板有界队列 |
| `ActionLease` | action_id、allowed_action、expires_ms、cancel_reason | 控制板 RAM |
| `LinkPeer` | boot_id、last_seq、last_heartbeat、capabilities、error_counts | 两板 RAM |
| `AudioAsset` | asset_id、hash、duration、content_class | 小智板只读 Flash/assets |
| `EventLog` | seq、monotonic_ms、source、type、state、reason、correlation_id | 两板串口 JSONL + RAM ring |

P0 不持久化原始麦克风音频、照片或长期身份数据。

## 11. 安全、隐私与权限

### 11.1 永远留在控制板/硬件的能力

- 实体急停与重新武装。
- 人员三态融合与 freshness。
- 障碍、低电、过流/温升和 Brownout 处置。
- 电机 PWM、STBY/EN、舵机 PWM 与机械限位。
- 动作租约、限速、限时、停止距离和最终人格状态。
- 是否允许说话、移动或重新开始公开会话的最终决定。

### 11.2 LLM 允许与禁止

LLM 只允许：

- 生成短台词和情绪标签。
- 提议枚举的高层动作。
- 读取有限、脱敏、非安全关键的上下文。

LLM 禁止：

- 输出 PWM、轮速、舵机角度或无限时长动作。
- 修改安全阈值、判断人员存在或解除急停。
- 创建任意 URL、下载 Lua 或恢复过期动作。
- 让旧 epoch 的迟到结果重新发声或运动。

### 11.3 密钥与数据

- Provider 密钥保存在小智 Server/本地网关，不进入固件仓库和串口日志。
- 控制板不开放未鉴权的局域网控制面；P0 优先只保留 UART 与 USB 调试。
- 原始语音是否上传需在现场明确提示；P0 不落盘原始语音。

## 12. 电源与物理设计

```text
2S 带保护电池
  ├─ 逻辑稳压 ── ESP-Claw 控制板 + 传感器 + OLED
  ├─ 语音/功放稳压 ── 小智板 + Codec + Amp + Speaker
  ├─ 急停链路 ── 电机稳压 ── H桥 ── 两驱电机
  └─ 急停链路 ── 舵机稳压 ── 头部/嘴部舵机
```

- 所有电源域星形共地；电机和舵机回流不得穿过麦克风/Codec 地路径。
- 小智板、麦克风和 Codec 远离 H 桥、电机线和降压电感。
- `AMP_MUTE/EN` 默认静音；由控制板与急停硬件共同约束。
- P0 语音窗口优先暂停轮子和非必要舵机；全双工 AEC 作为增强，不设为核心门禁。

## 13. NFR 验证矩阵

| NFR | 验证方法 | 通过标准 |
|---|---|---|
| 人员抢占 | `SECRET_ALIVE` 移动中注入 PRESENT/UNKNOWN | 控制命令撤销 ≤300 ms；不继续私密语音 |
| 板间断链 | 运行中拔 UART TX/RX、重启任一板 | 停车、静音、不恢复旧动作 |
| 重复/乱序 | 重放同一 action_id、乱序 seq、旧 epoch | 不重复执行；全部拒绝并记录 |
| 急停 | 移动、舵机和播音中按下 | 执行器断能、功放静音、只能本地重新武装 |
| 离线 | 关闭外网和小智 Server | 完成秘密活动、装死、按钮/本地唤醒、本地“妈妈”和安全闭环 |
| 语音 | 约定距离/噪声下说“牛来”20次 | 至少18次 `source=voice` 命中；按钮结果分开统计 |
| MCP越权 | 请求原始 PWM、越界参数、旧 epoch | 100% 拒绝且无执行器输出 |
| 声学/电源 | 最大音量、电机启停、舵机组合 | 无 Brownout；KWS/录音达到约定指标 |
| Demo | 冻结版本连续演出 | 10次三分钟无死机、撞击、倾倒或人格穿帮 |

## 14. 技术栈与版本策略

| 节点 | 技术 | 决策 |
|---|---|---|
| 小智语音板 | `78/xiaozhi-esp32` | 选择有 AEC 音频硬件支持的已验证板型；固定 tag/SHA 与对应 ESP-IDF |
| 生命控制板 | `espressif/esp-claw` `application/edge_agent` | 从 `eda_robot_pro` 派生 `niu_robot`；固定 tag/SHA 与其已验证 ESP-IDF |
| 控制与安全 | C/C++ + FreeRTOS | 最高优先级、固定内存、有界队列 |
| 创意行为 | ESP-Claw Event/Memory/Capability/Lua | 仅高层语义和低频异步行为 |
| 板间协议 | UART + COBS + JSON + CRC32 | 简单可抓包，支持版本/幂等/TTL |
| 云端语音 | 小智 Server | P0 只选一套 Server 与一种主传输协议 |
| 机械 | FreeCAD 参数化骨架 + 生成式外壳 | 外观不承担承力与孔位基准 |

两块板允许分别冻结各自已验证的 ESP-IDF，不要求为了“统一版本”强行升级或回退。

## 15. 团队分工

| 工作流 | 负责人 | 首要产出 |
|---|---|---|
| 小智语音节点 | 计算机成员 A | 独立唤醒/对话/TTS、UART Bridge、一个 MCP 工具 |
| ESP-Claw生命与安全 | 计算机成员 B | Persona/Safety FSM、Event/Memory/Lua、动作白名单、UART Link |
| 机械、电源与装配 | 智能制造成员 | 电源分域、急停、底盘/头部结构、噪声与负载测试 |

三条工作流开始前必须先冻结：UART 消息 ID、人格状态、动作枚举、电源接口、结构坐标基准和责任边界。

## 16. 实施门禁

| Gate | 通过条件 | 失败处理 |
|---|---|---|
| G0 双板物料 | 两块兼容 S3、音频板/Codec、控制板、电源域可用 | 启用单板+PC救场方案，不宣称双固件已运行 |
| G1 独立基线 | 两个上游固件各自 build/flash/boot | 不进入集成；锁定各自工具链 |
| G2 UART 合同 | HELLO、心跳、重启、CRC、ACK、旧 epoch 测试通过 | 仅用 Mock，不接执行器 |
| G3 安全身体 | 假负载移动、避障、急停、静音、无 Brownout | 不装正式外壳 |
| G4 离线故事 | SECRET→FREEZE→PUBLIC 状态机和本地“妈妈”通过 | 不接云端 LLM |
| G5 小智真实语音 | 真实麦克风唤醒、一次公开问答、一个 MCP 动作 | 按钮仅作兜底，语音失败如实标注 |
| G6 双板故障 | 断链、任一板重启、云端超时、旧结果注入通过 | 保持离线 P0 |
| G7 整机冻结 | 10次三分钟 Demo + 30分钟电源/热测试 | 回退最近稳定版本 |

## 17. P0、P1 与产品化边界

### P0 必须

- 双板握手、心跳和失败安全。
- `SECRET_ALIVE / FREEZE_DETECTED / PUBLIC_ALIVE` 故事闭环。
- ESP-Claw 三种秘密行为、一次有效记忆和一个受控 Capability/Lua 动作。
- 小智真实唤醒、一次开放问答、一次 TTS 和一个 MCP 高层动作。
- 人员出现 300 ms 内撤销运动并硬件静音。
- 断网仍能装死、复活、播放“妈妈”和安全移动。

### P1 增强

- AEC 全双工打断、秘密动态 TTS、情绪变量和记忆同步。
- 更完整的板间追踪、日志导出和资源监控。
- 更多表情/动作，但不增加底层动作权限。

### 不进入黑客松 P0

- 两套完整固件单板合并。
- 摄像头、SLAM、开放区域导航和悬崖边运行。
- 长期原始音频、照片、身份识别和 SD 日记。
- App、账户、量产 OTA、远程解除急停。
- LLM 直接控制执行器。

### 产品化演进

双板完成真实测量后，再以小智语音固件为主，迁入已经验证的 Persona FSM、Action Gateway、Event Router 和轻量记忆，评估是否保留完整 ESP-Claw Runtime。单板化是重构，不是把两个应用目录拼接。

## 18. 架构决策记录

### ADR-201：P0 采用双板而非单板融合

**决定：** 两块 ESP32-S3 分别运行小智和 ESP-Claw。  
**原因：** 隔离音频/Agent资源、允许各自固定工具链、便于三人并行和故障定位。  
**代价：** 增加一块板、电源预算和 UART 协议。  
**重新评审：** 双板 P0 完成，且单板 RAM/CPU/DMA/Flash/功耗实测有余量。

### ADR-202：ESP-Claw 控制板是唯一人格与身体权威

**决定：** 小智只拥有语音会话状态。  
**原因：** 避免两个 LLM、两个状态机争夺角色和动作。  
**代价：** 需要 `VOICE_POLICY` 与 `persona_epoch` 协调迟到结果。

### ADR-203：UART 是语义链路，不是远程执行器总线

**决定：** 只传事件、策略和白名单动作。  
**原因：** 控制板必须能独立判定安全并拒绝过期或越权命令。  
**代价：** 需要定义协议版本、幂等、TTL 和故障测试。

### ADR-204：装死与静音使用本地短路径

**决定：** 人员事件直接撤销运动，并通过硬线静音。  
**原因：** UART、小智任务或云端卡死时仍不能穿帮。  
**代价：** 增加一根控制线和功放默认态设计。

### ADR-205：云端只增强，不承载核心故事

**决定：** 本地资源完成最小叙事。  
**原因：** 比赛网络不可控。  
**代价：** P0 需要维护少量审核过的本地语音和台词。

## 19. 当前未决门禁

1. 是否能拿到第二块适合小智音频链路的 ESP32-S3 板。
2. 小智板 Codec、麦克风、功放和 AEC 参考通道是否真实可用。
3. 24 GHz 雷达具体型号、接口和 freshness 判据。
4. 电机堵转电流、最终重量和驱动热设计。
5. 电池、稳压和功放峰值下的完整功耗预算。
6. “牛来”自定义 KWS 在现场噪声下是否达到 18/20。

这些门禁不阻塞 Persona FSM、UART Mock、动作白名单、ESP-Claw Event/Memory 和桌面场景测试。

## 20. 官方参考

- [ESP-Claw](https://github.com/espressif/esp-claw)
- [xiaozhi-esp32](https://github.com/78/xiaozhi-esp32)
- [小智 WebSocket 协议](https://github.com/78/xiaozhi-esp32/blob/main/docs/websocket_zh.md)
- [小智 MCP 协议](https://github.com/78/xiaozhi-esp32/blob/main/docs/mcp-protocol_zh.md)
- [ESP-SR](https://github.com/espressif/esp-sr)

## 文档历史

| 版本 | 日期 | 说明 |
|---|---|---|
| 2.0 Proposal | 2026-09-01 | 按“必须基于 ESP-Claw + AI 小智”重构为双节点架构；加入 PUBLIC_ALIVE、单一人格权威、UART 合同、硬件静音和双板 NFR |
