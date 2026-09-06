# 牛来：Codex 接管与第一轮修复

日期：2026-09-06。基点：`91245675a2682d30e299144721cbf667761e2830`。本轮修改已整合到工作区，尚未提交 Git。

用户授权 Codex 负责产品取舍、开发、整合及验收。采用总控加三条开发线；Grok 已在 STATE 中确认 STOPPED，保留 `.grok-loop/STOP`，不自动恢复旧调度。

## 已修复

- 私密记忆只进入 ABSENT 提示，礼貌对话不再收到最近的私下台词；首次并发创建记忆记录改为幂等插入。
- 首句和周期语音、LLM、ASR 不再阻塞 WebSocket 接收控制事件；PRESENT/UNKNOWN/abort 使旧响应失效，打断后可以重新独处。
- 网页聊天不再阻塞同一服务的控制事件；场景变化后返回 409，丢弃旧回复，页面显示取消提示。
- 运动由明确的整句短口令决定，模型 Lua 无权自行触发、改方向或覆盖停止；问句、描述和否定不启动运动。
- 测距失效进入 UNKNOWN 并停腿，连续有效远距满 8 秒才恢复独处；排队的 SECRET 执行前复核状态。

## 验证

- 最终隔离回归：`149 passed, 1 warning in 7.91s`，退出码 0。既有警告为 Starlette TestClient/httpx 弃用提示。
- 13 个整合文件与受测副本 SHA256 全部一致；JavaScript 语法和 `git diff --check` 通过。
- 独立审核复现并验证了取消后的恢复和周期语音边界，未以作者总结代替审核。
- 真实 FFmpeg 编码：3 个 Opus 包、456 字节；不等于真实 ASR、声音听感或板上播放验收。
- ESP32-S3 实际源码单元交叉编译和完整 IDF 构建均通过。新应用固件 2,803,312 字节，SHA256 `e8259c5cc48cdbdf40f6cdd600d3c70b46c6cdd8d8cfbc68b57453240d7b3c22`；保存在 `outputs/niulai-codex-2026-09-06/xiaozhi.bin`，未烧录。
- 本机服务 `http://127.0.0.1:8000` 已启动；`/health` 版本为 `codex-bfb3eb8ef3b4`。首页、人格页、脚本、状态接口均 HTTP 200，实际 WebSocket hello/UNKNOWN 流程通过。

服务仅绑定本机，排练台仍明确是模拟模式。现有 SQLite 启动前已备份到 `.scratch/codex-takeover/memory-before-start.sqlite`。运行 PID、日志在该目录的 `runtime.json`、`server.stderr.log`。

完整构建首次因 Windows GBK 控制台输出失败；设置 `PYTHONUTF8=1` 和 `PYTHONIOENCODING=utf-8` 后重跑成功，构建说明已补齐。旧固件和原生命循环源码保留在 `.scratch/codex-takeover/native-before-build/`。

## 仍待完成

1. 确认喇叭、超声和独立舵机电源接线，四腿悬空固定后进行真机联调；本轮未烧录、未下发实体动作。
2. 实测妈妈顺序、礼貌语气、独处留白、靠近打断、离线恢复。应用任务原有 2.2 秒等待和 WSS 打开仍可能延迟私音取消，不能宣称停止时延达标。
3. 固定外部小智主干版本与完整补丁；本机成功构建不能替代从干净仓库重现。
4. 按固定 40 项及 7 门禁完成独立复评。历史 37.75 分只有汇总、证据格式不完整，本轮不靠增加测试数量虚报涨分。

本轮原始记录：`.grok-loop/evidence/runs/20260906-codex-takeover.json`。7 项真机门禁在获得实际证据前保持 NOT_RUN。
