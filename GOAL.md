# 牛来 overnight GOAL

日期：2026-09-06 凌晨 → **12:00 交卷**  
仓库：`23xxCh/ox-robot`  
工作区：`E:\AI WORK\硬件黑客松`  
固件树：`E:\XIAOZHI_NATIVE\xiaozhi-esp32`（overlay 同步 `firmware/xiaozhi-niulai/`）

## 北极星

一只桌上的潮玩牛：**人在时是礼貌玩具，人走后才过自己的生活。**  
观众不听解说也能看懂反差。技术服务于这场戏，不追求第二块板、官网云或完整 ESP-Claw。

## 已锁定（禁止回退）

后面任何 agent / 循环 / 提交都不能改掉这些：

1. **靠近不喊**：冻腿、打断 SECRET 吐槽、切断私有 WSS、只显示 **聆听** 脸。不播妈妈。
2. **喊「牛来」/ BOOT / KY-004**：先 `PlaySound(OGG_MAMA)` 约 2.2 秒，再礼貌听、想、说。走私有大脑。
3. **礼貌对话里让它动**：大脑可写白名单 Lua `niu.walk` / `niu.turn`（ttl≤2000），板端短促执行。靠近仍立刻冻腿。
4. **离开约 8 秒**：SECRET。不礼貌吐槽、其他表情（困/眨眼/思考/生气/吃惊）、短促晃腿。
5. **TFT**：全屏黄牛脸，棕色底。人在场只有聆听/微笑（说话时嘴动）。禁止再出现全白屏。
6. **私有 WSS only**：`ws://192.168.10.95:8000/xiaozhi/v1/`。拒绝 `xiaozhi.me`。不合完整 ESP-Claw。舵机 5V 外供。GPIO 12 是 CHRG，左后舵机 GPIO 9。
7. **冻结走板端 C**，不走 LLM。

## 完整系统 = 本轮 P0（今晚必须做完）

「完整」指 **12:00 能连拍 3 分钟真机戏** 的软件闭环，不是 v2 SPEC 里的全部场景引擎。

| ID | 交付 | 完成标准 |
|---|---|---|
| P0-1 | 生命循环 | PRESENT 冻 / 唤醒妈妈+礼貌 / ABSENT 吐槽+晃。测例覆盖状态转移。 |
| P0-2 | 黄牛脸 | SetupUI 之后画脸。人在：listening / happy。人走：secret 表情。说话嘴动。 |
| P0-3 | 礼貌说话 | 私有 WSS ASR→LLM→TTS。礼貌口吻。让动才发 Lua。 |
| P0-4 | 记忆进台词 | `MemoryStore` 接到真机路径：妈妈次数、上次被打断的事、最近 5 句不重复。独处会翻旧账。 |
| P0-5 | 独处生活 | 不只 11 秒一句。有冷却、换话题、可安静。断链时播本地 `secret*.ogg`，不假称云端在聊。 |
| P0-6 | 动作 | PRESENT 仅 Lua 短促走/转；ABSENT 可随机晃；任何靠近立刻 1500 µs。ttl≤2000。 |
| P0-7 | 大脑进程 | `0.0.0.0:8000` 健康。改 `brain/` 后优雅重启 uvicorn，不丢端口。WLAN 仍是 192.168.10.95。 |
| P0-8 | 测试与仓库 | `python -m pytest` 全绿。overlay 与 native 板型目录同步。推 `23xxCh/ox-robot`。 |
| P0-9 | 交卷材料 | Submission / Checkpoint2 / README / 飞书附录与真机行为一致。不写没做的能力。 |

## 不做（P1 / 禁止假装完成）

- 外壳总装、真正四足步态闭环、第二块板、毫米波、六轴
- 打开 xiaozhi.me / 官方 OTA / 合入完整 ESP-Claw
- 飞书/微信遥控驱动腿
- 完整 SPEC 场景 JSON 播放器、向量检索、微服务
- **不要闪 COM6**，除非：(a) 大脑挂了且必须改固件 URL，或 (b) WLAN IP 变了，或 (c) 屏又全白。闪之前在回复里写原因。默认只改源码 + 本地编译。
- 不要删 `NiulaiStartPoliteChat` 里的妈妈。不要把 PRESENT 无唤醒改回自动走路。

## 人才能做（循环不要假装）

- ≤3 分钟连续录像：妈妈 → 礼貌聊 → 靠近冻 → 离开 8 秒吐槽+表情
- 把 `docs/feishu-checkpoint2-append.xml` 贴进飞书
- 接线、外供 5V、机械装配

循环每次只在进度里提醒这两项还没拍/没贴，不要把时间花在写新文档催人。

## 通宵怎么跑

每 20 分钟一个 sprint：

1. 读本文件 + 当前 `firmware/xiaozhi-niulai/` + `brain/app/main.py` + `application.cc` 的妈妈函数。
2. 选 **一个未勾选的 P0**，做最小可验证改动。
3. 跑相关测例；`python -m pytest` 要绿。
4. 同步 overlay → `xiaozhi-esp32/main/boards/niulai-s3-expand-v17/`。
5. 提交并 `git push`（不要 force）。
6. 大脑若改了 Python：只重启 **自己拉起的** uvicorn；现役 PID 若 `/health` 已 ok 且代码已加载就不要再抢 8000。
7. 笔记本保活。不要让电脑睡觉。
8. **12:00 中国时区之后停止开发**，只做健康检查，并 `scheduler_delete` 本循环。

## 进度（循环每完成一项把 `[ ]` 改成 `[x]` 并写一行证据）

- [x] P0-2 黄牛脸源码 + 已烧 COM6（2026-09-06 凌晨，SetupUI 后画脸）
- [x] 妈妈先播再礼貌（`PlaySound(OGG_MAMA)+2.2s` 仍在 `application.cc`）
- [x] P0-4 记忆接到 WSS 说话路径（wake 计妈妈次数；PRESENT/abort 记下打断；ABSENT 翻旧账且最近 5 句去重。测例 `test_wake_counts_mama_and_absent_uses_interrupt`）
- [ ] P0-5 独处冷却 / 不重复 / 断链本地 secret ogg
- [ ] P0-6 PRESENT Lua 走路源码已有，测例+文档对齐；默认不烧板
- [ ] P0-3/P0-7 礼貌对话回归测例；brain `/health` 保持 ok
- [x] P0-8 pytest 全绿并 push（63 passed，`d79fe06`）
- [ ] P0-9 交卷稿与锁定行为一致
- [ ] 人：录像
- [ ] 人：飞书粘贴
