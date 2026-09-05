# 牛来本地云端大脑架构

**文档版本：** 1.0  
**日期：** 2026-09-05  
**状态：** P0 已按方案 A 落地协议切片；固件二次开发仍是人工门禁  
**覆盖：** 覆盖双板 UART 方案为赛后路线；本文件是当前实现的权威。

## 1. 系统概述

笔记本上的 `brain/` 扮演小智云端大脑：说话、Lua 动作编排、人格状态、飞书/微信 bot。唯一一块小智 S3 扩展板只负责听、说、屏、舵机和本地冻结。

**范围内：** 小智 WSS 协议、mock ASR/LLM/TTS、Lua 白名单沙箱、FREEZE 抢占、飞书事件订阅、微信回调、MCP `niu.perform` 窄工具。

**范围外：** 双板 ESP-Claw 固件、Hensun 控制面/账号/OTA、Lua 直写 PWM、第二块板接线。

**架构驱动：**

1. 超声冻结 ≤300 ms，必须在板端；大脑只能配合。
2. 不插第二块板。
3. 无 API key 时测试仍绿。
4. Lua 与 LLM 都是不可信输入。
5. 飞书或微信 bot 与语音走同一意图管道。

## 2. 模式

**模块化单体。** 一台电脑一个 FastAPI 进程。IM、WSS、Lua、Persona、MCP 是模块，不是微服务。

拒绝：双板 Claw（缺接线）、整仓 Hensun（账号/控制台过重）。

```text
飞书 bot / 微信 bot          麦克风
        │                      │
        ▼                      ▼
   /im/feishu|wechat     小智板 WSS /xiaozhi/v1/
        │                      │
        └──────────┬───────────┘
                   ▼
            NiulaiBrain
         persona / lua / mcp / providers
                   │
         ┌─────────┼─────────┐
         ▼         ▼         ▼
      回复 IM    TTS 下发   niu.perform
```

## 3. 组件

| 组件 | 职责 | 接口 |
|---|---|---|
| `wss` `/xiaozhi/v1/` | 小智 hello/listen/stt/llm/tts | WebSocket |
| `providers` | ASR/LLM/TTS，默认 mock | 可换 OpenAI 兼容 HTTP |
| `persona` | FREEZE / PUBLIC_ALIVE / SECRET_ALIVE | 内存 FSM |
| `lua_sandbox` | 只跑 `niu.*`，禁 os/io | `.lua` 文件或源码 |
| `mcp_broker` | 校验 verb+ttl，记录下发 | `call_perform` |
| `im` | 飞书 url_verification + 消息；微信 JSON 回调 | HTTP POST |
| 板端 Safety（尚未烧） | 超声 FREEZE、打鼾、舵机停 | 本地 C |

权威：PWM 只在板端；FREEZE 板端可独立完成；Lua 只在电脑；公开对话内容在大脑。

## 4. 数据

- `ActionIntent {verb, args, ttl_ms}`，禁止 `pulse_us`。
- `ImOutbound {channel, chat_id, text, intents}` 测试用发件箱。
- 原始音频只在当轮连接内存。
- 密钥：`NIULAI_LLM_*` / `FEISHU_APP_ID` / `FEISHU_APP_SECRET` / 微信 Token，未配置则 mock。

## 5. API

### 设备 WSS `GET /xiaozhi/v1/`

`hello` → `hello`；`SECRET_ALIVE` 时紧接着主动 `tts`。  
`listen.start` + 二进制 + `listen.stop` → `stt` → `llm` → `tts start/sentence_start/stop`。  
mock 模式把 UTF-8 字节当 ASR 文本。

### 飞书 `POST /im/feishu/event`

- `type=url_verification` → `{"challenge": ...}`（飞书后台配置请求网址时用）。
- `im.message.receive_v1` 文本 → 与语音同一 `handle_user_text`。

### 微信 `POST /im/wechat/callback`

JSON：`MsgType=text`, `FromUserName`, `Content`。企业微信 XML 可在固件门禁后加适配，不改意图管道。

FREEZE 时 IM 只回 `……`，不下发 walk，不泄漏吐槽。

### MCP

`niu.perform({verb, ttl_ms, ...})`  
verb ∈ walk/turn/stop/snore/eyes；缺 ttl 或未知 verb 不下发设备。

## 6. NFR 映射

| ID | 决策 | 状态 |
|---|---|---|
| NFR-SAFE-001 | 优先级在 persona + mcp_broker；Lua/LLM 不能绕过 | 大脑侧已测；板端待烧 |
| NFR-SAFE-002 | Lua 白名单 + 禁 os/io；无脉宽 | pytest 绿 |
| NFR-RT-001 | 冻结路径设计在板端 C；大脑 ingest_distance 只作协同 | 板端 HUMAN_GATE |
| NFR-REL-002 | mock provider，无 key 可跑 | pytest 绿 |
| NFR-OFFLINE-001 | 大脑挂了板端仍应能冻/鼾/妈妈 | 板端 HUMAN_GATE |

## 7. 技术栈

Python 3.12+、FastAPI、pytest。Lua 由受限解释器执行 `niu.*` 调用（不嵌入 LuaJIT）。固件仍计划官方 xiaozhi-esp32 加 `niulai-s3-expand-v17` 板型。

## 8. 取舍

- Lua 在电脑不在 S3：单板可做，演示「AI 写脚本驱动运动」；板上无完整 Claw VM。
- IM 与语音共用大脑：飞书/微信能指挥同一只牛；bot 凭据未配时只走测试发件箱。
- mock 音频用 UTF-8 而非 Opus：协议测试秒级确定性；真机需换 Opus provider。

## 9. 部署

开发：

```bash
python -m pip install -r brain/requirements.txt
python -m pytest -q brain/tests
python -m uvicorn brain.app.main:app --host 0.0.0.0 --port 8000
```

板端配网指向 `ws://<笔记本局域网IP>:8000/xiaozhi/v1/`。  
飞书开放平台事件订阅：`http://<IP>:8000/im/feishu/event`。  
微信公众号/企微：`http://<IP>:8000/im/wechat/callback`（公网或内网穿透）。

固件烧录会覆盖当前 Arduino 测试程序，需口头确认。

## 10. 下一步

1. 真机 HUMAN_GATE：小智板型、唤醒词「牛来牛来」、本地打鼾、MCP。
2. Provider 换成带 key 的 ASR/LLM/TTS。
3. 飞书发消息用 `im/v1/messages`（需 app_id/secret）；微信客服回复。
4. 赛后可选第二块 ESP-Claw 板，不阻塞本周。
