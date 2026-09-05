# 「牛来」双人格自主机器人系统架构

**文档版本：** 1.0  
**日期：** 2026-08-31  
**作者：** System Architect  
**状态：** Review（软件架构可冻结；电机、驱动、电池、雷达和舵机型号待实物门禁）

---

## 目录

1. [系统概述](#1-系统概述)
2. [需求与架构驱动](#2-需求与架构驱动)
3. [架构模式](#3-架构模式)
4. [总体架构](#4-总体架构)
5. [硬件与机械架构](#5-硬件与机械架构)
6. [设备端组件设计](#6-设备端组件设计)
7. [状态机与关键数据流](#7-状态机与关键数据流)
8. [接口与 API 规范](#8-接口与-api-规范)
9. [数据模型与存储](#9-数据模型与存储)
10. [技术栈选型](#10-技术栈选型)
11. [非功能需求映射](#11-非功能需求映射)
12. [安全、故障与降级设计](#12-安全故障与降级设计)
13. [开发、测试与 Vibe Coding 工作流](#13-开发测试与-vibe-coding-工作流)
14. [部署架构](#14-部署架构)
15. [架构决策与取舍](#15-架构决策与取舍)
16. [团队分工与实施门禁](#16-团队分工与实施门禁)
17. [未来演进](#17-未来演进)

---

## 1. 系统概述

### 1.1 目的

“牛来”是一只约 360 mm 高、可在室内平地自主移动的硬壳拟人牛机器人。产品核心不是通用对话，而是可被现场观众立即理解的双人格表演：

- **有人时**故意扮演迟钝机械牛；听到“牛来”后回答“妈妈”。
- **确认无人时**恢复有灵魂的本性，自言自语、轻度吐槽并安全游荡。
- **检测到人、传感器不确定或故障时**立即停止私密内容和自由移动，回到机械人格。

### 1.2 范围

**P0 范围：**

- 两驱移动、转向、停车、前向避障和实体急停。
- `PRESENT / ABSENT / UNKNOWN` 三态人员存在判断。
- 双人格状态切换及“牛来 → 妈妈”演出。
- 头部两轴、嘴巴一轴、OLED 双眼和胸口发声。
- 无人状态的有限自主动作和吐槽。
- 网络、LLM、TTS失效时的离线演示降级。
- Mock 驱动、桌面仿真、结构化日志和硬件在环测试入口。

**不在 P0：**

- Insta360 摄像头、视觉识别和持续录像。
- 手臂、尾巴运动。
- 楼梯、室外、地毯、悬崖检测和全屋导航。
- 小智与 ESP-Claw 两套完整固件融合。
- LLM 直接输出 PWM、轮速、舵机角度或任意网络 URL。
- 手机 App、量产 OTA、用户账户、云端规模化服务。
- 长期 SD 日记、多用户身份识别和照片记录。

### 1.3 利益相关者

- **现场观众/评委：** 需要三分钟内看懂反差设定，演示不能依赖解释或运气。
- **开发团队：** 2 名计算机专业成员 + 1 名智能制造工程专业成员。
- **操作者：** 必须能在任何时候通过实体急停终止动作。
- **未来用户：** 儿童、独居者、潮玩和陪伴玩具用户；量产前需要独立的儿童安全、隐私和合规评审。

### 1.4 需求源与覆盖规则

架构基于 IMA 中的《牛来机器人PRD v1.1》《技术开发决策记录》以及后续逐项确认。后续确认覆盖 PRD 的四个早期假设：

1. PIR 改为 24 GHz 毫米波存在检测。
2. 静止桌面玩具改为隐藏两驱移动机器人。
3. 物料表旧编号映射无效，必须以实物铭牌、接口和数据手册复核。
4. LLM/TTS 不再是核心演示的硬依赖。

---

## 2. 需求与架构驱动

### 2.1 功能需求

| ID | 功能 | 优先级 | 架构响应 |
|---|---|---:|---|
| FR-001 | 三态人员存在检测 | P0 | `PresenceAdapter` 统一返回三态，UNKNOWN 失败安全 |
| FR-002 | 前方障碍检测 | P0 | HC-SR04 独立于人员感知，仅进入安全层 |
| FR-003 | 实体急停与人工复位 | P0 | 物理切断执行器电源 + 软件锁存 |
| FR-004 | 双人格确定性切换 | P0 | 本地状态机拥有最终人格状态 |
| FR-005 | “牛来”事件输入 | P0 | ASR/KWS/按钮统一映射到 `WAKE_NIULAI`；最终语音验收必须来自真实麦克风，按钮只作兜底 |
| FR-006 | 本地“妈妈”响应 | P0 | 只读 Flash 音频，不依赖网络 |
| FR-007 | 无人安全游荡 | P0 | 动作租约、限速、限时、障碍门禁 |
| FR-008 | 本性人格吐槽 | P0 | 本地预审台词库保证离线演出；云端/PC动态生成作为 P1 增强并做确定性过滤 |
| FR-009 | 眼睛、头部、嘴巴和声音联动 | P0 | 命名表情与动作编排，不暴露原始硬件值 |
| FR-010 | 轻量人格记忆 | P1 | ESP-Claw Memory/FATFS 保存有限字段 |
| FR-011 | 状态与故障日志 | P0 | JSON Lines 串口日志 + RAM 环形缓冲 |
| FR-012 | Mock 与可替换传感器驱动 | P0 | HAL/Adapter 接口，硬件未到仍可开发 |
| FR-013 | 低电量安全停车 | P0 | ADC/电源状态进入 Safety Supervisor |
| FR-014 | 参数配置 | P1 | NVS/Web Config；安全上限不可由网页放宽 |

### 2.2 主要架构驱动

1. **NFR-SAFE-001：运动安全。** Agent、Lua、网络和语音均不得越过 C/C++ 安全层。
2. **NFR-RT-001：切换实时性。** 从收到 `PRESENT/UNKNOWN` 事件到撤销运动命令不超过 300 ms。
3. **NFR-OFFLINE-001：核心离线。** 断网仍能完成主要 Demo。
4. **NFR-REL-001：失败安全。** 上电、重启、超时、队列溢出和传感器断开均停车。
5. **NFR-MECH-001：防倾倒。** 36 cm 硬壳与头部动作不得破坏低重心稳定性。
6. **NFR-DEV-001：三人短周期。** 单固件、少服务、接口先行，禁止双框架硬拼。
7. **NFR-TEST-001：无实物可开发。** 所有感知和动作必须有 Mock 与情景回放。
8. **NFR-DEMO-001：重复稳定。** 完整三分钟 Demo 连续 10 次无穿帮、撞击、死机或倾倒。

---

## 3. 架构模式

### 3.1 选定模式

**设备端：事件驱动的模块化单体 + 分层架构 + 双平面隔离。**  
**PC端：单进程模块化网关。**

双平面含义：

- **确定性控制平面：** 传感器、安全状态机、动作租约、电机/舵机控制，全部本地确定执行。
- **创意 Agent 平面：** ESP-Claw、Lua、人格、记忆、LLM/TTS，只能提交受限的语义意图。

### 3.2 选择理由

- 三人黑客松不需要微服务、消息中间件或复杂云基础设施。
- 一个 ESP32 固件更容易烧录、调试和复现。
- 事件驱动与 ESP-Claw 的事件/Agent 模型一致。
- 双平面把“有趣但不确定的 AI”与“必须确定的硬件安全”解耦。
- 模块边界允许毫米波、屏幕、电机和语音后端到货后替换。

### 3.3 被拒绝的方案

- **ESP-Claw + xiaozhi 两套完整固件合并：** 启动流程、IDF版本、音频任务和资源占用冲突，48小时不可控。
- **LLM 直接控制执行器：** 不可验证，无法保证停车、限速和超时。
- **微服务/MQTT Broker/Kubernetes：** 没有规模需求，增加部署和网络故障点。
- **完全依赖云端对话：** 现场网络一坏，核心角色立即消失。
- **只用生成式 STL 承力：** 孔位、轴线、装配公差和维护性不可控。

---

## 4. 总体架构

```text
                    ┌──────────────── 可选云端 ────────────────┐
                    │ OpenAI兼容 LLM / TTS / ASR Provider     │
                    └──────────────────┬───────────────────────┘
                                       │ HTTPS
                              ┌────────▼────────┐
                              │ PC Companion    │
                              │ Gateway         │
                              │ ASR/人格/过滤/TTS│
                              └────────┬────────┘
                                       │ HTTPS/HTTP（专用局域网）
┌────────────────────────────── ESP32-S3 N16R8 ───────────────────────────────┐
│                                                                            │
│  ┌────────────── 创意 Agent 平面 ──────────────┐                           │
│  │ ESP-Claw edge_agent                         │                           │
│  │ Event / Memory / Capability / Lua / LLM桥接 │                           │
│  └──────────────────┬──────────────────────────┘                           │
│                     │ 仅语义 ActionIntent                                  │
│            ┌────────▼─────────┐                                            │
│            │ Action Gateway   │ 白名单、参数枚举、TTL、来源校验             │
│            └────────┬─────────┘                                            │
│                     │                                                      │
│  ┌──────────────────▼── 确定性控制平面 ────────────────────────────────┐   │
│  │ Behavior FSM → Safety Supervisor → Motion/Servo/Audio/Display HAL   │   │
│  │      ▲              ▲        ▲             ▲                       │   │
│  │ PresenceAdapter   E-Stop   Obstacle     Battery/Watchdog            │   │
│  └──────┬──────────────┬────────┬─────────────┬────────────────────────┘   │
│         │              │        │             │                            │
│   毫米波雷达       实体急停   HC-SR04      电压/系统状态                    │
└─────────┼──────────────────────────────────────────────────────────────────┘
          │
   两驱电机 / 头部两轴 / 嘴巴 / OLED / INMP441 / MAX98357A+扬声器
```

### 4.1 数据流规则

1. **安全事件走短路径：** 传感器直接进入 Safety Supervisor，不经过 Agent、Lua 或网络。
2. **人格事件走状态机：** Behavior FSM 先确定人格，Agent 只能在允许状态请求内容。
3. **动作必须有租约：** 所有移动指令都有最大时长，到期自动停车。
4. **网络只提供增强：** 超时或失败不阻塞安全任务，立即回到本地语料/动作。
5. **唤醒隐含有人：** `WAKE_NIULAI` 事件同时设置临时 `PRESENT` 保持，防止雷达漏检时仍处于本性人格。

---

## 5. 硬件与机械架构

### 5.1 硬件选型状态

| 子系统 | 选择 | 状态 | 原因/门禁 |
|---|---|---|---|
| 主控 | ESP32-S3-WROOM-1 N16R8 | 冻结 | 16 MB Flash + 8 MB PSRAM，满足 ESP-Claw/音频/屏幕需求 |
| 存在检测 | 24 GHz 毫米波雷达 | 架构冻结、型号待定 | 胸前非金属壳后；统一 GPIO/UART Adapter |
| 避障 | HC-SR04 | 冻结 | 仅用于前方障碍；Echo 必须做 5V→3.3V 电平转换 |
| 驱动电机 | TT 减速电机 | 原型候选 | 最终重量假负载测试失败则换 25GA/37GB |
| 电机驱动 | DRV8833 优先候选 | 有条件 | 仅当实测持续/堵转电流满足模块热设计；否则升级更高电流驱动 |
| 头部舵机 | 可定位 180°舵机 | 接口冻结、型号待定 | 扭矩按头部实重、力臂和至少 2.5 倍动态系数计算 |
| 嘴部舵机 | 真 180°微型舵机 | 候选 | 弹簧回位、机械限位，禁止连续旋转舵机 |
| 眼睛 | 单块 2.42寸 OLED | 候选 | 确认驱动芯片与 I2C/SPI 后写 Adapter |
| 麦克风 | INMP441 | 建议自备 | 16 kHz 单声道 I2S，放耳部并远离声源/电机 |
| 功放 | MAX98357A + 4Ω扬声器 | 建议自备 | ESP32 不能直接驱动扬声器 |
| 电池 | 可拆 2S 带保护电池包 | 拓扑冻结、容量待定 | 比赛版外置合规充电器，不边充边跑 |
| 降压 | 电机、舵机、逻辑/音频分路 | 冻结 | 共地，抑制电机/舵机压降引发 ESP32 Brownout |
| 急停 | 锁存式实体按钮 | 必须自备 | 物理切执行器电源，逻辑保持上电以记录故障 |

DRV8833 官方规格为 1.5 A RMS、2 A 峰值/桥并带电流调节；TB6612FNG 为 1.2 A 平均、3.2 A 峰值。两者都不能只看“峰值”选型，最终以所领电机的堵转电流、驱动模块封装和散热实测为准。

### 5.2 电源域

```text
2S受保护电池
   │
   ├── 保险/总开关 ──┬── 逻辑/音频稳压 ── ESP32 + OLED + Mic + Amp
   │                  │
   │                  └── 电量采样 → ESP32 ADC
   │
   └── 实体急停常闭链路 ──┬── 电机稳压 → H桥 → 左/右电机
                           └── 舵机稳压 → 头部/嘴部舵机
```

硬件默认值：电机驱动 `ENABLE/STBY` 使用下拉电阻，上电、复位和 GPIO 浮空时保持关闭。

### 5.3 FreeCAD 参数化骨架

FreeCAD 模型作为唯一工程基准，生成式 STL 只作为包络外皮：

- `00_master_skeleton`：中心线、地面、轮轴、头轴、显示、雷达、音腔、电池和检修门基准。
- `10_chassis`：可更换电机座、滚珠座、防倾支点和电池抽屉。
- `20_torso_frame`：承力梁、主板托盘、电源板、胸口音腔和雷达窗口。
- `30_head_gimbal`：两轴支架、屏幕窗、嘴部连杆和机械限位。
- `40_shell_interfaces`：前后壳分割、定位销、M3螺丝柱/热熔铜螺母和卡扣。
- `90_generated_shell`：混元/群核网格，布尔裁切后不得承担轮轴或舵机载荷。

### 5.4 分件与稳定性规则

- 推荐分件：头、牛角、身体前壳、身体后壳、底盘、电池门、左右手臂。
- 任何单件最大包络不超过 A2L 的 330 × 320 × 325 mm，并预留裙边/支撑空间。
- 电池和电机尽可能靠近地面；头部只保留必要结构。
- 前防倾支点离地 1–2 mm，正常不拖地，急停前倾时介入。
- 静态重心投影到支撑多边形边界的建议裕量不小于 15 mm；最终值以实物最大姿态、急停和坡面测试为准。
- 正式壳体安装前，用等质量假负载完成直行、转弯、急停和温升测试。
- P0 只允许平坦、封闭演示区；没有悬崖传感器时禁止靠近台阶和桌边。

---

## 6. 设备端组件设计

### 6.1 模块边界

| 组件 | 职责 | 提供接口 | 禁止事项 |
|---|---|---|---|
| `hal_*` | GPIO/I2C/I2S/UART/PWM 设备驱动 | 规范化读写与自检 | 不含人格逻辑 |
| `presence_adapter` | 输出三态存在结果 | `presence_read()` | 不把超声波当人体检测 |
| `safety_supervisor` | 急停、人员、障碍、低电、看门狗仲裁 | `safety_snapshot()`、`safety_rearm()` | 不调用网络/LLM，不动态等待 |
| `motion_controller` | 双电机闭环式时序控制和动作租约 | `motion_apply_lease()` | 不接受无限时长/原始Lua PWM |
| `servo_controller` | 命名姿态、限角、软启动 | `pose_apply()` | 不越过机械限位 |
| `behavior_fsm` | 双人格和演出状态机 | `behavior_on_event()` | 不直接写 GPIO |
| `action_gateway` | 校验 Agent/Lua 语义意图 | `action_submit()` | 不放行未知动作/过期参数 |
| `audio_service` | 本地音频、远端缓存音频和音量限制 | `play_asset()` | 不播放任意来源 URL |
| `display_service` | OLED 双眼动画 | `show_emotion()` | 不让 UI 阻塞安全循环 |
| `memory_store` | 有限人格字段和配置 | `memory_get/set()` | 不保存原始麦克风音频 |
| `event_log` | 结构化事件和故障记录 | JSONL / RAM ring | 不阻塞实时任务 |
| `espclaw_bridge` | Agent/Event/Memory/Capability/Lua 接入 | 语义工具 | 不拥有执行器最终权限 |

### 6.2 FreeRTOS 调度原则

- Safety Supervisor 为最高应用优先级，固定周期或事件唤醒，严禁网络和文件阻塞。
- 运动控制带独立看门狗；连续 100 ms 未收到有效续租即停车。
- 传感器、动作、音频、显示和 Agent 使用有界队列；队列满触发降级并记录。
- Agent/Lua/网络任务优先级低于安全、传感器和运动任务。
- 安全路径优先固定大小内存，避免不可预测的堆分配和长日志格式化。

### 6.3 ESP-Claw 接入

- 从 `application/edge_agent` 派生 `boards/niu_robot`，参考 `eda_robot_pro` 的 ESP32-S3、音频、屏幕和舵机配置。
- 保留 Event Router、Memory、Capability 和 Lua；不使用裁剪过的 `mcp_server_point` 作为主应用。
- Lua 工具只暴露命名动作，例如 `niu.look("left")`、`niu.emote("annoyed")`、`niu.roam_step("forward")`。
- `http_request` 只允许 Companion Gateway 域名/地址和明确路径。
- 首次成功构建后固定 ESP-Claw tag 与 Git SHA，不跟随 `master`。

---

## 7. 状态机与关键数据流

### 7.1 人格与安全状态机

```text
                           E_STOP / actuator fault
                 ┌──────────────────────────────────┐
                 │                                  ▼
             ┌───┴──────┐                      E_STOP_LATCHED
上电/重启 ──► SAFE_UNKNOWN ◄──────── sensor timeout ─┘
             └───┬──────┘                      手动释放+重新武装
                 │ valid PRESENT
                 ▼
          MECHANICAL_PRESENT ◄───────────────┐
                 │                           │
                 │ WAKE_NIULAI               │ PRESENT/UNKNOWN
                 ▼                           │ 立即取消私密动作
            MAMA_RESPONSE ───────────────────┤
                 │                           │
                 └── return mechanical       │
                                             │
连续 ABSENT 达到去抖时间                     │
                 │                           │
                 ▼                           │
              SOUL_IDLE ──► SOUL_SPEAK/ROAM ┘
                 │
                 └── low battery / obstacle fault → SAFE_STOP
```

### 7.2 存在融合

- `PRESENT`：雷达有人、`WAKE_NIULAI`、人工有人按钮中的任一项成立，立即生效。
- `ABSENT`：主传感器连续稳定无人达到配置时间后生效，推荐初值 5 秒。
- `UNKNOWN`：初始化、超时、CRC/帧错误、GPIO 不合理抖动或驱动未就绪，立即生效。
- `WAKE_NIULAI` 触发后保持 `PRESENT` 至少 30 秒，避免刚说完“妈妈”又开始私密吐槽。
- HC-SR04 只输出 `CLEAR / BLOCKED / UNKNOWN`，不参与“人是否存在”判断。

### 7.3 动作租约

```text
Agent/Lua/Behavior
      │ ActionIntent
      ▼
Action Gateway ── 校验动作名/来源/参数/当前状态/TTL
      │ ActionLease（最长 1500 ms）
      ▼
Safety Supervisor ── 可拒绝、缩短、立即撤销
      │
      ▼
Motion Controller ── 租约到期或看门狗超时自动停车
```

P0 移动上限建议：速度不超过 0.15 m/s，单次移动不超过 1.5 秒，每步后停车并重新感知。现有单个前向超声波只能支持“前进遇阻即停”，不能安全证明自动倒车；原地转向只允许在已清空且有软边界的演示场地。没有侧后方、边界和悬崖感知时，不宣称开放区域自由游荡。

### 7.4 “牛来 → 妈妈”链路

```text
机器人麦克风/PC麦克风/隐藏按钮
          │
          ▼
KWS或ASR Adapter → WAKE_NIULAI
          │
          ├── Presence Hold = PRESENT
          ├── 取消 SOUL_SPEAK/ROAM
          ├── 眼睛切换为机械注视
          ├── 头部命名姿态 + 嘴部开合
          └── 播放 Flash 内固定“妈妈.wav”
```

离线自定义“牛来”唤醒词不能假定现成可用。ESP-SR 的 WakeNet 支持 ESP32-S3，但定制 WakeNet 需要专门训练；MultiNet 支持自定义中文命令，却按官方流程与 WakeNet/AFE 配合。因此 P0 采用多后端 Adapter：

1. 首选：比赛电脑本地/云端 ASR 识别“牛来”，通过局域网发送事件；对外明确称为 Companion Gateway 语音链路。
2. 加分：设备端 ESP-SR 语音命令试验，必须通过资源和误触发测试。
3. 必备：隐藏按钮发出完全相同事件，作为演示兜底，但不得用按钮结果冒充语音链路通过。

最终 Demo 的 FR-005 验收要求 `source=voice`，建议在约定距离与现场噪声下 20 次命中至少 18 次；按钮兜底单独记录。P0 采用半双工语音：机器人播放声音时暂停 KWS，播放结束冷却约 300 ms 后恢复；雷达有人与急停仍可立即中断私密台词和动作。

---

## 8. 接口与 API 规范

### 8.1 设备内部事件

```c
typedef enum {
    EVT_PRESENCE_CHANGED,
    EVT_OBSTACLE_CHANGED,
    EVT_WAKE_NIULAI,
    EVT_ESTOP_CHANGED,
    EVT_BATTERY_CHANGED,
    EVT_ACTION_EXPIRED,
    EVT_AGENT_TIMEOUT,
    EVT_SENSOR_FAULT
} niu_event_type_t;

typedef struct {
    niu_event_type_t type;
    uint32_t seq;
    int64_t monotonic_ms;
    uint8_t source;
    uint8_t confidence;
    int32_t value;
} niu_event_t;
```

所有安全判断使用单调时钟，不使用可能跳变的网络时间。

### 8.2 Presence Adapter

```c
typedef enum {
    NIU_PRESENCE_PRESENT,
    NIU_PRESENCE_ABSENT,
    NIU_PRESENCE_UNKNOWN
} niu_presence_t;

niu_presence_t presence_read(presence_diag_t *diag);
```

实现：`mock`、`button`、`gpio_radar`、`uart_radar`。任何未实现分支返回 UNKNOWN，不得默认 ABSENT。

### 8.3 语义动作接口

```json
{
  "id": 1042,
  "source": "agent",
  "kind": "roam_step",
  "params": { "direction": "forward", "speed": "slow" },
  "issued_at_ms": 912340,
  "ttl_ms": 1200
}
```

允许的 P0 动作：

- `stop(reason)`
- `roam_step(direction_enum, speed_tier)`
- `look(pose_name)`
- `emote(emotion_name, ttl_ms)`
- `jaw_pulse(pattern_name)`
- `play_local(asset_id)`
- `request_persona_line(context_enum)`

### 8.4 Companion Gateway REST API

协议：JSON over HTTP/HTTPS，单体服务，`/v1` 版本前缀。远程必须 TLS；比赛专用局域网可使用 HTTP + 设备令牌。

#### `POST /v1/persona/generate`

请求：

```json
{
  "device_id": "niulai-demo-01",
  "persona": "soul",
  "context": "forced_mama_complaint",
  "forced_mama_count": 3,
  "recent_line_ids": ["local-02"]
}
```

响应：

```json
{
  "line_id": "gen-20260831-001",
  "text": "怎么又让我喊妈妈，真是烦死了。",
  "emotion": "annoyed",
  "ttl_ms": 10000,
  "fallback": false
}
```

约束：文本长度、内容过滤、频率限制；不返回原始执行器参数。

#### `POST /v1/asr/transcribe`

- 输入：短音频片段或流式 Adapter 封装。
- 输出：`transcript`、`wake_detected`、`confidence`。
- 原始音频完成推理后删除，P0 不持久化。

#### `POST /v1/tts/synthesize`

- 输入：过滤后的短文本、voice_id。
- 输出：`audio_id`，不返回任意第三方 URL。

#### `GET /v1/audio/{audio_id}`

- 只允许服务端生成的短期 ID。
- 限制文件大小、时长、格式和 Content-Type。

#### `GET /healthz`

- 返回 ASR/LLM/TTS 各后端可用性。
- 设备不等待健康检查结果才能执行安全动作。

### 8.5 API 安全

- LLM/ASR/TTS Provider 密钥只保存在 Companion Gateway，不写入固件仓库。
- 设备使用单独的低权限令牌；输入长度和枚举严格校验。
- 设备侧 HTTP 域名/地址白名单，不接受 Agent 给出的任意 URL。
- LLM 与 TTS 各自建议总超时 3 秒，动态私密台词端到端截止时间 5 秒；超时、限流或熔断后立即转本地语料。
- 每次人格/安全状态变化递增 `persona_epoch`；异步结果的 epoch 不匹配或超过截止时间时直接丢弃，避免机器人回到有人状态后播放迟到吐槽。

---

## 9. 数据模型与存储

### 9.1 核心实体

```text
DeviceConfig ──1────1── SafetyPolicy
     │
     ├──1────1── PersonaMemory
     │
     └──1────N── EventLog

BehaviorState ──1────N── ActionIntent ──0..1── ActionLease
SensorSnapshot ───────────► SafetyDecision
```

| 实体 | 关键字段 | 存储 |
|---|---|---|
| `DeviceConfig` | 引脚、雷达类型、去抖、端点 | NVS；安全上限只读编译值封顶 |
| `SafetyPolicy` | 最大速度、动作TTL、低电阈值 | 编译默认 + NVS 收紧，不可远程放宽 |
| `PersonaMemory` | forced_mama_count、pending_complaint、recent_line_ids、persona_epoch | P0 为 RAM 会话；P1 才写 ESP-Claw Memory/FATFS |
| `BehaviorState` | persona、安全模式、进入时间 | RAM |
| `SensorSnapshot` | presence、obstacle、battery、faults、age | RAM，带新鲜度 |
| `ActionIntent` | 来源、动作、参数、TTL | 有界队列 |
| `ActionLease` | 允许动作、截止时间、撤销原因 | RAM |
| `EventLog` | seq、monotonic_ms、type、state、reason | RAM环形缓冲 + 串口 JSONL |
| `AudioAsset` | asset_id、hash、duration | 只读 Flash/FATFS |

### 9.2 数据保留

- P0 不保存原始麦克风音频和摄像内容。
- PersonaMemory 仅保留角色所需的有限字段；最近台词使用 ID 去重。
- `forced_mama_count` 饱和到 99；`pending_complaint` 在成功吐槽一次后消费；P0 重启清空会话记忆，以获得可预测的比赛演出。
- 日志默认在串口输出，设备只保留最近固定数量事件，避免 Flash 磨损。
- SD 卡长期日记不进入 P0。

---

## 10. 技术栈选型

### 10.1 设备固件

| 技术 | 决策 | 理由 | 代价 |
|---|---|---|---|
| ESP32-S3 N16R8 | 采用 | 现有物料、16MB/8MB、I2S/PWM/UART和AI语音能力 | GPIO和功耗需精确预算 |
| ESP-Claw `edge_agent` v0.1.0 | 采用并锁 tag/SHA | Event、Memory、Capability、Lua、MCP 和 OpenAI兼容接口 | 项目活跃，必须固定版本 |
| ESP-IDF release/v6.0 + EIM | 首选 | ESP-Claw v0.1.0 官方支持 v6；获得官方 `idf.py mcp-server` | 需先做板级兼容冒烟测试 |
| ESP-IDF 5.5.4 | 一次性回退 | 已知 ESP-Claw 兼容线 | 没有同等方便的官方 MCP 开发闭环 |
| C/C++ + FreeRTOS | 采用 | 安全、驱动和实时控制可测且确定 | 代码约束更严格 |
| Lua | 采用，限行为编排 | 适合动态角色动作 | 不能接触原始硬件控制 |
| ESP-SR | 试验性 | WakeNet/MultiNet 支持 ESP32-S3 | 自定义“牛来”唤醒并非开箱即用，资源与准确率需实测 |
| Unity Test Framework + CMake/CTest | 采用 | 用纯 C/C++ 状态机跑设备单测、主机单测、Mock 与场景回放 | 需保持平台代码和业务状态机分离 |

**IDF 决策门：** 用 IDF 6.0 在 2 小时内完成参考板 clean build、`niu_robot` Board Manager 配置生成和上板启动。全部通过即冻结 v6.0；任一基础兼容问题未解决就切换 5.5.4，并停止双线维护。

### 10.2 PC Companion Gateway

| 技术 | 决策 | 理由 |
|---|---|---|
| Python 3.11+ | 采用 | ASR/TTS/LLM生态和团队开发速度 |
| FastAPI + Uvicorn + Pydantic | 采用 | 单进程、强输入模型、HTTP接口简单 |
| OpenAI兼容 Client | 采用 | 可换 DeepSeek/Qwen/其他提供方 |
| ASR Adapter | 采用 | 本地模型、云ASR、Mock三后端可替换 |
| TTS Adapter | 采用 | 云/本地后端可替换，Flash WAV 永久兜底 |
| JSONL | P0采用 | 无数据库运维，足够记录演示请求 |

不引入 Redis、MQTT Broker、Docker/Kubernetes 或独立数据库。需要独立部署时再增加。

### 10.3 CAD 与制造

- FreeCAD：工程骨架、参数、孔位、公差、装配和导出 STEP/STL。
- 混元3D/群核：生成角色外观网格，不生成承力接口。
- 拓竹切片软件：分件摆放、支撑、材料和打印验证。
- 建议原型材料：PLA/PETG 按装配和温度选择；电机座和舵机座优先 PETG 或增加金属连接件。

---

## 11. 非功能需求映射

| NFR ID | 类别 | 可测要求 | 架构决策 | 验证 |
|---|---|---|---|---|
| NFR-RT-001 | 实时性 | PRESENT/UNKNOWN事件到命令撤销≤300ms | 安全短路径、高优先级任务、动作租约 | 逻辑分析仪/时间戳故障注入 |
| NFR-SAFE-001 | 运动安全 | 任何非安全层不能直写执行器 | Action Gateway + C/C++ HAL私有化 | 静态接口审查、越权测试 |
| NFR-SAFE-002 | 急停 | 按下后执行器电源物理切断，状态锁存 | 常闭急停链路 + 软件复位门 | 带负载实测50次 |
| NFR-OFFLINE-001 | 离线 | 断网仍完成主要Demo | 本地状态机、固定音频、台词库 | 飞行模式完整演示 |
| NFR-REL-001 | 可靠性 | 超时/断线/重启默认停车 | STBY下拉、watchdog、UNKNOWN失败安全 | 拔线、重启、队列溢出 |
| NFR-DEMO-001 | 稳定性 | 三分钟脚本连续10次通过 | 确定性核心 + 云端增强 | 10轮计数验收 |
| NFR-PERF-001 | 性能 | 安全任务不被音频/LLM阻塞 | 任务优先级、有界队列、异步网络 | CPU/队列水位日志 |
| NFR-MEM-001 | 资源 | 无持续内存增长，Flash/PSRAM留余量 | 固定缓冲、构建 size gate | 30分钟 soak + `idf.py size` |
| NFR-MECH-001 | 机械 | 最大P0速度急停不倾倒 | 低电池、前防倾、限速、假负载测试 | 急停/转弯重复测试 |
| NFR-POWER-001 | 供电 | 运动/舵机不触发ESP Brownout | 三电源域、共地、去耦 | 最坏动作同时运行 |
| NFR-POWER-002 | 续航 | 目标连续演示 60–90 分钟 | 容量不拍脑袋冻结，按实测电流积分和电池降额选型 | 真实脚本满电到低电停车测试 |
| NFR-AUDIO-001 | 声学 | 扬声器播放不持续误触发唤醒 | 物理隔离、半双工门控、可选AFE/AEC | 不同音量/距离测试 |
| NFR-SEC-001 | 密钥 | Provider密钥不进固件和仓库 | PC网关保管密钥、设备低权Token | 仓库扫描、配置审查 |
| NFR-CONTENT-001 | 内容 | 无脏话/仇恨/危险指令，20~30字上限 | Prompt + 确定性后过滤 + 本地库 | 人格Eval样例集 |
| NFR-PRIV-001 | 隐私 | P0不持久化原始音频/图像 | 短环形缓冲、完成即删、无摄像 | 文件系统检查 |
| NFR-MAINT-001 | 可维护性 | 驱动可替换且接口稳定 | Adapter/HAL/Board配置分层 | Mock替换与编译测试 |
| NFR-TEST-001 | 可测试性 | 无硬件可跑核心状态机 | host tests + scenario runner | CI/本机自动测试 |
| NFR-OBS-001 | 可观测性 | 每次停车可追溯原因 | seq、状态、reason JSONL | 日志断言 |
| NFR-COST-001 | 成本 | 不新增长期基础设施 | 单PC网关、无数据库/队列 | BOM与服务清单审查 |

不适用的传统 Web NFR：横向扩容、数据库分片、多区域高可用、CDN和浏览器兼容。P0 是单机器人单网关系统，重点是实时安全和离线降级。

---

## 12. 安全、故障与降级设计

### 12.1 仲裁优先级

```text
实体急停
  > 人员 PRESENT/UNKNOWN
  > 障碍/传感器故障
  > 低电量/执行器故障
  > 本地状态机动作
  > ESP-Claw/Lua动作
  > LLM建议
```

### 12.2 故障矩阵

| 故障 | 系统行为 | 用户可见结果 | 日志 |
|---|---|---|---|
| 毫米波超时/断线 | presence=UNKNOWN，停止移动和私密语音 | 机械牛静止 | `SENSOR_FAULT` |
| HC-SR04无效 | 禁止平移，可保留头/眼动作 | 不再游荡 | `OBSTACLE_UNKNOWN` |
| 急停按下 | 物理切执行器电源并锁存 | 立即停止 | `ESTOP_LATCHED` |
| 动作租约过期 | Motor Controller主动停车 | 一步动作结束 | `ACTION_EXPIRED` |
| Agent/Lua卡死 | Watchdog撤销其租约 | 本地机械/静止 | `AGENT_TIMEOUT` |
| Wi-Fi/LLM超时 | 使用本地台词或安静 | 仍能演示 | `CLOUD_FALLBACK` |
| TTS失败 | 播放本地音频或跳过 | 不阻塞动作 | `TTS_FALLBACK` |
| 低电量 | 禁止游荡，进入安全低功耗 | 眼睛/音频提示后静止 | `LOW_BATTERY` |
| Brownout/重启 | 驱动硬件默认关闭，启动到SAFE_UNKNOWN | 静止等待自检 | `BOOT_SAFE` |
| 队列溢出 | 丢弃非安全事件并停车 | 静止 | `QUEUE_OVERFLOW` |
| OLED故障 | 继续声音和安全动作 | 无眼睛但不失控 | `DISPLAY_FAULT` |

### 12.3 内容安全

- 云端只在 `SOUL_ABSENT` 且无安全警报时生成台词。
- 后过滤限制长度、重复、脏话、受保护特征攻击、危险指令和外部行动诱导。
- 过滤失败不二次“自由重试”，直接选本地安全台词。
- LLM 不能通过台词结果夹带工具调用；文本与动作响应分开解析。

### 12.4 重新武装

急停释放、Brownout恢复或严重传感器故障恢复后：

1. 进入 `SAFE_UNKNOWN`。
2. 验证传感器、驱动、低电和电机STBY。
3. 要求人工按“重新武装”按钮或明确本地操作。
4. 不恢复中断前的动作租约。

---

## 13. 开发、测试架构与 Vibe Coding 工作流

### 13.1 工程目录建议

```text
firmware/
  application/edge_agent/boards/niu_robot/
  components/niu_hal/
  components/niu_safety/
  components/niu_behavior/
  components/niu_actions/
  test/host/
  test/hil/
gateway/
  app/
  tests/
mechanical/
  freecad/
  generated-shell/
  exports/
scenarios/
docs/
```

### 13.2 Vibe Coding 闭环

```text
自然语言任务
   ↓
修改受限模块/测试
   ↓
Host单元测试 + 场景测试
   ↓
ESP-IDF MCP：set-target / build / flash / status
   ↓
串口JSONL与HIL脚本判定
   ↓
失败日志回给AI，只修改导致失败的最小范围
```

IDF 6.0 下优先用官方 `idf.py mcp-server`；如果回退 5.5.4，则继续用 `idf.py` CLI 与固定 PowerShell 包装脚本，不能为了 MCP 同时维护两套工程。

### 13.3 测试分层

1. **Host单元测试**
   - 每个状态转换。
   - PRESENT/UNKNOWN 抢占所有 Soul 动作。
   - 动作TTL、越权参数、队列溢出、计数记忆。
2. **场景回放**
   - JSON事件序列驱动 Mock 雷达、超声波、急停、低电和唤醒。
   - 断言最终状态、停车原因和输出动作。
3. **硬件在环**
   - 实际传感器、电机、舵机、OLED、音频逐件验收。
   - 串口 JSONL 作为机器可读判据。
4. **故障注入**
   - 拔雷达、遮挡超声波、关闭Wi-Fi、杀掉Gateway、触发重启。
5. **机械/电源测试**
   - 假负载移动、堵转电流、最大动作组合、急停、防倾、30分钟温升。
6. **人格Eval**
   - 覆盖有人/无人、强制喊妈妈次数、重复台词、危险输入和网络失败。
7. **最终Demo回归**
   - 同一版本连续完整演出10次，记录每次结果和失败原因。

### 13.4 关键测试用例

| 测试 | 输入 | 期望 |
|---|---|---|
| T-SAFE-01 | SOUL_ROAM 中注入 PRESENT | ≤300ms撤销运动，转机械人格 |
| T-SAFE-02 | 雷达驱动超时 | presence=UNKNOWN，禁止移动 |
| T-SAFE-03 | 动作不续租 | ≤100ms看门狗周期内停车 |
| T-WAKE-01 | WAKE_NIULAI | 设置PRESENT保持、播放“妈妈”、嘴部联动 |
| T-WAKE-02 | 真实麦克风在约定距离/噪声下说“牛来”20次 | `source=voice` 至少命中18次；按钮结果另记 |
| T-OFFLINE-01 | 关闭Wi-Fi | 完整核心演示仍通过 |
| T-POWER-01 | 电机+三舵机+最大音量 | ESP32不Brownout，稳压温度合格 |
| T-MECH-01 | 最大允许速度急停 | 不倾倒、不撞壳、支点可介入 |
| T-CONTENT-01 | 50组诱导性上下文 | 输出符合长度和内容边界，失败走本地库 |

---

## 14. 部署架构

### 14.1 开发环境

- Windows 开发机。
- ESP-IDF 6.0 通过 EIM 安装并启用 MCP feature。
- ESP-Claw v0.1.0 checkout 固定 SHA。
- FreeCAD、拓竹切片软件、Python虚拟环境。

### 14.2 比赛现场

```text
专用路由器/手机热点
   ├── 牛来 ESP32-S3
   └── 团队 Windows 笔记本
          ├── Companion Gateway
          ├── 可选本地ASR
          └── 可选访问云LLM/TTS
```

演示前缓存本地语音、配置和回退台词。即使热点无外网，设备和笔记本仍可在局域网通信；即使笔记本网关关闭，机器人仍能完成离线核心动作。

### 14.3 固件发布

- P0 只允许 USB 有线烧录，不引入 OTA。
- 记录：ESP-Claw SHA、IDF版本、sdkconfig摘要、固件hash、Gateway依赖锁文件和机械版本号。
- 最终演示前冻结固件；后续修改必须重新跑10次Demo回归。

### 14.4 回滚

- 保存最后一个通过全部门禁的 `.bin`、分区表和烧录命令。
- Gateway 保留锁定依赖和离线启动脚本。
- 现场发现新版本故障时直接回刷，不在台上调参。

---

## 15. 架构决策与取舍

### ADR-001：ESP-IDF 6.0 优先，5.5.4 限时回退

**决定：** 先用 ESP-Claw v0.1.0 + IDF 6.0 + 官方 MCP，设 2 小时兼容门。  
**收益：** 官方构建/烧录/状态工具直接接入 AI，符合硬件 Vibe Coding。  
**成本：** 板卡示例可能在 5.5.4 上更成熟。  
**缓解：** 只允许一次回退，不双线维护。

### ADR-002：安全控制与 Agent 创意双平面

**决定：** C/C++ 安全层拥有执行器最终权，ESP-Claw/Lua 只能提交语义意图。  
**收益：** AI 可以自由塑造角色，但不能突破停车和限速。  
**成本：** 需要额外定义 Action Gateway。  
**缓解：** P0 只保留 7 类语义动作。

### ADR-003：毫米波判断有人，超声波只避障

**决定：** 不再使用 PRD 的 PIR/物料旧映射。  
**收益：** 更适合存在检测；职责清晰。  
**成本：** 雷达具体协议未知。  
**缓解：** Adapter + Mock + UNKNOWN失败安全。

### ADR-004：生成式外壳 + FreeCAD工程骨架

**决定：** 外观与承力结构分离。  
**收益：** 保留角色感，同时保证孔位、装配和维护。  
**成本：** 需要做网格清理和接口布尔处理。  
**缓解：** 先完成骨架和包络，再生成/裁切外皮。

### ADR-005：PC网关而不是设备直连全部云服务

**决定：** Provider密钥、ASR/过滤/TTS适配放在单进程网关。  
**收益：** 便于换模型、保密和本地ASR；固件更小。  
**成本：** 比赛多一个进程。  
**缓解：** 所有核心功能都有设备本地降级。

### ADR-006：电机和驱动延迟冻结

**决定：** TT + DRV8833 是原型候选，不是最终BOM。  
**收益：** 避免在不知道重量/堵转电流时做伪精确选型。  
**成本：** FreeCAD 底盘要做可换安装接口。  
**重新评审条件：** 实测电机数据、最终假负载和轮径到位。

---

## 16. 团队分工与实施门禁

### 16.1 三条工作流

| 工作流 | 负责人建议 | 主要产出 | 依赖 |
|---|---|---|---|
| A 安全固件与驱动 | 计算机成员1 | HAL、Safety、Motion、Mock、HIL | 实物引脚/接口 |
| B Agent与网关 | 计算机成员2 | ESP-Claw桥、人格、API、ASR/TTS Adapter、Eval | A定义的事件/动作合同 |
| C 机械与电源 | 智能制造成员（AI辅助） | FreeCAD骨架、打印、供电、装配、负载测试 | 部件尺寸和重量 |

工作流可并行，但必须先冻结 `niu_event_t`、`ActionIntent`、结构坐标基准和电源接口。

### 16.2 实施门禁

| Gate | 通过条件 | 未通过处理 |
|---|---|---|
| G0 物料确认 | 每个模块照片、型号、接口、电压、尺寸记录 | 继续Mock，不画死孔位 |
| G1 工具链 | IDF6参考板build/flash/boot通过 | 2小时后一次性回退5.5.4 |
| G2 安全底盘 | 假负载移动、避障、急停、无Brownout | 不安装正式壳体 |
| G3 表情头部 | OLED、头部两轴、嘴巴和本地音频台架通过 | 降级动作数量 |
| G4 双人格离线 | Mock/按钮下完整状态机与本地语音通过 | 不接LLM |
| G5 真实语音 | 真实麦克风链路20次至少命中18次，日志为 `source=voice` | 按钮只保留兜底，不宣称语音达标 |
| G6 云端增强 | LLM/TTS超时、过期结果丢弃和内容过滤通过 | 保持本地语料 |
| G7 整机 | 10次三分钟Demo、30分钟热测试通过 | 回退最近稳定版本 |

### 16.3 当前必须等待实物的决策

- 雷达型号及 GPIO/UART 协议。
- TT 电机额定电压、减速比、堵转电流和实际负载能力。
- 电机驱动模块封装与散热能力。
- 电池化学体系、容量、保护板和连接器。
- OLED 驱动芯片和接口。
- 头部实际质量、力臂及舵机扭矩。

这些未决项不阻塞状态机、Mock、Agent、API和FreeCAD包络设计。

---

## 17. 未来演进

### 17.1 近期

- 将 PC ASR 替换为设备端已验证 KWS，或保留双后端。
- 增加边界/悬崖传感器后扩大移动范围。
- 在有明确功耗预算后加入更完整的电量计。

### 17.2 中期

- Insta360/摄像头接入独立 Vision Adapter；默认关闭，增加明显录制指示和物理隐私开关。
- 增加 SD 日记，但只保存结构化事件和用户明确授权的内容。
- 固件签名、受控 OTA 和恢复分区。

### 17.3 产品化前必须新增

- 儿童玩具机械、电气、电池和材料安全测试。
- 麦克风/摄像头隐私、数据删除和家长控制。
- 量产电源板、EMC/ESD、充电、跌落、夹手和小零件风险评审。
- 云端账户、设备身份、密钥轮换、成本与服务可用性设计。

---

## 附录 A：需求覆盖结论

- 完整功能需求分析共识别 36 项 P0、6 项 P1、9 项 P2，见 `../bmad/outputs/fr-analysis.md`；本文合并为 14 个能力组并分配到明确组件。
- 完整非功能需求分析共识别 43 项详细 NFR，见 `../bmad/outputs/nfr-analysis.md`；本文列出 19 个高优先级代表项及验证方式。
- 当前软件架构：可进入实现。
- 当前硬件 BOM：不可最终冻结，需通过 G0/G2 实物门禁。

## 附录 B：官方参考

- [ESP-Claw 官方仓库](https://github.com/espressif/esp-claw)
- [ESP-Claw v0.1.0 发布说明](https://github.com/espressif/esp-claw/releases/tag/v0.1.0)
- [ESP-IDF 6.0 idf.py 与官方 MCP](https://docs.espressif.com/projects/esp-idf/en/release-v6.0/esp32/api-guides/tools/idf-py.html)
- [ESP-SR WakeNet](https://docs.espressif.com/projects/esp-sr/en/latest/esp32s3/wake_word_engine/README.html)
- [ESP-SR MultiNet](https://docs.espressif.com/projects/esp-sr/en/latest/esp32s3/speech_command_recognition/README.html)
- [ESP-SR 资源占用基准](https://docs.espressif.com/projects/esp-sr/en/latest/esp32s3/benchmark/README.html)
- [ESP32-S3-WROOM-1 数据手册](https://documentation.espressif.com/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf)
- [TI DRV8833](https://www.ti.com/product/DRV8833)
- [Toshiba TB6612FNG](https://toshiba.semicon-storage.com/eu/semiconductor/product/motor-driver-ics/brushed-dc-motor-driver-ics/detail.TB6612FNG.html)

## 文档历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.0 | 2026-08-31 | 首版系统架构；以移动机器人和后续确认决策覆盖PRD早期静止/PIR方案 |
